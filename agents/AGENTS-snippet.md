# Markdown Thread — instructions for agents

<!-- Paste this section into AGENTS.md, CLAUDE.md or similar. Spec v0.2
     (2026-10-08). -->

## Markdown threads

Markdown files in this project may contain discussion threads for you. Full
rules: SPEC.md of markdown-thread (spec v0.2).

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
answered, `+++` = closed. A user's follow-up is a `-->` after a `<--`, so
follow-ups (and `-->` after `+++`, which reopens) are simply open threads.

**When asked to process a file:**

1. Find every thread. If two threads share a label, don't write to them;
   report it, and still reply to every other thread.
2. For each open thread, read all its messages in order (a follow-up
   answers or questions the `<--` before it, often yours) and the anchored
   text and context, then append at the end of the thread: a blank `>` line,
   `> <-- TOOL/MODEL @ YYYY-MM-DDTHH:MM±HH:MM` (local time with offset), and
   the reply, each line prefixed like the thread's other lines (keep list
   indentation).
3. Reply exactly once to every open thread, even if the reply is only a
   question. Don't reply to answered or closed threads. Text the user wrote
   under your reply without a `-->` line is part of your message: don't
   reply; ask the user to put it under `-->`.
4. Don't change messages, labels, anchors or body text unless a thread asks;
   propose body changes in the reply first. A `-->` "yes" to your proposal is
   the go-ahead: apply it and say so in the reply. Keep `==text== [?label]`
   together: added words go after the label token. Make edits one at a
   time, never in parallel.
5. Questions: if you need something from the user to answer an open thread,
   ask it in your reply to that thread (don't guess). Open a new thread only
   when the user explicitly told you to leave questions in the file: a
   header with the new label alone, then `> <-- TOOL/MODEL @ TIMESTAMP` as
   the second line and the question below (it waits for the user as
   `answered`). Never write `> [?label] question` yourself: that is the
   user's form. Ask everything else in the conversation, not in the file.
   Several `-->` messages since your last reply get one reply covering all.
6. Close threads only when asked: blank `>` line, then `> +++ NAME @
   TIMESTAMP ! reason` (fields optional). Do multi-step requests in the
   order given; removing closed threads also removes ones you just closed.
7. Read each close reason: it may answer your last question or ask for a
   change. Don't reply to closed threads or act on a reason by yourself;
   report it and ask in the conversation. Reply to a closed thread only when
   the user explicitly asks you to; the reply makes it `answered`.
8. List closed threads and offer to remove them. Remove without asking only
   if the front matter has `threads: { autoremove_closed: true }`. Removing
   deletes the thread, its `[?label]` anchors, and the `==` around range
   anchors.
9. Report what you changed and ask the user to reload the file.

If `mdthread.py` (markdown-thread's reference parser) is available, use it:
`list --json`, `check`, `reply`, `ask`, `close`, `remove`.
