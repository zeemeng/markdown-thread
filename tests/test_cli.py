"""Reference implementation: helpers and command-line behaviour."""
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
                           "--timestamp", "2026-10-06T21:00-04:00")
        self.assertEqual(code, 0)
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
