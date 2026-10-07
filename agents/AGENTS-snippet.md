# Markdown Thread — instructions for agents

<!-- Paste this section into AGENTS.md, CLAUDE.md or similar. Spec v0.1. -->

## Markdown threads

Markdown files in this project may contain discussion threads for you. Full
rules: SPEC.md of markdown-thread (spec v0.1).

**Format.** A thread is a block quote whose first line starts with
`[?label]`; every line of it starts with `>`. Anchors `[?label]` in the text
point at it; `==text== [?label]` marks the exact text.

<!-- mdthread: example -->
```markdown
The dispatcher ==polls every five seconds== [?why ticks].

> [?why ticks] Why poll?
>
> <-- agent/model-x @ 2026-10-06T19:57-04:00
> It keeps the dispatcher stateless.
>
> --> Alice
> Fair.
>
> +++ Alice ! done
```

- The text after `[?label]` (and lines up to the first marker) is the opening
  question.
- Marker lines: `-->` the user, `<--` a responder, `+++` closed. Only the
  name, `@ timestamp` and (for `+++`) `! reason` go on a marker line; the
  message follows on the next lines.
- Every marker after the opening question is preceded by a blank `>` line.
- Labels match case-insensitively with whitespace collapsed. Code blocks
  never contain threads or anchors.

**State** comes from the last item: question or `-->` = open, `<--` =
answered, `+++` = closed.

**When asked to process a file:**

1. Find every thread. If two threads share a label, don't write to them;
   report it.
2. For each open thread, read the anchored text and context, then append at
   the end of the thread: a blank `>` line, `> <-- TOOL/MODEL @
   YYYY-MM-DDTHH:MM±HH:MM` (local time with offset), and the reply, each line
   prefixed like the thread's other lines (keep list indentation).
3. Reply once per open thread. Don't reply to answered or closed threads.
4. Don't change messages, labels, anchors or body text unless a thread asks;
   propose body changes in the reply first.
5. Close threads only when asked: blank `>` line, then `> +++ NAME @
   TIMESTAMP ! reason` (fields optional).
6. List closed threads and offer to remove them. Remove without asking only
   if the front matter has `threads: { autoremove_closed: true }`. Removing
   deletes the thread, its `[?label]` anchors, and the `==` around range
   anchors.
7. Report what you changed and ask the user to reload the file.

If `mdthread.py` (markdown-thread's reference parser) is available, use it:
`list --json`, `check`, `reply`, `close`, `remove`.
