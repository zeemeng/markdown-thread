"""Conformance: every fixture reproduces exactly."""
import json
import unittest

from helpers import FIXTURES, mdthread, read, run_op

# Implementation warnings expected per parse fixture (not part of the spec).
WARNINGS = {
    "basic": [],
    "opener-forms": [],
    "states": ["empty-thread"],
    "labels": [],
    "ordinary-quotes": ["nested-thread", "orphan-anchor", "orphan-anchor"],
    "marker-fields": ["invalid-timestamp", "marker-ignored-text", "marker-ignored-text",
                      "responder-marker-incomplete"],
    "close-rule": ["close-without-blank"],
    "code": [],
    "anchors": ["orphan-anchor"],
    "duplicates": [],
    "lists": ["inconsistent-indent", "inconsistent-indent"],
    "front-matter-yaml": [],
    "front-matter-flow": [],
    "front-matter-toml": [],
    "link-definition": ["label-is-link"],
    "boundaries": ["no-blank-before-thread", "lazy-continuation", "header-in-thread",
                   "text-after-close"],
    "crlf": [],
}


class ParseFixtures(unittest.TestCase):
    def test_every_fixture_has_expectations(self):
        names = sorted(p.stem for p in (FIXTURES / "parse").glob("*.md"))
        self.assertEqual(names, sorted(WARNINGS))
        for name in names:
            self.assertTrue((FIXTURES / "parse" / f"{name}.json").exists(), name)

    def test_parse(self):
        for md in sorted((FIXTURES / "parse").glob("*.md")):
            with self.subTest(md.stem):
                doc = mdthread.Document(read(md))
                expected = json.loads(read(md.with_suffix(".json")))
                self.assertEqual(doc.to_json(), expected)

    def test_warnings(self):
        for name, codes in WARNINGS.items():
            with self.subTest(name):
                doc = mdthread.Document(read(FIXTURES / "parse" / f"{name}.md"))
                got = sorted(d["code"] for d in doc.diagnostics if d["severity"] == "warning")
                self.assertEqual(got, sorted(codes))


class OpFixtures(unittest.TestCase):
    def test_ops(self):
        cases = sorted((FIXTURES / "ops").glob("*.op.json"))
        self.assertGreater(len(cases), 0)
        for op_file in cases:
            name = op_file.name[:-len(".op.json")]
            with self.subTest(name):
                src = read(FIXTURES / "ops" / f"{name}.md")
                out = run_op(src, json.loads(read(op_file)))
                self.assertEqual(out, read(FIXTURES / "ops" / f"{name}.out.md"))

    def test_ops_output_parses_cleanly(self):
        """Edits never introduce errors or new warnings."""
        for op_file in sorted((FIXTURES / "ops").glob("*.op.json")):
            name = op_file.name[:-len(".op.json")]
            with self.subTest(name):
                before = mdthread.Document(read(FIXTURES / "ops" / f"{name}.md"))
                after = mdthread.Document(read(FIXTURES / "ops" / f"{name}.out.md"))
                self.assertEqual(after.errors(), [])
                self.assertLessEqual({d["code"] for d in after.diagnostics},
                                     {d["code"] for d in before.diagnostics})


if __name__ == "__main__":
    unittest.main()
