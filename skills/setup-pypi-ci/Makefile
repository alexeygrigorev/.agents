publish-build:
	uv run hatch build

publish-clean:
	rm -r dist/

# Release: tag the current version and push to trigger CI publish.
release:
	@VERSION=$$(grep -E "^__version__" <pkg>/__version__.py | sed -E "s/.*['\"]([^'\"]+)['\"].*/\1/"); \
	echo "Releasing v$$VERSION"; \
	git tag "v$$VERSION"; \
	git push origin "v$$VERSION"
