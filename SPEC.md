# Markdown Thread — Specification

Version 0.1 (draft, 2026-10-06)

Markdown Thread is a plain-text convention for discussion threads inside a
Markdown document. A thread is a block quote placed near the text it discusses;
anchors in the text point at it. Any Markdown renderer shows threads as
ordinary quotes; tools that implement this specification can find, answer,
close and remove them.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are to be interpreted
as described in RFC 2119.

## 1. Example

<!-- mdthread: example -->
```markdown
The dispatcher ==polls every five seconds== [?why ticks] and then sleeps.

> [?why ticks] Why poll instead of reacting to events?
>
> <-- agent/model-x @ 2026-10-06T19:57-04:00
> Polling keeps the dispatcher stateless across restarts.
>
> --> Alice @ 2026-10-06T20:03
> Fair, but five seconds is slow.
>
> <-- agent/model-x @ 2026-10-06T20:05-04:00
> One second would cost about 2 % CPU; I can measure it.
>
> +++ Alice @ 2026-10-06 ! keep five seconds for now
```

The thread `why ticks` has an opener message, three marked messages and a
closing line. Its state is closed (§6).

## 2. Terms

- **Annotator**: whoever opens a thread or writes `-->` messages, usually a
  person.
- **Responder**: whoever answers with `<--` messages, usually an AI agent. A
  responder may also be a person.
- **Content line**: a line of a block quote with its quote marker removed
  (§3.1).
- **Body**: every part of the document that is not front matter, a thread, a
  code block or an HTML comment (§3.3).

## 3. Document structure

### 3.1 Lines and block quotes

A document is split into lines at LF; a trailing CR on a line is ignored.

A **quote line** is a line whose first non-whitespace character is `>`. Its
**content** is the remainder after that `>` and at most one following space
or tab.

A **block quote** is a maximal run of consecutive quote lines. A line that is
not a quote line, including a blank line, ends the block quote.

Note: CommonMark lets a non-quote line continue a paragraph inside a block
quote ("lazy continuation"). This specification does not: such a line ends the
thread (§4).

### 3.2 Front matter

If the first line of the document is exactly `---`, the lines up to and
including the next line that is exactly `---` or `...` are YAML front matter.
If the first line is exactly `+++`, the lines up to and including the next
line that is exactly `+++` are TOML front matter. If no closing line exists,
there is no front matter.

### 3.3 Excluded regions

The following are never part of the body, so they contain no anchors and
start no threads:

1. front matter (§3.2);
2. fenced code blocks: a line whose first non-whitespace characters are at
   least three backticks or three tildes opens a fence (for backticks, only
   if the rest of the line contains no backtick); the fence closes at a
   line consisting only of whitespace and at least as many of the same
   character, or at the end of the document (or of the enclosing block quote);
3. code spans: text between matching runs of backticks on one line;
4. HTML comments (`<!--` … `-->`), which may span lines;
5. indented code blocks as defined by CommonMark. Implementations MAY omit this
   rule; they MUST then document it.

Inside a thread, fenced code blocks are recognised on content lines; lines
inside them are never markers (§5). HTML comments are not recognised inside
threads: a content line `-->` that closes a multi-line comment in a message is
a marker line. Write comments in messages on one line.

## 4. Threads

A **thread** is a block quote outside the excluded regions (§3.3) whose first
content line starts with a label token (§4.1) followed by whitespace or the
end of the line. The label token MUST be complete on that line. This first
line is the **header**. The block quote's lines are the thread's lines; the thread ends
where the block quote ends.

A block quote nested inside another block quote (content starting with `>`)
is not a thread in this version. Nested threads are reserved for a future
version.

A header label applies to the thread only on the header line. A content line
inside a thread that starts with a label token is message text; it does not
start a new thread. Two threads MUST be separated by at least one line that
is not a quote line.

### 4.1 Labels

A **label token** is `[?`, followed by one or more characters other than `[`
and `]`, followed by `]`. The **label** is the text between `[?` and `]`.

A label's **key** is computed by:

1. replacing every run of whitespace (including line breaks) with one space;
2. removing leading and trailing spaces;
3. applying Unicode default case folding. Implementations without Unicode case
   folding MUST at least fold ASCII letters and SHOULD document the
   difference.

A label token whose key is empty (for example `[?]` or `[?  ]`) is not a label
token.

Two labels are the same if their keys are equal. A document MUST NOT contain
two threads with the same key. Implementations MUST report duplicates as an
error, and responders MUST NOT write to any thread that has a duplicate.
Label tokens with a duplicated key are not anchors.

## 5. Messages

### 5.1 Marker lines

A **marker line** is a content line of a thread, outside fenced code within
the thread, that starts with one of these markers followed by whitespace or
the end of the line:

| Marker | Meaning | Written by |
|---|---|---|
| `-->` | message | annotator |
| `<--` | message | responder |
| `+++` | close | anyone |

The header line is never a marker line. A `+++` line is a marker line only if
it is the second line of the thread or the previous content line is blank.
This keeps `+++` lines of pasted diffs inside message text.

`-->` and `<--` lines SHOULD be preceded by a blank content line unless they
are the second line of the thread; without it, most renderers merge the marker
into the previous paragraph.

### 5.2 Marker fields

The text after the marker is split into fields:

```
message-marker = ("-->" / "<--") [ws name] [ws "@" ws? timestamp [ws ignored]]
close-marker   = "+++" [ws name] [ws "@" ws? timestamp [ws ignored]]
                 [ws "!" ws reason]
```

Parsing, applied to the text after the marker:

1. **Reason** (`+++` only). The first `!` that is at the start of the text or
   preceded by whitespace, and is followed by whitespace or the end of the
   text, starts the reason. The reason is the rest of the text after the `!`,
   trimmed. The text before the `!` is parsed by the next steps.
2. **Timestamp delimiter.** The first `@` that is at the start of the text or
   preceded by whitespace, and is followed by whitespace, a digit or the end
   of the text, is the delimiter. Without a delimiter, the whole text is the
   name.
3. **Name.** The text before the delimiter, trimmed. It may contain spaces and
   `@` (for example `@alice:example.org`). An empty name means no name.
4. **Timestamp.** After the delimiter and optional whitespace, the longest
   prefix matching the timestamp format (§5.3). Anything else after the
   delimiter is ignored. If nothing matches, there is no timestamp.

All fields are optional. Text written on a marker line is never message text.

### 5.3 Timestamps

```
timestamp = date [ "T" time [ offset ] ]
date      = 4DIGIT "-" 2DIGIT "-" 2DIGIT
time      = 2DIGIT ":" 2DIGIT [ ":" 2DIGIT ]
offset    = "Z" / ( "+" / "-" ) 2DIGIT ":" 2DIGIT
```

This is a subset of ISO 8601. Responders SHOULD write the full form with
minutes and an offset, for example `2026-10-06T19:57-04:00`.

### 5.4 Message bodies

- **Opener**: the text after the header's label token, plus the content lines
  that follow it up to the first marker line. If both are empty, there is no
  opener. The opener counts as an annotator message.
- A `-->` or `<--` message's body is the content lines after its marker line
  up to the next marker line or the end of the thread.
- A `+++` line has no body. Content lines between a `+++` line and the next
  marker line belong to no message; implementations SHOULD warn about
  non-blank ones.

Leading and trailing blank lines are not part of a body. A body may contain
any Markdown, written as content lines.

## 6. State

A thread's state comes from its last message or close line:

| Last item | State |
|---|---|
| none | `empty` |
| opener or `-->` | `open` |
| `<--` | `answered` |
| `+++` | `closed` |

A `-->` after a `+++` reopens the thread.

## 7. Anchors

An **anchor** is a label token in the body (§3.3) whose key matches a thread
in the document. A label token that matches no thread is plain text.

A label token is not an anchor when it is:

- preceded by `!` (an image), `\` (escaped) or `]`; or
- followed by `(` or `[` (a link); or
- the label of a link reference definition (`[?x]: …` at the start of a
  line).

A label token in the body MAY span a line break (§4.1).

### 7.1 Highlights and range anchors

A **highlight** is `==`, followed by text that does not begin or end with
whitespace and does not contain `==` or a blank line, followed by `==`.
Highlights are matched left to right, without overlap, within one block of
body text.

A **block of body text** is a run of consecutive non-blank body lines. A new
block also starts at a line that begins (after indentation and any `>`
markers) with `#` (a heading), a list marker (`-`, `*` or `+`, or digits
followed by `.` or `)`, then a space), or that is a thematic break, and after
a heading line. This approximates CommonMark's paragraphs closely enough for
anchors.

An anchor directly after a highlight, separated by nothing or by whitespace
that contains at most one line break, is a **range anchor**: the highlighted
text is the text the thread discusses. Any other anchor is a **point anchor**.

Several anchors may refer to the same thread.

### 7.2 Link definitions

If a link reference definition uses a thread's label (`[?x]: https://…`),
renderers show its anchors as links. Implementations SHOULD warn; the thread
remains a thread.

## 8. Operations

### 8.1 Replying

A responder adds a message only at the end of a thread:

1. a blank content line, unless the thread ends with one;
2. `<-- NAME @ TIMESTAMP`, where NAME identifies the responder and TIMESTAMP
   is the full form (§5.3);
3. the body as content lines.

The quote prefix of the new lines SHOULD match the thread's header line
(including indentation inside list items).

### 8.2 Closing

Closing appends a blank content line (if needed) and a `+++` line. Fields are
optional (§5.2).

### 8.3 Removing

Removing a thread:

1. deletes the thread's lines;
2. deletes each of its anchors and the whitespace between a range anchor and
   its highlight;
3. replaces each range anchor's highlight with its text (removes the `==`
   pairs).

Implementations SHOULD tidy the result: no doubled spaces where an anchor
was, no empty lines left by an anchor, and no runs of blank lines where the
thread was.

### 8.4 Front matter option

```yaml
threads:
  autoremove_closed: true
```

or `threads: { autoremove_closed: true }`. When true, a responder that has
processed a document MAY remove closed threads without asking. When absent or
false, it MUST NOT remove threads unless asked.

## 9. Responder rules

A responder:

1. writes only when asked to process a document;
2. replies only to `open` threads, once each per request;
3. MUST NOT change existing messages, labels, anchors or body text unless a
   thread or the user asks for it; it SHOULD propose such changes in a reply
   first;
4. closes a thread only when asked;
5. removes threads only when asked or when §8.4 allows it;
6. reports duplicates (§4.1) and does not write to those threads.

## 10. Rendering notes (non-normative)

Checked with Pandoc 3.7 and GitHub's Markdown API on 2026-10-06:

- `[?label]` renders as literal text in both, unless a link definition uses
  the label.
- Content lines without a blank line between them form one paragraph. The
  blank line before a marker starts a new paragraph for each message; the
  marker and the first line of its body share that paragraph (Pandoc, GitHub
  file view: `<– bot @ 2026-10-06 Reply.`). GitHub's comment rendering keeps
  the line break.
- Pandoc needs a blank line before a block quote; without it the quote merges
  into the preceding paragraph. GitHub does not.
- Pandoc's smart punctuation renders `-->` as `–>` and `<--` as `<–`.
- `==text==` is a highlight in Obsidian, Zettlr and render-markdown.nvim, and
  in Pandoc only with the `mark` extension. GitHub shows it literally.
- `+++` and `!` render literally.

## 11. Versioning

The version is `MAJOR.MINOR`. A change that alters how an existing document is
parsed increments MAJOR. Additions that leave existing documents' parses
unchanged increment MINOR.

## 12. Reserved for future versions

- Threads nested in block quotes (replies to replies, branching).
