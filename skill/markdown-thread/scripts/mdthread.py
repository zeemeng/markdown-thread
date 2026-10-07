#!/usr/bin/env python3
"""mdthread: reference implementation of the Markdown Thread spec v0.1.

Parses threads, anchors and states (SPEC.md), reports diagnostics, and edits
documents: reply, close, remove. Standard library only; Python 3.10+.

Positions in JSON output: lines are 1-based; columns are 0-based UTF-8 byte
offsets, end exclusive.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import json
import re
import sys
import unicodedata

SPEC_VERSION = "0.1"

# --- lexical rules (SPEC §3-§7) ----------------------------------------------

QUOTE_RE = re.compile(r"^([ \t]*)>(?:[ \t])?")          # §3.1 quote line + one space
FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})")            # §3.3.2 opening fence
LABEL_TOKEN_RE = re.compile(r"\[\?([^\[\]]+)\]")          # §4.1
MARKER_RE = re.compile(r"^(-->|<--|\+\+\+)(?=[ \t]|$)(.*)$")  # §5.1
REASON_RE = re.compile(r"(?:^|(?<=\s))!(?=\s|$)")          # §5.2 step 1
AT_RE = re.compile(r"(?:^|(?<=\s))@(?=\s|\d|$)")           # §5.2 step 2
TIMESTAMP_RE = re.compile(                                # §5.3
    r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?)?")
FULL_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})$")
HIGHLIGHT_RE = re.compile(r"==(?!\s)((?:(?!==).)+?)(?<!\s)==", re.S)  # §7.1
CODE_SPAN_RE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")  # maximal backtick runs
BLOCK_START_RE = re.compile(                              # §7.1 block of body text
    r"^[ \t]*(?:>[ \t]?)*[ \t]*(?:#|[-*+][ \t]|\d+[.)][ \t]|"
    r"(?:\*[ \t]*){3,}$|(?:-[ \t]*){3,}$|(?:_[ \t]*){3,}$)")
HEADING_RE = re.compile(r"^[ \t]*(?:>[ \t]?)*[ \t]*#")
QUOTE_PREFIX_RE = re.compile(r"^[ \t]*(?:>[ \t]?)+")
FM_FLOW_RE = re.compile(r"^threads:\s*\{(.*)\}\s*(?:#.*)?$")
FM_BLOCK_RE = re.compile(r"^threads:\s*(?:#.*)?$")
FM_KEY_RE = re.compile(r"autoremove_closed\s*:\s*([A-Za-z]+)")
TRUE_WORDS = {"true", "True", "TRUE"}


def label_key(label: str) -> str:
    """§4.1: collapse whitespace, trim, Unicode default case folding."""
    return unicodedata.normalize("NFC", " ".join(label.split()).casefold())


def byte_col(line: str, idx: int) -> int:
    return len(line[:idx].encode("utf-8"))


def is_blank(s: str) -> bool:
    return s.strip() == ""


def now_timestamp() -> str:
    """Local time, minutes precision, with UTC offset (SPEC §5.3 full form)."""
    t = _dt.datetime.now().astimezone().replace(second=0, microsecond=0)
    return t.isoformat(timespec="minutes")


# --- model -------------------------------------------------------------------

class Message:
    def __init__(self, kind, line, name=None, timestamp=None, reason=None, body=None):
        self.kind = kind            # opener | annotator | responder | close
        self.line = line            # 0-based index of header/marker line
        self.name = name
        self.timestamp = timestamp
        self.reason = reason
        self.body = body or []

    def to_json(self):
        d = {"kind": self.kind, "line": self.line + 1, "name": self.name,
             "timestamp": self.timestamp}
        if self.kind == "close":
            d["reason"] = self.reason
        else:
            d["body"] = self.body
        return d


class Anchor:
    def __init__(self, kind, start, end, token_start, highlight=None, hl_span=None):
        self.kind = kind            # point | range
        self.start = start          # absolute offsets in document text
        self.end = end
        self.token_start = token_start
        self.highlight = highlight  # highlighted text, whitespace collapsed
        self.hl_span = hl_span      # (start, end) absolute offsets of ==...==


class Thread:
    def __init__(self, label, key, start, end, prefix):
        self.label = label
        self.key = key
        self.start = start          # 0-based first line
        self.end = end              # 0-based last line (inclusive)
        self.prefix = prefix        # raw text up to and including the header's `>`
        self.messages: list[Message] = []
        self.anchors: list[Anchor] = []
        self.duplicate = False

    @property
    def state(self) -> str:
        if not self.messages:
            return "empty"
        return {"opener": "open", "annotator": "open", "responder": "answered",
                "close": "closed"}[self.messages[-1].kind]


class Document:
    def __init__(self, text: str):
        self.text = text
        self.raw = text.split("\n")
        self.lines = [l[:-1] if l.endswith("\r") else l for l in self.raw]
        self.n = len(self.lines)
        self.offsets = []
        pos = 0
        for l in self.raw:
            self.offsets.append(pos)
            pos += len(l) + 1
        self.kind = ["body"] * self.n   # front_matter | code | thread | body
        self.masked = list(self.lines)  # body lines with code spans/comments blanked
        self.threads: list[Thread] = []
        self.diagnostics: list[dict] = []
        self.front_matter = {"present": False, "format": None, "autoremove_closed": False}
        self.linkdef_keys: dict[str, int] = {}
        self.comment_start: set[int] = set()
        self.quote_code: set[int] = set()   # fenced code inside block quotes
        self._parse()

    # diagnostics ---------------------------------------------------------
    def diag(self, severity, code, line, message):
        self.diagnostics.append({"severity": severity, "code": code,
                                 "line": line + 1, "message": message})

    def errors(self):
        return [d for d in self.diagnostics if d["severity"] == "error"]

    # position helpers ----------------------------------------------------
    def pos(self, offset: int) -> list[int]:
        """Absolute offset -> [line (1-based), byte column (0-based)]."""
        lo, hi = 0, self.n - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.offsets[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return [lo + 1, byte_col(self.raw[lo], offset - self.offsets[lo])]

    # parsing -------------------------------------------------------------
    def _parse(self):
        start = self._front_matter()
        self._regions(start)
        self._threads()
        self._duplicates()
        self._anchors()
        self.diagnostics.sort(key=lambda d: (d["line"], d["severity"] != "error", d["code"]))

    def _front_matter(self) -> int:
        """§3.2. Returns the first line index after front matter."""
        if not self.lines or self.lines[0] not in ("---", "+++"):
            return 0
        opener = self.lines[0]
        closers = ("---", "...") if opener == "---" else ("+++",)
        for i in range(1, self.n):
            if self.lines[i] in closers:
                for j in range(i + 1):
                    self.kind[j] = "front_matter"
                self.front_matter["present"] = True
                self.front_matter["format"] = "yaml" if opener == "---" else "toml"
                if opener == "---":
                    self._front_matter_option(self.lines[1:i])
                return i + 1
        return 0

    def _front_matter_option(self, fm_lines):
        """§8.4: `threads: { autoremove_closed: true }` or the block form."""
        for k, line in enumerate(fm_lines):
            m = FM_FLOW_RE.match(line)
            if m:
                km = FM_KEY_RE.search(m.group(1))
                self.front_matter["autoremove_closed"] = bool(km and km.group(1) in TRUE_WORDS)
                return
            if FM_BLOCK_RE.match(line):
                for sub in fm_lines[k + 1:]:
                    if sub and not sub[0].isspace():
                        break
                    km = FM_KEY_RE.match(sub.strip())
                    if km:
                        self.front_matter["autoremove_closed"] = km.group(1) in TRUE_WORDS
                        return
                return

    def _regions(self, start: int):
        """§3.3: fenced code (top level and inside block quotes), HTML comments,
        code spans. Thread detection happens later on the remaining lines."""
        fence = None          # (char, length, in_quote)
        in_comment = False
        for i in range(start, self.n):
            line = self.lines[i]
            qm = QUOTE_RE.match(line)
            if fence is not None:
                ch, ln, in_quote = fence
                if in_quote and not qm:
                    fence = None          # block quote ended: fence ends with it
                else:
                    content = line[qm.end():] if (in_quote and qm) else line
                    if re.match(r"^[ \t]*" + re.escape(ch) + "{" + str(ln) + r",}[ \t]*$", content):
                        fence = None
                    if in_quote:
                        self.quote_code.add(i)
                    else:
                        self.kind[i] = "code"
                    continue
            if in_comment:
                end = line.find("-->")
                if end < 0:
                    self.masked[i] = " " * len(line)
                    self.kind[i] = "comment"
                    continue
                self.masked[i] = " " * (end + 3) + line[end + 3:]
                in_comment = False
                if is_blank(line[end + 3:]):
                    self.kind[i] = "comment"
                    continue
                # text after the comment stays body (masked prefix), but the line
                # cannot start a thread because it starts inside a comment
                self.comment_start.add(i)
            content = line[qm.end():] if qm else line
            fm = FENCE_RE.match(content)
            if fm and not (fm.group(1)[0] == "`" and "`" in content[fm.end():]):
                fence = (fm.group(1)[0], len(fm.group(1)), bool(qm))
                if qm:
                    self.quote_code.add(i)
                else:
                    self.kind[i] = "code"
                continue
            masked = CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), self.masked[i])
            # HTML comments (possibly opening a multi-line one)
            out, j = [], 0
            while True:
                s = masked.find("<!--", j)
                if s < 0:
                    out.append(masked[j:])
                    break
                e = masked.find("-->", s + 4)
                out.append(masked[j:s])
                if e < 0:
                    out.append(" " * (len(masked) - s))
                    in_comment = True
                    break
                out.append(" " * (e + 3 - s))
                j = e + 3
            self.masked[i] = "".join(out)

    def _threads(self):
        """§4-§6: find block quotes whose first content line is a header."""
        i = 0
        while i < self.n:
            if self.kind[i] != "body" or i in self.comment_start or not QUOTE_RE.match(self.lines[i]):
                i += 1
                continue
            j = i
            while j + 1 < self.n and self.kind[j + 1] == "body" and QUOTE_RE.match(self.lines[j + 1]):
                j += 1
            self._quote(i, j)
            i = j + 1

    def _quote(self, s: int, e: int):
        qm = QUOTE_RE.match(self.lines[s])
        first = self.lines[s][qm.end():]
        tm = LABEL_TOKEN_RE.match(first)
        if not tm or not label_key(tm.group(1)) or not re.match(r"[ \t]|$", first[tm.end():]):
            inner = QUOTE_RE.match(first)
            if inner:
                im = LABEL_TOKEN_RE.match(first[inner.end():])
                if im and label_key(im.group(1)):
                    self.diag("warning", "nested-thread", s,
                              "threads nested in block quotes are not supported in v0.1")
            return
        prefix = self.lines[s][:self.lines[s].index(">") + 1]
        t = Thread(tm.group(1), label_key(tm.group(1)), s, e, prefix)
        for k in range(s, e + 1):
            self.kind[k] = "thread"
        content = []
        indent = qm.group(1)
        for k in range(s, e + 1):
            m = QUOTE_RE.match(self.lines[k])
            content.append(self.lines[k][m.end():])
            if m.group(1) != indent:
                self.diag("warning", "inconsistent-indent", k,
                          "thread line indented differently from the header")
        # markers (§5.1), skipping fenced code inside messages
        markers = []      # (content index, marker, rest)
        fence = None
        for k in range(1, len(content)):
            c = content[k]
            if fence:
                if re.match(r"^[ \t]*" + re.escape(fence[0]) + "{" + str(fence[1]) + r",}[ \t]*$", c):
                    fence = None
                continue
            fm = FENCE_RE.match(c)
            if fm and not (fm.group(1)[0] == "`" and "`" in c[fm.end():]):
                fence = (fm.group(1)[0], len(fm.group(1)), s + k)
                continue
            mm = MARKER_RE.match(c)
            if mm:
                after_blank = k == 1 or is_blank(content[k - 1])
                if mm.group(1) == "+++" and not after_blank:
                    self.diag("warning", "close-without-blank", s + k,
                              "`+++` after a non-blank line is message text; "
                              "add a blank `>` line before it to close")
                    continue
                if not after_blank:
                    self.diag("warning", "missing-blank-before-marker", s + k,
                              "renderers merge this marker into the previous paragraph")
                markers.append((k, mm.group(1), mm.group(2)))
                continue
            hm = LABEL_TOKEN_RE.match(c)
            if hm and label_key(hm.group(1)) and re.match(r"[ \t]|$", c[hm.end():]):
                self.diag("warning", "header-in-thread", s + k,
                          "a header inside a thread is message text; separate threads "
                          "with a blank line")
        if fence:
            self.diag("warning", "unclosed-fence", fence[2], "code fence in a thread is never closed")
        # opener (§5.4)
        first_marker = markers[0][0] if markers else len(content)
        opener = [first[tm.end():].strip()] + content[1:first_marker]
        opener = _trim_blank(opener)
        if opener:
            t.messages.append(Message("opener", s, body=opener))
        for idx, (k, marker, rest) in enumerate(markers):
            nxt = markers[idx + 1][0] if idx + 1 < len(markers) else len(content)
            body = content[k + 1:nxt]
            name, ts, reason, ignored, bad_ts = parse_fields(marker, rest)
            if ignored:
                self.diag("warning", "marker-ignored-text", s + k,
                          f"ignored after the timestamp: {ignored!r}")
            if bad_ts:
                self.diag("warning", "invalid-timestamp", s + k,
                          f"not a timestamp (YYYY-MM-DD[THH:MM[:SS][offset]]): {bad_ts!r}")
            if marker == "+++":
                t.messages.append(Message("close", s + k, name, ts, reason))
                stray = [b for b in body if not is_blank(b)]
                if stray:
                    self.diag("warning", "text-after-close", s + k + 1,
                              "lines after `+++` belong to no message")
                continue
            kind = "annotator" if marker == "-->" else "responder"
            body = _trim_blank(body)
            t.messages.append(Message(kind, s + k, name, ts, body=body))
            if not body:
                self.diag("warning", "empty-message", s + k, "message has no body")
            if kind == "responder" and (not name or not ts):
                self.diag("warning", "responder-marker-incomplete", s + k,
                          "`<--` should carry a responder name and a timestamp")
        if not t.messages:
            self.diag("warning", "empty-thread", s, "thread has no messages")
        # rendering hygiene
        if s > 0 and self.kind[s - 1] != "thread" and not is_blank(self.lines[s - 1]):
            self.diag("warning", "no-blank-before-thread", s,
                      "Pandoc merges a quote into the paragraph above; add a blank line")
        if e + 1 < self.n and not is_blank(self.lines[e + 1]):
            self.diag("warning", "lazy-continuation", e + 1,
                      "this line ends the thread; CommonMark renderers continue the quote")
        self.threads.append(t)

    def _duplicates(self):
        seen: dict[str, Thread] = {}
        for t in self.threads:
            if t.key in seen:
                seen[t.key].duplicate = True
                t.duplicate = True
                self.diag("error", "duplicate-label", t.start,
                          f"label {t.label!r} is already used by the thread at line "
                          f"{seen[t.key].start + 1}")
            else:
                seen[t.key] = t

    def _blocks(self):
        """§7.1: runs of non-blank body lines, split at block starts."""
        block = []
        for i in range(self.n):
            if self.kind[i] != "body" or i in self.quote_code or is_blank(self.lines[i]):
                if block:
                    yield block
                block = []
                continue
            if block and (BLOCK_START_RE.match(self.lines[i]) or HEADING_RE.match(self.lines[block[-1]])):
                yield block
                block = []
            block.append(i)
        if block:
            yield block

    def _anchors(self):
        by_key = {t.key: t for t in self.threads if not t.duplicate}
        dup_keys = {t.key for t in self.threads if t.duplicate}
        for block in self._blocks():
            base = self.offsets[block[0]]
            parts = []
            for i in block:
                m = self.masked[i]
                qp = QUOTE_PREFIX_RE.match(m)
                if qp:
                    m = " " * qp.end() + m[qp.end():]
                parts.append(m + self.raw[i][len(self.lines[i]):])   # keep CR width
            text = "\n".join(parts)
            highlights = [(h.start(), h.end(), " ".join(h.group(1).split()))
                          for h in HIGHLIGHT_RE.finditer(text)]
            for tok in LABEL_TOKEN_RE.finditer(text):
                key = label_key(tok.group(1))
                if not key:
                    continue
                st, en = tok.start(), tok.end()
                prev = text[st - 1] if st else ""
                nxt = text[en] if en < len(text) else ""
                line_start = text.rfind("\n", 0, st) + 1
                if is_blank(text[line_start:st]) and nxt == ":":
                    self.linkdef_keys.setdefault(key, self.pos(base + st)[0] - 1)
                    continue
                if prev in ("!", "\\", "]") or nxt in ("(", "["):
                    continue
                if key in dup_keys:
                    continue
                t = by_key.get(key)
                if t is None:
                    self.diag("warning", "orphan-anchor", self.pos(base + st)[0] - 1,
                              f"[?{tok.group(1)}] matches no thread; it is plain text")
                    continue
                anchor = Anchor("point", base + st, base + en, base + st)
                for hs, he, htext in highlights:
                    gap = text[he:st]
                    if he <= st and gap.strip() == "" and gap.count("\n") <= 1:
                        anchor = Anchor("range", base + st, base + en, base + st,
                                        htext, (base + hs, base + he))
                        break
                t.anchors.append(anchor)
        for key, line in self.linkdef_keys.items():
            if key in by_key or key in dup_keys:
                self.diag("warning", "label-is-link", line,
                          "a link definition uses this thread's label; renderers show "
                          "its anchors as links")

    # output --------------------------------------------------------------
    def to_json(self) -> dict:
        return {
            "spec": SPEC_VERSION,
            "front_matter": {"present": self.front_matter["present"],
                             "autoremove_closed": self.front_matter["autoremove_closed"]},
            "threads": [{
                "label": t.label,
                "key": t.key,
                "start_line": t.start + 1,
                "end_line": t.end + 1,
                "state": t.state,
                "duplicate": t.duplicate,
                "messages": [m.to_json() for m in t.messages],
                "anchors": [{
                    "kind": a.kind,
                    "start": self.pos(a.start),
                    "end": self.pos(a.end),
                    "highlight": a.highlight,
                } for a in t.anchors],
            } for t in self.threads],
            "errors": [{"code": d["code"], "line": d["line"]} for d in self.errors()],
        }

    def find(self, label: str) -> Thread:
        key = label_key(label)
        matches = [t for t in self.threads if t.key == key]
        if not matches:
            raise MdThreadError(f"no thread labelled {label!r}")
        if len(matches) > 1:
            raise MdThreadError(f"label {label!r} is duplicated; fix it before editing")
        return matches[0]


def _trim_blank(lines):
    a, b = 0, len(lines)
    while a < b and is_blank(lines[a]):
        a += 1
    while b > a and is_blank(lines[b - 1]):
        b -= 1
    return lines[a:b]


def parse_fields(marker: str, text: str):
    """§5.2. Returns (name, timestamp, reason, ignored_text, invalid_timestamp)."""
    reason = None
    if marker == "+++":
        rm = REASON_RE.search(text)
        if rm:
            reason = text[rm.end():].strip() or None
            text = text[:rm.start()]
    am = AT_RE.search(text)
    if not am:
        return (text.strip() or None), None, reason, None, None
    name = text[:am.start()].strip() or None
    rest = text[am.end():].lstrip()
    tm = TIMESTAMP_RE.match(rest)
    if not tm:
        return name, None, reason, None, (rest.strip() or None)
    ignored = rest[tm.end():].strip() or None
    return name, tm.group(0), reason, ignored, None


class MdThreadError(Exception):
    pass


# --- editing (SPEC §8) -------------------------------------------------------

def _append_lines(doc: Document, t: Thread, new: list[str]) -> str:
    """Insert content lines at the end of thread t, quoted like its header."""
    nl = "\r\n" if doc.raw[t.start].endswith("\r") else "\n"
    last = doc.lines[t.end]
    quoted = []
    if not is_blank(QUOTE_RE.sub("", last, count=1)):
        quoted.append(t.prefix)
    for c in new:
        quoted.append(t.prefix + (" " + c if c else ""))
    insert_at = doc.offsets[t.end] + len(doc.raw[t.end])
    return doc.text[:insert_at] + "".join(nl + q for q in quoted) + doc.text[insert_at:]


def reply(doc: Document, label: str, name: str, body: str, timestamp: str | None = None,
          force: bool = False) -> str:
    t = doc.find(label)
    if t.state != "open" and not force:
        raise MdThreadError(f"thread {t.label!r} is {t.state}, not open (use --force)")
    if not name or not name.strip():
        raise MdThreadError("a responder name is required")
    ts = timestamp or now_timestamp()
    if not FULL_TIMESTAMP_RE.match(ts):
        raise MdThreadError(f"timestamp {ts!r} is not the full form YYYY-MM-DDTHH:MM[:SS]±HH:MM")
    lines = body.rstrip("\n").split("\n")
    if not any(l.strip() for l in lines):
        raise MdThreadError("reply body is empty")
    return _append_lines(doc, t, [f"<-- {name.strip()} @ {ts}"] + [l.rstrip() for l in lines])


def close(doc: Document, label: str, name: str | None = None, timestamp: str | None = None,
          reason: str | None = None) -> str:
    t = doc.find(label)
    if t.state == "closed":
        raise MdThreadError(f"thread {t.label!r} is already closed")
    if timestamp and not TIMESTAMP_RE.fullmatch(timestamp):
        raise MdThreadError(f"timestamp {timestamp!r} is not YYYY-MM-DD[THH:MM[:SS][offset]]")
    if reason and "\n" in reason:
        raise MdThreadError("a close reason is one line")
    line = "+++"
    if name:
        line += " " + name.strip()
    if timestamp:
        line += " @ " + timestamp
    if reason:
        line += " ! " + reason.strip()
    return _append_lines(doc, t, [line])


def remove(doc: Document, threads: list[Thread]) -> str:
    """§8.3: delete threads, delete their anchors, unwrap range highlights, tidy.

    Anchor edits are character deletions (they may join two lines). Lines are
    tagged with sentinels before editing so the line pass afterwards knows which
    lines to drop (thread lines) and which to drop only if left blank (lines
    whose anchors were removed)."""
    text = doc.text
    deletions = []                  # (start, end) on doc.text
    tags = {}                       # offset -> sentinel
    for t in threads:
        for a in t.anchors:
            if a.kind == "range":
                hs, he = a.hl_span
                deletions.append((hs, hs + 2))
                deletions.append((he - 2, a.end))  # closing ==, gap, token
                tags[doc.offsets[doc.pos(hs)[0] - 1]] = TOUCHED
            else:
                s, e = a.start, a.end
                ls = text.rfind("\n", 0, s) + 1
                after = text[e:e + 1]
                if s > ls and text[s - 1] in " \t" and (after == "" or after in " \t\r\n.,;:!?)"):
                    while s > ls and text[s - 1] in " \t":
                        s -= 1
                elif is_blank(text[ls:s]):
                    while e < len(text) and text[e] in " \t":
                        e += 1
                deletions.append((s, e))
                tags[doc.offsets[doc.pos(a.start)[0] - 1]] = TOUCHED
        for i in range(t.start, t.end + 1):
            tags[doc.offsets[i]] = DROP
    edited = _apply(text, deletions, tags)
    final_nl = edited.endswith("\n")
    lines = (edited[:-1] if final_nl else edited).split("\n")
    out: list[str] = []
    k = 0
    while k < len(lines):
        line = lines[k]
        if not (line.startswith(DROP) or (line.startswith(TOUCHED) and is_blank(line[1:].replace(DROP, "").replace(TOUCHED, "")))):
            out.append(line.replace(TOUCHED, "").replace(DROP, ""))
            k += 1
            continue
        while k < len(lines) and (lines[k].startswith(DROP) or (
                lines[k].startswith(TOUCHED) and is_blank(lines[k][1:]))):
            k += 1                  # skip the dropped run
        nxt_blank = k < len(lines) and is_blank(lines[k])
        prev_blank = not out or is_blank(out[-1])
        if k >= len(lines):
            while out and is_blank(out[-1]):
                out.pop()           # region at the end: no trailing blank lines
        elif prev_blank and nxt_blank:
            k += 1                  # avoid a doubled blank line
    result = "\n".join(out)
    return result + "\n" if final_nl else result


TOUCHED = "\x00"
DROP = "\x01"


def _apply(text: str, deletions, tags) -> str:
    """Delete the union of `deletions`; insert tags[pos] before position pos
    (a tag inside a deleted range moves to the range start)."""
    merged = []
    for s, e in sorted(deletions):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    placed = {}
    for p, tag in tags.items():
        for s, e in merged:
            if s < p < e:
                p = s
                break
        placed[p] = placed.get(p, "") + tag
    out, cur = [], 0
    points = sorted(set([m[0] for m in merged] + list(placed)))
    di = 0
    for p in points:
        out.append(text[cur:p])
        cur = p
        out.append(placed.get(p, ""))
        while di < len(merged) and merged[di][0] == p:
            cur = max(cur, merged[di][1])
            di += 1
    out.append(text[cur:])
    return "".join(out)


# --- CLI ----------------------------------------------------------------------

def _read(path: str) -> Document:
    with open(path, encoding="utf-8", newline="") as f:
        return Document(f.read())


def _emit(path: str, old: str, new: str, write: bool):
    if old == new:
        print("no change")
        return
    if write:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new)
        print(f"wrote {path}")
        return
    sys.stdout.writelines(difflib.unified_diff(
        old.splitlines(True), new.splitlines(True), f"a/{path}", f"b/{path}"))
    print("(dry run; add --write to apply)")


def _row(doc: Document, t: Thread) -> str:
    last = t.messages[-1] if t.messages else None
    who = ""
    if last is not None:
        who = {"opener": "annotator", "annotator": "annotator",
               "responder": "responder", "close": "close"}[last.kind]
        if last.name:
            who += f" {last.name}"
    anchors = ", ".join(f"{doc.pos(a.start)[0]}" + ("r" if a.kind == "range" else "p")
                        for a in t.anchors) or "-"
    flag = " DUPLICATE" if t.duplicate else ""
    return (f"{t.start + 1}-{t.end + 1}\t{t.state}{flag}\t[?{t.label}]\t"
            f"messages={len(t.messages)}\tlast={who or '-'}\tanchors={anchors}")


def cmd_list(a) -> int:
    doc = _read(a.file)
    threads = [t for t in doc.threads if a.state == "all" or t.state == a.state]
    if a.json:
        data = doc.to_json()
        keep = {t.start + 1 for t in threads}
        data["threads"] = [t for t in data["threads"] if t["start_line"] in keep]
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    for t in threads:
        print(_row(doc, t))
    counts = {}
    for t in doc.threads:
        counts[t.state] = counts.get(t.state, 0) + 1
    summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items())) or "no threads"
    print(f"# {summary}; autoremove_closed={str(doc.front_matter['autoremove_closed']).lower()}")
    return 0


def cmd_check(a) -> int:
    doc = _read(a.file)
    for d in doc.diagnostics:
        print(f"{a.file}:{d['line']}: {d['severity']}: {d['code']}: {d['message']}")
    errs = len(doc.errors())
    print(f"# {len(doc.threads)} thread(s), {errs} error(s), "
          f"{len(doc.diagnostics) - errs} warning(s)")
    return 1 if errs else 0


def _body(a) -> str:
    if a.body is not None:
        return a.body
    if a.body_file == "-":
        return sys.stdin.read()
    with open(a.body_file, encoding="utf-8") as f:
        return f.read()


def cmd_reply(a) -> int:
    doc = _read(a.file)
    _emit(a.file, doc.text, reply(doc, a.label, a.name, _body(a), a.timestamp, a.force), a.write)
    return 0


def cmd_close(a) -> int:
    doc = _read(a.file)
    ts = now_timestamp() if a.now else a.timestamp
    _emit(a.file, doc.text, close(doc, a.label, a.name, ts, a.reason), a.write)
    return 0


def cmd_remove(a) -> int:
    doc = _read(a.file)
    if a.closed:
        threads = [t for t in doc.threads if t.state == "closed" and not t.duplicate]
    else:
        threads = [doc.find(l) for l in a.labels]
    if not threads:
        print("no matching threads")
        return 0
    for t in threads:
        print(f"remove [?{t.label}] (lines {t.start + 1}-{t.end + 1}, {len(t.anchors)} anchor(s))")
    _emit(a.file, doc.text, remove(doc, threads), a.write)
    return 0


def cmd_now(a) -> int:
    print(now_timestamp())
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mdthread", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list", help="list threads")
    s.add_argument("file")
    s.add_argument("--state", default="all", choices=["all", "open", "answered", "closed", "empty"])
    s.add_argument("--json", action="store_true", help="full parse result (fixture format)")
    s.set_defaults(fn=cmd_list)
    s = sub.add_parser("check", help="report errors and warnings; exit 1 on errors")
    s.add_argument("file")
    s.set_defaults(fn=cmd_check)
    s = sub.add_parser("reply", help="append a <-- message to an open thread")
    s.add_argument("file")
    s.add_argument("label")
    s.add_argument("--name", required=True, help="responder identifier, e.g. hermes/claude-opus-5-5")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--body")
    g.add_argument("--body-file", help="file with the body, or - for stdin")
    s.add_argument("--timestamp", help="default: now, local time with offset")
    s.add_argument("--force", action="store_true", help="reply even if the thread is not open")
    s.add_argument("--write", action="store_true")
    s.set_defaults(fn=cmd_reply)
    s = sub.add_parser("close", help="append a +++ line")
    s.add_argument("file")
    s.add_argument("label")
    s.add_argument("--name")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--timestamp")
    g.add_argument("--now", action="store_true")
    s.add_argument("--reason")
    s.add_argument("--write", action="store_true")
    s.set_defaults(fn=cmd_close)
    s = sub.add_parser("remove", help="remove threads with their anchors")
    s.add_argument("file")
    s.add_argument("labels", nargs="*")
    s.add_argument("--closed", action="store_true", help="remove every closed thread")
    s.add_argument("--write", action="store_true")
    s.set_defaults(fn=cmd_remove)
    s = sub.add_parser("now", help="print a timestamp for a <-- marker")
    s.set_defaults(fn=cmd_now)
    return p


def main(argv=None) -> int:
    p = build_parser()
    a = p.parse_args(argv)
    if a.cmd == "remove" and bool(a.labels) == bool(a.closed):
        p.error("give labels or --closed, not both")
    try:
        return a.fn(a)
    except MdThreadError as e:
        print(f"mdthread: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"mdthread: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
