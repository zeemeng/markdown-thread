# markdown-thread

Discussion threads inside Markdown documents, for annotating (mostly
LLM-written) text and getting replies from an agent in place.

<!-- mdthread: example -->
```markdown
The dispatcher ==polls every five seconds== [?why ticks].

> [?why ticks] Why poll instead of reacting to events?
>
> <-- agent/model-x @ 2026-10-06T19:57-04:00
> Polling keeps the dispatcher stateless across restarts.
>
> +++ Alice ! ok
```

Threads are ordinary block quotes, so every Markdown renderer shows them
sensibly. Status: spec v0.1 draft (2026-10-06). License: [MIT](LICENSE).

## Contents

| Path | What |
|---|---|
| [SPEC.md](SPEC.md) | the format, independent of any tool |
| [GUIDE.md](GUIDE.md) | how to use it day to day |
| [fixtures/](fixtures/README.md) | conformance cases for any implementation |
| [agents/AGENTS-snippet.md](agents/AGENTS-snippet.md) | instructions to paste into agent instruction files such as `AGENTS.md` |
| `skill/markdown-thread/` | Hermes skill, with the reference parser `scripts/mdthread.py` |
| `tests/` | tests for the reference parser, fixtures and doc examples |

## Reference parser

`skill/markdown-thread/scripts/mdthread.py`: Python 3.10+, standard library
only.

```sh
mdthread.py list FILE [--state open|answered|closed|empty] [--json]
mdthread.py check FILE
mdthread.py reply FILE LABEL --name NAME (--body TEXT | --body-file PATH) [--write]
mdthread.py close FILE LABEL [--name NAME] [--now | --timestamp TS] [--reason TEXT] [--write]
mdthread.py remove FILE (LABEL... | --closed) [--write]
mdthread.py now
```

Edit commands print a unified diff unless `--write` is given. `check` exits 1
on errors. Indented code blocks (CommonMark) are not detected (SPEC §3.3
allows this); fenced code is.

## Development

```sh
make test            # python3 -m unittest discover -s tests
make sync-spec       # copy SPEC.md into the skill after editing it
make install-skill   # link the skill into ~/.hermes/skills/productivity/
make uninstall-skill
```

The Neovim renderer is planned as a separate repo, `markdown-thread.nvim`,
tested against `fixtures/`.
