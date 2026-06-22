"""Configure the 'zodex' profile: Codex routed to Z.AI under ~/.zodex."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shlex
import sys
from pathlib import Path


ZODEX_PROXY_PORT = 18765
ZAI_CODING_CHAT_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
ZAI_API_KEY_URL = "https://z.ai/manage-apikey/apikey-list"


CONFIG_TOML = f"""# Codex routed to Z.AI GLM Coding Plan.
# This profile is selected by setting CODEX_HOME=$HOME/.zodex.

model = "glm-5.2"
model_provider = "codex-proxy"
model_catalog_json = __MODEL_CATALOG_JSON__
model_context_window = 1000000
disable_response_storage = true
personality = "pragmatic"
suppress_unstable_features_warning = true

[features]
apps = false

[features.multi_agent_v2]
enabled = true
max_concurrent_threads_per_session = 16

[plugins."github@openai-curated"]
enabled = false

[model_providers.codex-proxy]
name = "Z.AI via local codex-proxy"
base_url = "http://127.0.0.1:{ZODEX_PROXY_PORT}/v1"
wire_api = "responses"
requires_openai_auth = false
"""


MODEL_CATALOG_JSON = """{
  "models": [
    {
      "slug": "glm-5.2",
      "display_name": "GLM-5.2",
      "description": "Z.AI GLM coding model routed through local codex-proxy.",
      "base_instructions": "You are Codex, a coding agent. Be concise, precise, and useful.",
      "default_reasoning_level": "high",
      "supported_reasoning_levels": [
        { "effort": "none", "description": "Disable explicit thinking budget" },
        { "effort": "medium", "description": "Balanced reasoning" },
        { "effort": "high", "description": "More reasoning for coding tasks" }
      ],
      "shell_type": "shell_command",
      "visibility": "list",
      "supported_in_api": true,
      "priority": 50,
      "additional_speed_tiers": [],
      "service_tiers": [],
      "availability_nux": null,
      "upgrade": null,
      "supports_reasoning_summaries": false,
      "default_reasoning_summary": "none",
      "support_verbosity": false,
      "default_verbosity": "medium",
      "apply_patch_tool_type": "freeform",
      "web_search_tool_type": "text_and_image",
      "truncation_policy": { "mode": "tokens", "limit": 10000 },
      "supports_parallel_tool_calls": true,
      "supports_image_detail_original": true,
      "context_window": 1000000,
      "max_context_window": 1000000,
      "effective_context_window_percent": 95,
      "experimental_supported_tools": [],
      "input_modalities": ["text", "image"],
      "supports_search_tool": true,
      "use_responses_lite": false
    },
    {
      "slug": "glm-5-turbo",
      "display_name": "GLM-5-Turbo",
      "description": "Z.AI faster GLM model routed through local codex-proxy.",
      "base_instructions": "You are Codex, a coding agent. Be concise, precise, and useful.",
      "default_reasoning_level": "medium",
      "supported_reasoning_levels": [
        { "effort": "none", "description": "Disable explicit thinking budget" },
        { "effort": "medium", "description": "Balanced reasoning" },
        { "effort": "high", "description": "More reasoning for coding tasks" }
      ],
      "shell_type": "shell_command",
      "visibility": "list",
      "supported_in_api": true,
      "priority": 51,
      "additional_speed_tiers": [],
      "service_tiers": [],
      "availability_nux": null,
      "upgrade": null,
      "supports_reasoning_summaries": false,
      "default_reasoning_summary": "none",
      "support_verbosity": false,
      "default_verbosity": "medium",
      "apply_patch_tool_type": "freeform",
      "web_search_tool_type": "text_and_image",
      "truncation_policy": { "mode": "tokens", "limit": 10000 },
      "supports_parallel_tool_calls": true,
      "supports_image_detail_original": true,
      "context_window": 1000000,
      "max_context_window": 1000000,
      "effective_context_window_percent": 95,
      "experimental_supported_tools": [],
      "input_modalities": ["text", "image"],
      "supports_search_tool": true,
      "use_responses_lite": false
    }
  ]
}
"""


PROXY_CONFIG_JSON = f"""{{
  "server": {{
    "host": "127.0.0.1",
    "port": {ZODEX_PROXY_PORT},
    "log_level": "INFO"
  }},
  "providers": {{
    "zai": {{
      "type": "zai",
      "api_url": "{ZAI_CODING_CHAT_URL}",
      "endpoints": {{}},
      "allow_authorization_passthrough": false,
      "models": ["glm-5.2", "glm-5-turbo"]
    }}
  }},
  "models": {{
    "served": ["glm-5.2", "glm-5-turbo", "compact-default"]
  }},
  "routing": {{
    "model_routes": {{
      "*": ["proxy:glm-5.2"],
      "glm-5.2": [
        {{
          "type": "physical",
          "provider": "zai",
          "model": "glm-5.2",
          "reasoning": {{ "effort": "high" }}
        }}
      ],
      "glm-5-turbo": [
        {{
          "type": "physical",
          "provider": "zai",
          "model": "glm-5-turbo",
          "reasoning": {{ "effort": "medium" }}
        }}
      ],
      "compact-default": [
        {{
          "type": "physical",
          "provider": "zai",
          "model": "glm-5-turbo",
          "reasoning": {{ "effort": "none" }}
        }}
      ]
    }}
  }},
  "health": {{
    "auth_failure_immediate_unhealthy": true,
    "failure_threshold": 3,
    "cooldown_seconds": 60
  }},
  "access": {{
    "require_key": false,
    "keys": []
  }},
  "auto_compaction": {{
    "enabled": true,
    "max_attempts_per_request": 1,
    "tail_items_to_keep": 8
  }},
  "reasoning": {{
    "default_effort": "high",
    "effort_levels": {{
      "none": {{ "budget": 0, "level": "LOW" }},
      "medium": {{ "budget": 16384, "level": "MEDIUM" }},
      "high": {{ "budget": 32768, "level": "HIGH" }}
    }}
  }},
  "timeouts": {{
    "connect_seconds": 10,
    "read_seconds": 600
  }},
  "compaction": {{
    "temperature": 0.1,
    "preferred_targets": ["compact-default"]
  }}
}}
"""


def read_zlaude_key() -> str:
    settings_path = Path.home() / ".zlaude" / "settings.json"
    if not settings_path.exists():
        return ""
    try:
        data = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        return ""
    env = data.get("env", {})
    if not isinstance(env, dict):
        return ""
    key = env.get("ANTHROPIC_AUTH_TOKEN", "")
    return key.strip() if isinstance(key, str) else ""


def prompt_api_key(reuse_zlaude_key: bool) -> str:
    zlaude_key = read_zlaude_key()
    if reuse_zlaude_key and zlaude_key:
        return zlaude_key

    if zlaude_key:
        answer = input("  Reuse Z.AI key from ~/.zlaude/settings.json? [Y/n]: ").strip().lower()
        if answer in {"", "y", "yes"}:
            return zlaude_key

    print(f"  Get a Z.AI API key at: {ZAI_API_KEY_URL}")
    key = getpass.getpass("  Enter your Z.AI API key: ").strip()
    if not key:
        print("Error: no Z.AI API key provided. Aborting; no changes made.")
        sys.exit(1)
    return key


def write_private_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    os.chmod(path, 0o600)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reuse-zlaude-key",
        action="store_true",
        help="reuse ~/.zlaude/settings.json's Z.AI key without prompting",
    )
    args = parser.parse_args()

    api_key = prompt_api_key(args.reuse_zlaude_key)

    zodex_dir = Path.home() / ".zodex"
    zodex_dir.mkdir(parents=True, exist_ok=True)

    config_path = zodex_dir / "config.toml"
    env_path = zodex_dir / "zai.env"
    proxy_config_path = zodex_dir / "codex-proxy" / "config.json"
    model_catalog_path = zodex_dir / "model-catalogs" / "zai.json"

    config_path.write_text(
        CONFIG_TOML.replace("__MODEL_CATALOG_JSON__", json.dumps(str(model_catalog_path)))
    )
    write_private_file(env_path, f"ZAI_API_KEY={shlex.quote(api_key)}\n")
    proxy_config_path.parent.mkdir(parents=True, exist_ok=True)
    proxy_config_path.write_text(PROXY_CONFIG_JSON)
    model_catalog_path.parent.mkdir(parents=True, exist_ok=True)
    model_catalog_path.write_text(MODEL_CATALOG_JSON)

    print(f"  Configured zodex profile at {zodex_dir}")


if __name__ == "__main__":
    main()
