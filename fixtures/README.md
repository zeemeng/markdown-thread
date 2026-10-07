# Conformance fixtures

Implementation-independent test cases for SPEC.md v0.1. Any implementation
should reproduce them exactly.

## `parse/`

| File | Content |
|---|---|
| `NAME.md` | input document |
| `NAME.json` | expected parse result |

Parse result (comments added for explanation):

```jsonc
{
  "spec": "0.1",
  "front_matter": { "present": true, "autoremove_closed": false },
  "threads": [
    {
      "label": "why ticks",            // as written between "[?" and "]"
      "key": "why ticks",              // §4.1
      "start_line": 3, "end_line": 14, // 1-based, inclusive
      "state": "closed",               // empty | open | answered | closed
      "duplicate": false,
      "messages": [
        { "kind": "opener", "line": 3, "name": null, "timestamp": null,
          "body": ["Why poll instead of reacting to events?"] },
        { "kind": "close", "line": 14, "name": "Alice",
          "timestamp": "2026-10-06", "reason": "keep five seconds for now" }
      ],
      "anchors": [
        { "kind": "range", "start": [1, 44], "end": [1, 56],
          "highlight": "polls every five seconds" }
      ]
    }
  ],
  "errors": [ { "code": "duplicate-label", "line": 5 } ]
}
```

- `kind` is `opener`, `annotator` (`-->`), `responder` (`<--`) or `close`
  (`+++`). `line` is the header line for the opener, else the marker line.
- `body` lists content lines (quote marker and one space removed), without
  leading or trailing blank lines. Close items have `reason` instead.
- Anchor positions are `[line, column]`: 1-based line, 0-based column in
  UTF-8 bytes; `end` is exclusive and covers the label token only.
- `highlight` is the highlighted text with whitespace runs collapsed to one
  space, or `null` for point anchors.
- `errors` holds spec-level errors only (duplicate labels). Warnings are
  implementation-specific and are not part of the fixtures.

## `ops/`

| File | Content |
|---|---|
| `NAME.md` | input document |
| `NAME.op.json` | operation |
| `NAME.out.md` | expected document afterwards |

Operations:

- `{"op": "reply", "label", "name", "timestamp", "body"}` (§8.1)
- `{"op": "close", "label", "name"?, "timestamp"?, "reason"?}` (§8.2)
- `{"op": "remove", "labels": [...]}` or `{"op": "remove", "closed": true}`
  (§8.3, including the reference implementation's tidy rules)

## Cases

| Case | Covers |
|---|---|
| `parse/basic` | the SPEC §1 example |
| `parse/opener-forms` | short, multi-line, second-line and long-form openers |
| `parse/states` | empty, open, answered, closed, reopened |
| `parse/labels` | key normalisation, wrapped anchor, empty tokens, `[?x](…)` and `[?x]:` headers, Unicode |
| `parse/ordinary-quotes` | `[sic]` with markers, label not on the first line, callout, nested quote |
| `parse/marker-fields` | names with spaces and `@`, `@` before a digit, bad and partial timestamps, reasons with `@`, `Alice!` |
| `parse/close-rule` | `+++` in a pasted diff, `+++` on the second line |
| `parse/code` | fences, tildes, code spans, comments (single and multi-line), markers in message code, fences in ordinary quotes |
| `parse/anchors` | range vs point, gaps, wrapped and multi-line highlights, exclusions, list item boundaries, heading, ordinary quote |
| `parse/duplicates` | duplicate keys; anchors to them are ignored |
| `parse/lists` | threads inside list items, mixed indentation |
| `parse/front-matter-yaml` | block option form; quote inside front matter |
| `parse/front-matter-flow` | flow option form, `TRUE` |
| `parse/front-matter-toml` | `+++` front matter, option ignored |
| `parse/link-definition` | `[?docs]: url` with a thread `docs` |
| `parse/boundaries` | quote right after a paragraph, lazy continuation, two headers in one quote, text after close |
| `parse/crlf` | CRLF line endings |
| `ops/reply-basic` | multi-paragraph reply |
| `ops/reply-after-blank` | thread already ends with a blank `>` line |
| `ops/reply-in-list` | indented thread, case-insensitive label, code in the reply |
| `ops/close-fields` | name, timestamp and reason |
| `ops/close-bare` | `+++` alone |
| `ops/remove-closed` | range, wrapped, point and line-start anchors; threads at start and end |
| `ops/remove-label` | remove one thread by label |
