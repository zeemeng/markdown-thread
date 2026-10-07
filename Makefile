SKILL_DIR := $(HOME)/.hermes/skills/productivity/markdown-thread

.PHONY: test sync-spec install-skill uninstall-skill

test:
	python3 -m unittest discover -s tests

# The skill ships a copy of SPEC.md: Hermes refuses files outside the skill dir.
sync-spec:
	cp SPEC.md skill/markdown-thread/references/protocol.md

install-skill:
	@if [ -e "$(SKILL_DIR)" ] && [ ! -L "$(SKILL_DIR)" ]; then \
		echo "$(SKILL_DIR) exists and is not a symlink; move it away first" >&2; exit 1; fi
	mkdir -p "$(dir $(SKILL_DIR))"
	ln -sfn "$(CURDIR)/skill/markdown-thread" "$(SKILL_DIR)"
	@echo "linked $(SKILL_DIR) -> $(CURDIR)/skill/markdown-thread"

uninstall-skill:
	@if [ -L "$(SKILL_DIR)" ]; then rm "$(SKILL_DIR)" && echo "removed $(SKILL_DIR)"; \
	else echo "$(SKILL_DIR) is not a symlink; left alone"; fi
