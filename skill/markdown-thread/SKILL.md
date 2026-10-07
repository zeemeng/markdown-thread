---
name: markdown-thread
description: Answer, close and remove [?label] threads in Markdown.
version: 0.1.0
author: Max Meng, Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [markdown, annotation, review, threads, comments]
    related_skills: []
---

# Markdown Thread

Process discussion threads written in a Markdown document under the Markdown
Thread spec v0.1 (`references/protocol.md`): reply to open threads, close
threads, and remove closed ones. All parsing and editing goes through
`scripts/mdthread.py` (Python 3.10+, standard library only), so markers,
quoting and anchors stay valid.

## When to Use

- "reply to the threads in X.md", "answer my comments in X", "process the
  open threads"
- "close [?label] in X.md", "remove the closed threads"
- A document contains block quotes starting with `> [?label]` and the user
  asks about them.

Don't use for: Markdown footnotes, GitHub review comments, or editing a
document's body (unless a thread asks for it and the user agrees).

## Quick Reference

`M` = `<skill_dir>/scripts/mdthread.py` (`skill_dir` is shown by `skill_view`).

```
python3 M list FILE [--state open|answered|closed|empty] [--json]
python3 M check FILE                      # exit 1 on errors
python3 M reply FILE LABEL --name NAME (--body TEXT | --body-file PATH) [--write]
python3 M close FILE LABEL [--name NAME] [--now] [--reason TEXT] [--write]
python3 M remove FILE (LABEL... | --closed) [--write]
python3 M now                             # timestamp for a <-- marker
```

Edit commands print a diff and change nothing without `--write`.

## Procedure

1. **Inventory.** `terminal(command="python3 M check FILE")`, then
   `terminal(command="python3 M list --json FILE")`. Done when you know every
   thread's label, state, messages and anchors, and every error.
2. **Errors.** A `duplicate-label` error blocks every thread with that label:
   do not write to them; tell the user which lines collide. Other threads can
   proceed.
3. **Read context.** For each `open` thread, `read_file` the anchored lines
   and enough surrounding text to answer. A thread without anchors is about
   the whole document. Done when every open thread has a drafted answer.
4. **Reply.** For each open, non-duplicate thread, once: `write_file` the
   reply body (plain Markdown, no `>` prefixes) to a scratch file, then
   `terminal(command="python3 M reply FILE 'LABEL' --name NAME --body-file BODY --write")`.
   NAME is `hermes/<model>`, or
   `hermes:<profile>/<model>` outside the default profile. The script adds the
   blank line, the marker and the timestamp. Done when each reply command
   printed `wrote FILE`.
5. **Requested changes.** If a thread asks to change the body, describe the
   change in the reply and apply it only after the user agrees (or if the
   request explicitly says to apply it). Never edit messages, labels or
   anchors by hand.
6. **Verify.** Re-run `check` and `list`. Done when replied threads are
   `answered`, there are no new errors, and no warnings point at lines you
   wrote.
7. **Closed threads.** If `list` shows `closed` threads:
   - `front_matter.autoremove_closed` true: run `remove FILE --closed --write`
     and report what was removed;
   - otherwise list them (label, closer, reason) and offer to remove them.
   Close a thread only when the user asks:
   `close FILE LABEL --name NAME --now [--reason TEXT] --write`.
8. **Report.** Threads replied, closed and removed; errors; a reminder to
   reload the file in the editor (`:e` in Neovim).

## Pitfalls

- Text on a marker line is never message text: `--> why?` makes `why?` a
  name. The script never writes that; don't hand-write markers.
- `+++` only closes after a blank `>` line or as a thread's second line; a
  `+++` inside a message (a pasted diff) is text. `check` warns with
  `close-without-blank`.
- Labels match case-insensitively with whitespace collapsed; quote the label
  as shown by `list`, or any spelling with the same key.
- A thread ends at the first line that does not start with `>`. Replies go
  only at the end of a thread; the script handles indentation inside lists.
- The user may have the file open; edits on disk need a reload there.
- `answered` threads are waiting for the user: do not reply again.

## Verification

- `python3 M check FILE` exits 0 (or only pre-existing errors remain).
- `python3 M list FILE --state open` lists no thread you were asked to answer.
- The final report names every thread touched.
