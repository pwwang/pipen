SHELL=/bin/bash

version:
	@if [ -z "$(word 2,$(MAKECMDGOALS))" ]; then \
		CURRENT_VERSION=$$(grep '^__version__' pipen/version.py | sed 's/__version__ = "\(.*\)"/\1/'); \
		MAJOR=$$(echo $$CURRENT_VERSION | cut -d. -f1); \
		MINOR=$$(echo $$CURRENT_VERSION | cut -d. -f2); \
		PATCH=$$(echo $$CURRENT_VERSION | cut -d. -f3); \
		NEW_PATCH=$$((PATCH + 1)); \
		NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
	else \
		NEW_VERSION="$(word 2,$(MAKECMDGOALS))"; \
	fi; \
	echo "Updating version to $$NEW_VERSION"; \
	sed -i "s/^version = .*/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	sed -i "s/^__version__ = .*/__version__ = \"$$NEW_VERSION\"/" pipen/version.py; \
	LAST_TAG=$$(git describe --tags --abbrev=0 2>/dev/null || echo ""); \
	if [ -z "$$LAST_TAG" ]; then \
		COMMITS=$$(git log --pretty=format:"- %s" HEAD); \
	else \
		COMMITS=$$(git log --pretty=format:"- %s" $$LAST_TAG..HEAD); \
	fi; \
	if [ -n "$$COMMITS" ]; then \
		printf "\n## %s\n\n%s\n\n" "$$NEW_VERSION" "$$COMMITS" | cat - <(tail -n +3 docs/CHANGELOG.md) > docs/CHANGELOG.md.tmp; \
		head -n 2 docs/CHANGELOG.md > docs/CHANGELOG.md.new; \
		cat docs/CHANGELOG.md.tmp >> docs/CHANGELOG.md.new; \
		mv docs/CHANGELOG.md.new docs/CHANGELOG.md; \
		rm -f docs/CHANGELOG.md.tmp; \
	fi; \
	echo "Version updated to $$NEW_VERSION";

# Catch-all rule to ignore version number argument
%:
	@:

.PHONY: version
