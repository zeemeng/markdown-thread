# Markdown Thread — User Guide

How to discuss a Markdown document with an agent inside the document itself.
The rules are in [SPEC.md](SPEC.md); this guide covers everyday use.
(2026-10-08, spec v0.2)

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

If the agent needs something from you to answer, it asks in its reply. Answer
with a follow-up (next section); the agent picks it up on the next run.

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

Then ask the agent to "answer my follow-ups in notes/dispatch.md" (or just
"process the threads"): a thread that ends with your `-->` is open again. If
the agent proposed a change, "yes, do it" in a follow-up lets it apply the
change; it says in its reply what it changed.

Start every follow-up with a `-->` line. Text you type straight under the
agent's reply, without `-->`, becomes part of the agent's message: the thread
still looks answered and the agent won't see it as yours.

### Questions from the agent

The agent asks in the document only in its replies to your open threads, or
when you tell it to, for example "leave your questions about dispatch.md as
threads". Then it opens threads of its own, without an opening question:

<!-- mdthread: example -->
```markdown
The dispatcher ==sleeps== [?sleep length] between ticks.

> [?sleep length]
> <-- agent/model-x @ 2026-10-08T15:00-04:00
> Should the sleep stay fixed, or back off when idle?
```

These wait for you like any answered thread: reply with `-->`. Otherwise the
agent asks you in the conversation, not in the file.

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

The reason is your last word on the thread. If it answers the agent's
question or asks for a change ("b, go ahead"), the agent doesn't act on it by
itself: it reports the reason and asks you first, because a closed thread gets
no reply that would show the change was made. To have the agent act, reply
with a `-->` follow-up instead of closing. You can also tell the agent to
reply in a closed thread, for example "reply to my close note in [?why
ticks]"; its reply makes the thread answered again.

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

**Neovim** with markdown-thread.nvim (rendering through render-markdown):

- `:MdThread new` adds an anchor and a thread at the word under the cursor or
  around a selection; an empty label is named from the text.
- `:MdThread followup` adds the blank `>` line and `-->` at the end of the
  thread under the cursor; `:MdThread close [reason]` closes it.
- `:MdThread list` shows the threads in a location list that follows your
  edits.
- With Enter wired to the plugin (see its README), Enter on an empty `> ` line
  inside a thread keeps the thread going; a second Enter ends it.
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
