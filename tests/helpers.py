import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"
SCRIPT = ROOT / "skill" / "markdown-thread" / "scripts" / "mdthread.py"

_spec = importlib.util.spec_from_file_location("mdthread", SCRIPT)
mdthread = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mdthread)


def read(path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def run_op(text: str, op: dict) -> str:
    doc = mdthread.Document(text)
    if op["op"] == "reply":
        return mdthread.reply(doc, op["label"], op["name"], op["body"], op["timestamp"])
    if op["op"] == "ask":
        return mdthread.ask(doc, op["label"], op["name"], op["body"], op["timestamp"],
                            op.get("line"), op.get("text"))
    if op["op"] == "close":
        return mdthread.close(doc, op["label"], op.get("name"), op.get("timestamp"),
                              op.get("reason"))
    if op["op"] == "remove":
        if op.get("closed"):
            threads = [t for t in doc.threads if t.state == "closed" and not t.duplicate]
        else:
            threads = [doc.find(label) for label in op["labels"]]
        return mdthread.remove(doc, threads)
    raise ValueError(op["op"])
