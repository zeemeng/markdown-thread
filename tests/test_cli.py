"""Reference implementation: helpers and command-line behaviour."""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import FIXTURES, SCRIPT, mdthread, read


def cli(*args, stdin=None):
    p = subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin,
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


class LabelKey(unittest.TestCase):
    def test_normalisation(self):
        k = mdthread.label_key
        self.assertEqual(k("Why  Ticks"), "why ticks")
        self.assertEqual(k("  why\n ticks "), "why ticks")
        self.assertEqual(k("Straße"), k("STRASSE"))      # full case folding
        self.assertEqual(k("   "), "")


class Fields(unittest.TestCase):
    def test_table(self):
        f = mdthread.parse_fields
        cases = [
            ("-->", "", (None, None, None, None, None)),
            ("-->", " Max Meng", ("Max Meng", None, None, None, None)),
            ("-->", " Max @ 2026-10-06", ("Max", "2026-10-06", None, None, None)),
            ("-->", " @ 2026-10-06T10:00Z", (None, "2026-10-06T10:00Z", None, None, None)),
            ("-->", " @max:example.org", ("@max:example.org", None, None, None, None)),
            ("-->", " max@example.org", ("max@example.org", None, None, None, None)),
            ("-->", " Max @2026-10-06", ("Max", "2026-10-06", None, None, None)),
            ("-->", " Max @ soon", ("Max", None, None, None, "soon")),
            ("-->", " Max @ 2026-10-06 x", ("Max", "2026-10-06", None, "x", None)),
            ("-->", " Max ! not a reason", ("Max ! not a reason", None, None, None, None)),
            ("+++", " ! wontfix", (None, None, "wontfix", None, None)),
            ("+++", " Max @ 2026-10-06 ! a @ b", ("Max", "2026-10-06", "a @ b", None, None)),
            ("+++", " Max! now", ("Max! now", None, None, None, None)),
            ("+++", " !", (None, None, None, None, None)),
        ]
        for marker, text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(f(marker, text), expected)


class Cli(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)

    def doc(self, text, name="doc.md"):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return path

    def test_list_and_filter(self):
        path = str(FIXTURES / "parse" / "states.md")
        code, out, _ = cli("list", path)
        self.assertEqual(code, 0)
        self.assertIn("1-1\tempty\t[?empty]", out)
        self.assertTrue(out.rstrip().endswith(
            "# 1 answered, 1 closed, 1 empty, 2 open; autoremove_closed=false"))
        code, out, _ = cli("list", path, "--state", "open")
        rows = [l for l in out.splitlines() if not l.startswith("#")]
        self.assertEqual([r.split("\t")[2] for r in rows], ["[?open]", "[?reopened]"])

    def test_list_json_is_fixture_format(self):
        path = FIXTURES / "parse" / "basic.md"
        code, out, _ = cli("list", "--json", str(path))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), json.loads(read(path.with_suffix(".json"))))

    def test_check_exit_codes(self):
        code, out, _ = cli("check", str(FIXTURES / "parse" / "states.md"))
        self.assertEqual(code, 0)
        self.assertIn("warning: empty-thread", out)
        code, out, _ = cli("check", str(FIXTURES / "parse" / "duplicates.md"))
        self.assertEqual(code, 1)
        self.assertIn(":5: error: duplicate-label", out)

    def test_reply_dry_run_then_write(self):
        path = self.doc("> [?q] Why?\n")
        code, out, _ = cli("reply", path, "q", "--name", "bot", "--body", "Because.",
                           "--timestamp", "2026-10-06T21:00-04:00")
        self.assertEqual(code, 0)
        self.assertIn("+> <-- bot @ 2026-10-06T21:00-04:00", out)
        self.assertIn("dry run", out)
        self.assertEqual(read(path), "> [?q] Why?\n")
        code, out, _ = cli("reply", path, "q", "--name", "bot", "--body-file", "-",
                           "--timestamp", "2026-10-06T21:00-04:00", "--write",
                           stdin="Because.\n")
        self.assertEqual(code, 0)
        self.assertEqual(read(path), "> [?q] Why?\n>\n> <-- bot @ 2026-10-06T21:00-04:00\n"
                                     "> Because.\n")
        self.assertEqual(mdthread.Document(read(path)).threads[0].state, "answered")

    def test_reply_default_timestamp_is_full_form(self):
        path = self.doc("> [?q] Why?\n")
        cli("reply", path, "q", "--name", "bot", "--body", "x", "--write")
        ts = mdthread.Document(read(path)).threads[0].messages[-1].timestamp
        self.assertRegex(ts, mdthread.FULL_TIMESTAMP_RE)

    def test_reply_refusals(self):
        closed = self.doc("> [?q] Why?\n>\n> +++\n", "closed.md")
        code, _, err = cli("reply", closed, "q", "--name", "bot", "--body", "x")
        self.assertEqual(code, 1)
        self.assertIn("is closed, not open", err)
        code, out, _ = cli("reply", closed, "q", "--name", "bot", "--body", "x", "--force",
                           "--timestamp", "2026-10-06T21:00-04:00", "--write")
        self.assertEqual(code, 0)
        # now answered: --force does not reach answered (or empty) threads (SPEC §9 rule 2)
        for path in (closed, self.doc("> [?e]\n", "empty.md")):
            code, _, err = cli("reply", path, "q" if path == closed else "e", "--name", "bot",
                               "--body", "x", "--force", "--write")
            self.assertEqual(code, 1)
            self.assertIn("--force works only on closed threads", err)
        dup = str(FIXTURES / "parse" / "duplicates.md")
        code, _, err = cli("reply", dup, "dup", "--name", "bot", "--body", "x")
        self.assertEqual((code, "duplicated" in err), (1, True))
        code, _, err = cli("reply", closed, "nope", "--name", "bot", "--body", "x")
        self.assertEqual((code, "no thread" in err), (1, True))
        opened = self.doc("> [?q] Why?\n", "open.md")
        code, _, err = cli("reply", opened, "q", "--name", "bot", "--body", "x",
                           "--timestamp", "2026-10-06")
        self.assertEqual((code, "full form" in err), (1, True))
        code, _, err = cli("reply", opened, "q", "--name", "bot", "--body", "  \n")
        self.assertEqual((code, "empty" in err), (1, True))

    def test_close_and_reopen(self):
        path = self.doc("> [?q] Why?\n")
        code, _, _ = cli("close", path, "q", "--name", "Max", "--now", "--reason", "ok",
                         "--write")
        self.assertEqual(code, 0)
        doc = mdthread.Document(read(path))
        last = doc.threads[0].messages[-1]
        self.assertEqual((doc.threads[0].state, last.name, last.reason), ("closed", "Max", "ok"))
        self.assertRegex(last.timestamp, mdthread.FULL_TIMESTAMP_RE)
        code, _, err = cli("close", path, "q")
        self.assertEqual((code, "already closed" in err), (1, True))
        with open(path, "a", encoding="utf-8") as f:
            f.write(">\n> --> Max\n> One more thing.\n")
        self.assertEqual(mdthread.Document(read(path)).threads[0].state, "open")

    def test_remove_arguments(self):
        path = self.doc("> [?q] Why?\n")
        code, _, err = cli("remove", path)
        self.assertEqual(code, 2)
        code, _, _ = cli("remove", path, "q", "--closed")
        self.assertEqual(code, 2)
        code, out, _ = cli("remove", path, "--closed")
        self.assertEqual((code, out.strip()), (0, "no matching threads"))

    def test_remove_write(self):
        src = FIXTURES / "ops" / "remove-closed.md"
        path = self.doc(read(src))
        code, out, _ = cli("remove", path, "--closed", "--write")
        self.assertEqual(code, 0)
        self.assertEqual(read(path), read(FIXTURES / "ops" / "remove-closed.out.md"))
        self.assertEqual(len(re.findall(r"^remove ", out, re.M)), 3)

    def test_ask_write_makes_an_answered_thread(self):
        path = self.doc("Intro.\n\nThe cap is three.\n")
        code, out, _ = cli("ask", path, "cap", "--name", "agent/x", "--line", "3",
                           "--text", "three", "--body", "Why three?", "--write")
        self.assertEqual((code, out.strip()), (0, f"wrote {path}"))
        doc = mdthread.Document(read(path))
        t = doc.find("cap")
        self.assertEqual((t.state, len(t.anchors), t.anchors[0].kind), ("answered", 1, "range"))
        self.assertRegex(t.messages[0].timestamp, mdthread.FULL_TIMESTAMP_RE)
        # the user's follow-up reopens it for the next pass
        with open(path, "a", encoding="utf-8") as f:
            f.write(">\n> --> Max\n> Load tests chose it.\n")
        self.assertEqual(mdthread.Document(read(path)).find("cap").state, "open")

    def test_ask_thread_order_follows_anchors(self):
        """Threads after a paragraph come out in anchor order, whatever order
        the questions are asked in (bottom-up keeps line numbers valid)."""
        orders = [["c", "b", "a"], ["a", "b", "c"], ["b", "a", "c"]]
        words = {"a": (1, "One"), "b": (1, "two"), "c": (2, "three")}
        for order in orders:
            with self.subTest(order=order):
                path = self.doc("One two\nthree.\n\nNext.\n")
                for label in order:
                    line, text = words[label]
                    code, _, err = cli("ask", path, label, "--name", "a/x", "--line", str(line),
                                       "--text", text, "--body", "Q?", "--write")
                    self.assertEqual(code, 0, err)
                doc = mdthread.Document(read(path))
                self.assertEqual([t.label for t in doc.threads], ["a", "b", "c"])
                self.assertTrue(read(path).endswith("> Q?\n\nNext.\n"))
        # a thread without anchors that already follows the paragraph stays first
        path = self.doc("One two.\n\n> [?first] x\n")
        cli("ask", path, "z", "--name", "a/x", "--line", "1", "--text", "One", "--body", "Q?", "--write")
        self.assertEqual([t.label for t in mdthread.Document(read(path)).threads], ["first", "z"])

    def test_ask_crlf(self):
        path = self.doc("One.\r\nTwo.\r\n")
        code, _, err = cli("ask", path, "q", "--name", "a/x", "--line", "1", "--body", "Hm?",
                           "--timestamp", "2026-10-08T15:00-04:00", "--write")
        self.assertEqual(code, 0, err)
        self.assertEqual(read(path), "One. [?q]\r\nTwo.\r\n\r\n> [?q]\r\n"
                                     "> <-- a/x @ 2026-10-08T15:00-04:00\r\n> Hm?\r\n")

    def test_ask_refusals(self):
        text = ("Body [?stray] text `code`.\n\n> [?q] Why?\n\n```\nfenced\n```\n\n"
                "[?linked]: https://example.org\n")
        path = self.doc(text)
        cases = [
            (["q", "--line", "1"], "already used by the thread at line 3"),
            (["Q  ", "--line", "1"], "already used"),
            (["a]b"], "without [ or ]"),
            (["new", "--line", "3"], "not body text"),
            (["new", "--line", "6"], "not body text"),
            (["new", "--line", "2"], "not body text"),
            (["new", "--line", "99"], "not body text"),
            (["new", "--line", "1", "--text", "code"], "does not occur"),
            (["new", "--line", "1", "--text", " text"], "surrounding spaces"),
            (["new", "--text", "Body"], "--text needs --line"),
            (["stray", "--line", "1"], "would not make a clean new thread"),
            (["linked"], "errors or warnings"),
        ]
        for args, msg in cases:
            with self.subTest(args=args):
                code, _, err = cli("ask", path, *args, "--name", "a/x", "--body", "Hm?", "--write")
                self.assertEqual(code, 1)
                self.assertIn(msg, err)
        self.assertEqual(read(path), text)
        code, _, err = cli("ask", path, "new", "--name", " ", "--body", "Hm?")
        self.assertIn("responder name is required", err)
        code, _, err = cli("ask", path, "new", "--name", "a/x", "--body", "\n")
        self.assertIn("body is empty", err)

    def test_write_refuses_a_file_changed_since_reading(self):
        path = self.doc("> [?q] Why?\n")
        doc = mdthread.Document(read(path))
        new = mdthread.reply(doc, "q", "a/x", "Because.", "2026-10-08T15:00-04:00")
        with open(path, "a", encoding="utf-8") as f:
            f.write("\nEdited meanwhile.\n")
        with self.assertRaises(mdthread.MdThreadError):
            mdthread._emit(path, doc.text, new, True)
        self.assertEqual(read(path), "> [?q] Why?\n\nEdited meanwhile.\n")
        with contextlib.redirect_stdout(io.StringIO()):
            mdthread._emit(path, read(path), "x\n", True)
        self.assertEqual(read(path), "x\n")

    def test_now(self):
        code, out, _ = cli("now")
        self.assertEqual(code, 0)
        self.assertRegex(out.strip(), mdthread.FULL_TIMESTAMP_RE)

    def test_missing_file(self):
        code, _, err = cli("list", os.path.join(self.dir, "missing.md"))
        self.assertEqual(code, 1)
        self.assertIn("No such file", err)


if __name__ == "__main__":
    unittest.main()
