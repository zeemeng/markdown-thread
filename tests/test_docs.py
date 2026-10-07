"""Every Markdown example in the docs is marked and parses as declared.

Mark an example with `<!-- mdthread: example -->` on the line before the
fence; add `warnings=code,code` to declare expected warnings."""
import re
import unittest

from helpers import ROOT, mdthread, read

DOCS = ["README.md", "SPEC.md", "GUIDE.md", "agents/AGENTS-snippet.md",
        "skill/markdown-thread/SKILL.md"]
BLOCK_RE = re.compile(r"(?:<!-- mdthread: example(?: warnings=([\w,-]+))? -->\n)?"
                      r"```markdown\n(.*?)```", re.S)


class DocExamples(unittest.TestCase):
    def test_examples(self):
        total = 0
        for name in DOCS:
            text = read(ROOT / name)
            for m in BLOCK_RE.finditer(text):
                total += 1
                line = text[:m.start()].count("\n") + 1
                with self.subTest(f"{name}:{line}"):
                    self.assertTrue(m.group(0).startswith("<!--"),
                                    "unmarked ```markdown example")
                    doc = mdthread.Document(m.group(2))
                    self.assertTrue(doc.threads, "example has no thread")
                    self.assertEqual(doc.errors(), [])
                    warnings = sorted(d["code"] for d in doc.diagnostics)
                    declared = sorted(filter(None, (m.group(1) or "").split(",")))
                    self.assertEqual(warnings, declared)
        self.assertGreaterEqual(total, 9)

    def test_spec_example_is_the_basic_fixture(self):
        spec = read(ROOT / "SPEC.md")
        example = BLOCK_RE.search(spec).group(2)
        self.assertEqual(example, read(ROOT / "fixtures" / "parse" / "basic.md"))


    def test_skill_spec_copy_is_current(self):
        self.assertEqual(read(ROOT / "skill/markdown-thread/references/protocol.md"),
                         read(ROOT / "SPEC.md"), "run `make sync-spec`")


if __name__ == "__main__":
    unittest.main()
