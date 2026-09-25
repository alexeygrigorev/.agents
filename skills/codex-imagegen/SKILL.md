---
name: codex-imagegen
description: Use when a non-Codex engine needs raster artwork, pixel sprites, illustrations, or transparent assets generated through Codex's built-in imagegen tool.
compatibility: Requires an authenticated non-interactive codex CLI, its built-in image generation capability, workspace-write access for generated artifacts, and Python with Pillow or a uv-managed environment for chroma-key removal when needed.
---

# Codex Image Generation Bridge

This skill lets Claude, Gemini, or another non-Codex engine create project-bound raster images by delegating the image operation to a fresh, non-interactive Codex process. Codex is used only as the image-generation worker; the calling engine remains responsible for understanding the user request, integrating the result, and testing the application.

Use the local `imagegen` skill as the source of truth for prompt structure, transparent-image handling, asset paths, and validation. This document records the working procedure used for the Moon Hop artwork: a pixel-art bunny sprite sheet, a chroma-key removal pass, and a matching 16:9 pixel-art title splash.

## Activation boundary

Use this skill when all of these are true:

- The caller is not Codex and does not have a native image-generation tool.
- The user wants a raster image, sprite sheet, illustration, background, concept image, or image edit.
- A local `codex` CLI is available and authenticated.
- The deliverable belongs in a project, game, site, or other workspace.

Do not use it for:

- SVG, CSS, Canvas-only visuals, icons, or simple geometric shapes that are better made natively.
- Audio, video, or text-to-speech work.
- A request that explicitly requires a different image provider.
- A Codex session that already has the native `imagegen` skill and tool; use those directly instead of nesting another Codex process.

## Model pin: Luna Max

This is a body-level execution rule rather than trigger metadata. Delegated jobs must use `gpt-5.6-luna` with `max` reasoning and must not use Sol.

The required model configuration is:

```text
model = gpt-5.6-luna
model_reasoning_effort = max
```

In plain language, this is Luna Max. Every delegated image job must include both overrides:

```bash
-c model="gpt-5.6-luna" -c model_reasoning_effort="max"
```

Never use `gpt-5.6-sol`, `gpt-6-sol`, the user's default model, or an unverified model alias for this skill. If Luna is unavailable, stop and report that exact failure; do not silently downgrade to Sol or another model. The image model itself remains Codex's built-in image tool, not the OpenAI image API.

## Non-interactive delegation

Codex must run with `codex exec`, never with an interactive `codex` process. Run the command in the background with an explicit timeout and capture a short final summary separately from the full log:

```bash
timeout 30m codex exec \
  -C "$PROJECT_ROOT" \
  --sandbox workspace-write \
  -c model="gpt-5.6-luna" \
  -c model_reasoning_effort="max" \
  -o "$SUMMARY_FILE" \
  "$PROMPT" \
  > "$LOG_FILE" 2>&1 &
```

Add `--skip-git-repo-check` when the project is not a Git repository. Use `--sandbox workspace-write` because the worker must save the generated image into the project. Do not add `--dangerously-bypass-approvals-and-sandbox`. Read the summary file first after completion, then inspect the log only for diagnostics.

The Codex worker starts with no conversation context. Give it:

- The absolute project path.
- The exact source and final asset paths.
- The requested dimensions, aspect ratio, style, palette, and constraints.
- The fact that it must read the applicable `AGENTS.md`, `CLAUDE.md`, and imagegen instructions.
- A short final-response format containing only paths, dimensions, alpha status, and a completion note.
- A boundary saying that it must not modify source code, tests, or unrelated files.

## Built-in imagegen only

The delegated prompt must say:

```text
Read the local imagegen skill and use its built-in image generation tool.
Do not use the image_gen.py CLI fallback.
Do not ask for or print any API key.
```

The built-in tool does not require an `OPENAI_API_KEY`. If the built-in tool is unavailable, report that fact to the user and ask before using a separately approved API-key fallback. Never hide a provider downgrade in a delegated job.

Generate one asset per built-in image call. A single job may contain several independent generation requests, but it must make one tool call per asset and save each result independently.

## Prompt structure

Give the image worker a structured prompt rather than an adjective pile:

```text
Use case: stylized-concept
Asset type: <project asset role>
Primary request: <what the image depicts>
Scene/backdrop: <environment or background>
Subject: <focal character/object and pose>
Style/medium: <pixel art, illustration, concept art, etc.>
Composition/framing: <camera angle, crop, negative space, aspect ratio>
Lighting/mood: <mood without contradicting the medium>
Color palette: <specific limited palette>
Constraints: <must-have details and exact dimensions>
Avoid: <text, watermark, blur, extra characters, incompatible style>
```

For a specific game asset, name the game, screen, renderer, expected cell count, and whether the final image needs alpha. A precise composition constraint prevents a beautiful image that cannot actually be used by the game.

## Pixel-art sprite workflow

For an animated game character, ask for a sheet rather than a single pose when animation matters. The Moon Hop sheet used this exact contract:

- Four columns by two rows, eight frames, in this order: idle, run A, run B, jump, dash, hurt, celebrate, crouch.
- One consistent side-view bunny astronaut, centered in every cell, with consistent scale and generous padding.
- Crisp deliberate pixel blocks, a limited palette, hard edges, and no smooth painterly gradients.
- No grid lines, labels, text, watermark, cast shadow, or extra character.
- A perfectly flat `#00ff00` chroma-key background if the model does not provide native alpha; do not use green in the subject.
- Raw source at `assets/generated/bunny-sprite-source.png`.
- Final transparent sheet at `assets/generated/bunny-sprite.png`.

A useful worker instruction is:

```text
Generate the raw sheet with the built-in image tool. Inspect its actual dimensions and frame layout rather than assuming the requested size. If it has native alpha and transparent corners, preserve that alpha. If it uses the flat green key, run the installed remove_chroma_key.py workflow. Save both the raw source and the final transparent sheet at the exact project paths. Validate all eight frame regions contain visible subject pixels. Do not modify any other project files.
```

The generated source is often wider than a nominal square even when the logical layout is 4x2. Compute cell width as `naturalWidth / 4` and cell height as `naturalHeight / 2`; do not hard-code a 1024x1024 assumption.

## Chroma-key and alpha handling

Prefer native alpha when the built-in tool returns it. Inspect the image channels and corner pixels before processing. If the corners are transparent and the subject is separated cleanly, keep the native alpha and do not run key removal.

For a genuine flat key, use the installed helper:

```bash
python "${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/remove_chroma_key.py" \
  --input "$SOURCE_IMAGE" \
  --out "$FINAL_IMAGE" \
  --auto-key border \
  --soft-matte \
  --transparent-threshold 12 \
  --opaque-threshold 220 \
  --despill
```

The helper requires Pillow. Use an existing project environment or `uv run --with pillow ...`; do not install with `pip`. If a cached or project environment already has Pillow, prefer it. If the helper cannot run, ask the calling engine to handle the dependency rather than silently using a different image process.

Validate:

- The final file exists and is non-empty.
- The output has an alpha channel.
- All four corners are transparent.
- Every expected sprite cell has non-zero alpha coverage.
- The subject does not contain obvious key-color fringe.
- The output dimensions and frame layout match the code that will consume it.

## Pixel-art title splash workflow

For a title screen, generate a separate 16:9 image rather than stretching a sprite sheet. The Moon Hop title brief was:

```text
Use case: illustration-story
Asset type: 16:9 pixel-art game title splash
Primary request: a brave white bunny astronaut riding a carrot-powered lunar skiff over violet alien-moon craters
Scene/backdrop: deep indigo star field, distant planets, layered lunar horizon, cyan energy trails
Subject: bunny and skiff in the right third, with clean dark negative space in the left third for UI
Style/medium: crisp limited-palette pixel art, deliberate 2x2-style pixel blocks, no smooth gradients
Composition/framing: 16:9 landscape, subject right, UI space left, strong silhouette, readable at game scale
Lighting/mood: dramatic cyan rim light and carrot-orange propulsion glow
Constraints: no words, no letters, no logo, no watermark, no UI, no border, no extra characters
```

Save it as a non-destructive sibling such as `assets/generated/title-art-pixel.png`. Keep the previous artwork until the new asset has been visually accepted.

## Integration rules

After generation, keep the image in the project and update the consuming code:

- Use a stable project-relative path such as `/assets/generated/...`.
- Add `image-rendering: pixelated` to CSS images and set `imageSmoothingEnabled = false` before drawing sprite frames on Canvas.
- Compute frame rectangles from the actual loaded image dimensions.
- Preserve a procedural or existing-art fallback if the image fails to load.
- Do not leave a project-referenced asset only in Codex's default generated-image directory.
- Do not overwrite an existing asset unless the user explicitly requested replacement; otherwise use a versioned sibling.

For a game, report the sprite frame order and the final cell layout to the code that consumes it. Keep UI text and HUD styling separate from the sprite so a failed image does not break the interface.

## Visual and gameplay validation

A generated image is not finished merely because the API returned a file. For game work:

1. Load the project in a browser.
2. Confirm the image request succeeds and the asset dimensions are correct.
3. Use Playwright screenshots for the title, active gameplay, and game-over states.
4. Exercise the controls that select sprite frames: jump, double jump, dash, hit, and celebration.
5. Check that alpha edges are clean, the sprite is not cropped, and the pixel scale is crisp.
6. Run the project's lint, typecheck, test, and build commands.
7. Iterate the prompt or integration based on rendered evidence, not just the raw image preview.

Useful checks include:

```bash
identify -format '%f %wx%h channels=%[channels] corner=%[pixel:p{0,0}]\\n' "$IMAGE"
npm run lint
npm run typecheck
npm test
npm run build
```

If the project uses Playwright, capture explicit states rather than relying on a generic success screenshot. Save screenshots in a project-local review directory.

## Reporting

At the end of a delegated image job, report only useful facts:

- Final project-relative asset paths.
- Raw source path when retained.
- Dimensions, aspect ratio, and alpha status.
- Whether Codex's built-in image tool or a fallback was used.
- Any validation or browser-test result that affects confidence.

Never print credentials, full environment files, authentication headers, or private provider configuration. The model pin is safe to report: `gpt-5.6-luna` with `max` reasoning.

## Failure handling

- **Luna unavailable:** report the exact model error and stop; do not use Sol.
- **Built-in image tool unavailable:** report that the local imagegen tool is unavailable and ask before any API-key fallback.
- **Chroma removal unavailable:** retain the raw source, explain the Pillow/uv dependency issue, and do not claim transparency was validated.
- **Wrong frame count or layout:** inspect the actual image, adjust the consumer to the verified layout, or regenerate with a narrower prompt.
- **Image is technically valid but visually wrong:** iterate on composition, palette, silhouette, or pixel scale using rendered screenshots. Do not paper over an art-direction problem with extra UI.
- **Asset looks good but gameplay does not:** keep the art, then fix collision boxes, frame selection, scale, and timing separately.
