# Markdown Thread — User Guide

How to discuss a Markdown document with an agent inside the document itself.
The rules are in [SPEC.md](SPEC.md); this guide covers everyday use.
(2026-10-06, spec v0.1)

## 1. Ask a question

Mark the text you mean and add a label:

<!-- mdthread: example -->
```markdown
The dispatcher ==polls every five seconds== [?why ticks] and then sleeps.

> [?why ticks] Why poll instead of reacting to events?
```

- `==…==` marks the exact text (a **range anchor**). A bare `[?why ticks]`
  marks a point. Anchors are optional.
- The quote below starts with the same label: that is the **thread**. Put it
  after the paragraph, separated by blank lines.
- Labels are free text after `?`. Case and extra spaces don't matter:
  `[?Why  Ticks]` is the same label. Every thread needs its own label.
- One thread can have several anchors: repeat the label wherever it applies.
- A comment about the whole document needs no anchor:

<!-- mdthread: example -->
```markdown
> [?overall] Is the tone right for an engineering audience?
```

Longer questions continue on the next lines, all starting with `>`:

<!-- mdthread: example -->
```markdown
> [?scope] Two things:
>
> - does this cover retries?
> - what happens on restart?
```

## 2. Get answers

Ask the agent to process the file:

- Ask your agent: "reply to the open threads in notes/dispatch.md".
- Agents without built-in support need
  [agents/AGENTS-snippet.md](agents/AGENTS-snippet.md) in their instructions
  file (for example `AGENTS.md`).

The agent appends a reply to each open thread and leaves everything else
alone:

<!-- mdthread: example -->
```markdown
> [?why ticks] Why poll instead of reacting to events?
>
> <-- agent/model-x @ 2026-10-06T19:57-04:00
> Polling keeps the dispatcher stateless across restarts.
```

Reload the file in your editor afterwards (`:e` in Neovim).

## 3. Follow up

Add a blank `>` line, then `-->` and your message:

<!-- mdthread: example -->
```markdown
> [?why ticks] Why poll instead of reacting to events?
>
> <-- agent/model-x @ 2026-10-06T19:57-04:00
> Polling keeps the dispatcher stateless across restarts.
>
> --> Alice @ 2026-10-06
> Fair, but five seconds is slow.
```

Your name and the time after `-->` are optional (`-->` alone is fine). Write
the message on the next line: text on the `-->` line is read as your name.

## 4. Close and reopen

When a thread is done, add a closing line:

<!-- mdthread: example -->
```markdown
> [?why ticks] Why poll instead of reacting to events?
>
> <-- agent/model-x @ 2026-10-06T19:57-04:00
> Polling keeps the dispatcher stateless across restarts.
>
> +++ Alice ! keep five seconds for now
```

Everything after `+++` is optional: a name, `@ date`, and `! reason`. The
blank `>` line before `+++` is required; without it the line is ordinary
text.

You can also ask the agent: "close [?why ticks] in dispatch.md".

To reopen a closed thread, add a blank `>` line and another `-->` message
after the `+++` line. The thread is open again and the agent will reply; the
closing line stays as part of the history:

<!-- mdthread: example -->
```markdown
> [?why ticks] Why poll instead of reacting to events?
>
> <-- agent/model-x @ 2026-10-06T19:57-04:00
> Polling keeps the dispatcher stateless across restarts.
>
> +++ Alice ! keep five seconds for now
>
> --> Alice @ 2026-10-08
> Load doubled this week; is five seconds still fine?
```

## 5. Clean up

The agent never deletes threads on its own. After processing a file it lists
closed threads and offers to remove them. Removing a thread deletes the quote
and its anchors and keeps the highlighted text as plain text.

To have closed threads removed automatically, add this to the file's front
matter:

```yaml
---
threads:
  autoremove_closed: true
---
```

## 6. How states work

The last message decides:

| Thread ends with | State | Agent |
|---|---|---|
| your question or `-->` | open | replies |
| `<--` | answered | waits for you |
| `+++` | closed | offers removal |

## 7. Editors

**Neovim** (with this setup's bullets.vim and render-markdown):

- Enter continues a `> ` line. Enter on an empty `> ` line ends the quote, and
  with it the thread.
- For the blank `>` line before `-->`: Enter, then Ctrl+Enter (keeps the empty
  `> ` line), then type `> --> `. A smoother Enter is planned for
  markdown-thread.nvim.
- render-markdown's completion menu may pop up after `> [`; ignore it. Enter
  doesn't accept an item unless you selected one.

**Zettlr**: threads look like ordinary quotes; `==text==` shows as a
highlight.

## 8. Things to know

- Threads render as ordinary quotes everywhere (GitHub, Pandoc exports). Remove
  closed threads before sharing, or keep them as a record.
- `==text==` is a highlight in Obsidian, Zettlr and render-markdown, in Pandoc
  only with `-f markdown+mark`, and plain `==text==` on GitHub.
- Keep a blank line before and after each thread. Without one before it,
  Pandoc merges the thread into the paragraph above; a line right after it
  ends the thread.
- Inside a list, indent the thread to the item's text.
- `mdthread check FILE` (in `skill/markdown-thread/scripts/`) reports mistakes
  such as duplicate labels or a `+++` without its blank line.
