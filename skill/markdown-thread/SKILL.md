---
name: markdown-thread
description: Use for [?label] threads, follow-ups, comments in .md files.
version: 0.2.0
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
Thread spec v0.2 (`references/protocol.md`): reply to open threads and the
user's follow-ups, read the user's answers to your questions, ask questions
in threads when told to, close threads, and remove closed ones. All parsing and editing goes through
`scripts/mdthread.py` (Python 3.10+, standard library only), so markers,
quoting and anchors stay valid.

## When to Use

- "reply to the threads in X.md", "answer my comments in X", "process the
  open threads"
- follow-ups: "I replied in X.md", "answer my follow-ups", "check my answers
  in the threads", "continue the discussion in X.md"
- "close [?label] in X.md", "remove the closed threads"
- "leave your questions as threads in X.md", "ask me in the file"
  (permission to open question threads with `ask`)
- A document you read contains block quotes starting with `> [?label]`:
  load this skill before replying to, reviewing or editing it.

Don't use for: Markdown footnotes, GitHub review comments, or editing a
document's body (unless a thread asks for it and the user agrees).

## How a discussion moves

| Thread ends with | State | Who acts |
|---|---|---|
| the opener, or a user `-->` follow-up | `open` | you reply |
| your (or another responder's) `<--` | `answered` | the user |
| `+++` (close line, optional `! reason`) | `closed` | nobody; offer removal |

The user's follow-up is a `-->` message after a `<--`, so every follow-up
shows up as an `open` thread, and a `-->` after `+++` reopens a closed thread.
`list --state open` finds both kinds. There is no separate "follow-up" state.

You open a thread only when the user explicitly tells you to put your
questions in the document, and only with `ask`: it writes a label-only header
and your `<--` question, so the thread is `answered` (waiting for the user)
and shows that you asked. Never write `> [?label] question` yourself: that
form is the user's opener, it reads as the user's question and leaves the
thread `open`, so a later run would answer its own question.

## Where your questions go

- **In the thread**, as part of your `<--` reply, when you reply to an open
  thread (its opener or a user follow-up) and need something from the user
  to answer it. The thread becomes `answered` and waits for the user's `-->`.
- **In a closed thread, only when the user explicitly asks** you to reply
  there (for example to answer or question its close reason): use
  `reply --force`. Your reply makes the thread `answered`, waiting for the
  user; say so in the report. An `answered` thread is waiting for the user:
  don't add to it, ask in the conversation instead.
- **In new threads, only when the user explicitly told you** to leave
  questions in the document (in the conversation or in a thread message):
  one `ask` per question, anchored at the text it is about.
- **Everywhere else in the conversation** (chat, the clarify tool): questions
  about the task, about parts of the document no open thread covers, and
  whether to act on a close reason.

## Situations

| Situation | What to do |
|---|---|
| New thread: only the opener | Answer it. |
| Follow-up `-->` after a `<--` | Read the whole thread, answer the latest `-->` in its light. |
| Several `-->` messages since the last `<--` | Answer all of them in one reply. |
| Follow-up answers your question or approves your proposal ("yes, do it") | Act on it: apply the change, then say in the reply what you changed. |
| Follow-up rejects or corrects your proposal | Don't apply it; acknowledge, and revise or ask. |
| Follow-up after `+++` (reopened) | Treat as a follow-up; the earlier close reason is context. |
| You lack information to answer | Ask in your reply; don't guess. |
| Thread asks for a body change, no approval yet | Propose it in the reply; apply only if the request explicitly says to. |
| Thread mentions another thread or section | Answer in this thread; don't write in the other thread. |
| `answered` thread (ends with any `<--`, also another responder's) | Skip it: it waits for the user. |
| `closed` thread with a reason that answers you or asks for a change | Don't reply or act; report it and ask in the conversation. |
| User explicitly asks you to reply to a closed thread | `reply --force`; the thread becomes `answered`. Report it. |
| `closed` thread, nothing to act on | Offer removal (or remove, if the front matter allows it). |
| `empty` thread (label only) | Skip it and report it. |
| Duplicate label | Don't write to those threads; report the lines. Reply to all other threads as usual. |
| User text under your `<--` without a `-->` marker | It is part of your message, so the thread is `answered`. Don't reply (not even with `--force`) and don't edit it; in the report, quote it and ask the user to put it under a `-->` line. |
| A question no open thread covers | Ask in the conversation, not in the file. |
| User told you to leave your questions in the file | One `ask` per question, from the bottom of the file up. Don't also ask them in the conversation. |
| `answered` thread you opened with `ask` | Skip it: it waits for the user's `-->`. |

## Quick Reference

`M` = `<skill_dir>/scripts/mdthread.py` (`skill_dir` is shown by `skill_view`).

```
python3 M list FILE [--state open|answered|closed|empty] [--json]
python3 M check FILE                      # exit 1 on errors
python3 M reply FILE LABEL --name NAME (--body TEXT | --body-file PATH) [--force] [--write]
python3 M ask FILE LABEL --name NAME (--body TEXT | --body-file PATH)
              [--line N [--text EXACT]] [--write]   # only when told to (above)
python3 M close FILE LABEL [--name NAME] [--now] [--reason TEXT] [--write]
python3 M remove FILE (LABEL... | --closed) [--write]
python3 M now                             # timestamp for a <-- marker
```

Edit commands print a diff and change nothing without `--write`. `list
--json` gives every thread with all its messages in order: `kind` is
`opener`, `annotator` (`-->`), `responder` (`<--`) or `close` (with `reason`).

## Procedure

1. **Inventory.** `terminal(command="python3 M check FILE")`, then
   `terminal(command="python3 M list --json FILE")`. Done when you know every
   thread's label, state, messages and anchors, and every error. Open threads
   are new questions, follow-ups and reopened threads alike.
2. **Errors.** A `duplicate-label` error blocks only the threads with that
   label: do not write to them, and tell the user which lines collide. It
   never blocks the other threads: reply to them in the same run, don't wait
   for the duplicate to be fixed.
3. **Read the whole thread.** For each `open` thread, read all its messages
   in order, not just the last one: a follow-up answers, questions or
   corrects the `<--` before it, often yours from an earlier run. Then
   `read_file` the anchored lines and enough surrounding text. A thread
   without anchors is about the whole document. Done when every open thread
   has a drafted answer to its latest annotator messages (Situations).
4. **Answers to your questions.** If the `<--` before the follow-up asked a
   question or proposed something, the follow-up is the user's answer: act
   on it. "Yes, do it" to a proposed change is the agreement step 6 needs;
   apply the change and say in the reply what you changed. If the answer is
   still not enough, ask again in the reply.
5. **Reply.** Every open, non-duplicate thread gets exactly one reply, even
   when all you can write is a question. For each: `write_file` the reply
   body (plain Markdown, no `>` prefixes) to a scratch file, then
   `terminal(command="python3 M reply FILE 'LABEL' --name NAME --body-file BODY --write")`.
   NAME is `hermes/` plus your full model id as configured (for example
   `hermes/claude-haiku-4-5`, not `hermes/haiku`), or
   `hermes:<profile>/<model>` outside the default profile. The script adds
   the blank line, the marker and the timestamp. Questions you need answered
   go in this reply, not in your report. Done when each reply command
   printed `wrote FILE`.
6. **Requested changes.** If a thread asks to change the body, describe the
   change in the reply and apply it only after the user agrees (a `-->`
   follow-up, step 4) or if the request explicitly says to apply it. Never
   edit messages, labels or anchors by hand. Keep `==text== [?label]`
   together: put added words after the label token, never between `==` and
   `[?label]`, or the range anchor becomes a point anchor.
7. **New questions (only when told to).** For each question, pick a short
   new label and the body line it is about, then
   `python3 M ask FILE 'LABEL' --name NAME --line N [--text 'EXACT WORDS'] --body-file BODY --write`.
   `--text` marks words on that line as `==EXACT WORDS==`; without `--line`
   the thread is about the whole document and goes at the end. Run the
   `ask` commands one after another, from the bottom of the file up, in one
   terminal command joined with `&&`, so line numbers stay valid.
8. **Verify.** Re-run `check` and `list`. Done when no `open` thread is left
   (except duplicates), replied and asked threads are `answered`, range
   anchors you touched are still `r` in `list`, there are no new errors, and
   no warnings point at lines you wrote.
9. **Closed threads.** For each `closed` thread, read the close reason
   (`! ...`). It is the user's last word and may answer your last question
   ("b, go ahead") or ask for something. Do not reply to a closed thread
   (unless the user explicitly asks you to) and do not change the document
   because of a reason on your own: a closed
   thread gets no reply, so nothing would record that you acted. List such
   reasons in the report and ask in the conversation whether to apply them.
   Then:
   - `front_matter.autoremove_closed` true: run `remove FILE --closed --write`
     (after any confirmed changes) and report what was removed;
   - otherwise list them (label, closer, reason) and offer to remove them.
   Close a thread only when the user asks:
   `close FILE LABEL --name NAME --now [--reason TEXT] --write`.
   Run a multi-step request in the order the user gave it. `remove --closed`
   removes every thread that is closed at that moment, including ones you
   just closed: to remove the old closed threads and close another, remove
   first (or remove by label).
10. **Report.** Threads replied to (follow-ups marked as such), questions you
    asked in threads (replies and `ask`), changes applied, threads closed and
    removed, close reasons waiting for a decision, errors, and a reminder to
    reload the file in the editor (`:e` in Neovim). Ask the conversation
    questions here.

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
- `answered` threads are waiting for the user, including threads you opened
  with `ask`: do not reply again.
- Never create or edit threads by hand (`write_file`, `patch`): use `reply`,
  `ask`, `close` and `remove`. Body edits the user approved are the only
  hand edits.
- Never run edit commands in parallel (several tool calls at once): each one
  rewrites the file and shifts line numbers. Run them one at a time; the
  script refuses to write if the file changed since it read it.
- `reply --force` works only on closed threads and makes them `answered`:
  use it only when the user explicitly asks you to reply to that closed
  thread, never on your own (spec §9 rule 2). It refuses answered threads.
- A question you need answered to reply to an open thread goes in that
  reply, not in the conversation; any other question goes in the
  conversation, or in an `ask` thread when the user told you to.

## Verification

- `python3 M check FILE` exits 0 (or only pre-existing errors remain).
- `python3 M list FILE --state open` lists no thread you were asked to answer.
- The final report names every thread touched and every close reason left
  for the user to decide.
