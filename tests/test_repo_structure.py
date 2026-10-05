"""Repository hygiene: links, figures, workflow commands, example, personal-info scan."""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".md", ".py", ".json", ".jsonl", ".yml", ".yaml", ".toml", ".svg", ".txt", ".cfg", ""}


def tracked_text_files():
    out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                         cwd=ROOT, capture_output=True, text=True)
    names = [n for n in out.stdout.split("\0") if n] if out.returncode == 0 else []
    if not names:
        names = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]
    return [ROOT / n for n in names if (ROOT / n).suffix in TEXT_SUFFIXES and (ROOT / n).is_file()]


class RepoTests(unittest.TestCase):
    def test_markdown_relative_links_resolve(self):
        pat = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")
        for f in ROOT.rglob("*.md"):
            if ".git" in f.parts or "examples" in f.parts:
                continue
            for target in pat.findall(f.read_text(encoding="utf-8")):
                if re.match(r"[a-z]+:", target) or target.startswith("#"):
                    continue
                path = target.split("#")[0]
                self.assertTrue((f.parent / path).exists(), f"{f.relative_to(ROOT)}: broken link {target}")

    def test_svgs_parse_and_have_titles(self):
        svgs = sorted((ROOT / "docs" / "img").glob("*.svg"))
        self.assertGreaterEqual(len(svgs), 6)
        for f in svgs:
            root = ET.fromstring(f.read_text(encoding="utf-8"))
            self.assertTrue(root.tag.endswith("svg"))
            self.assertTrue(any(c.tag.endswith("title") for c in root), f"{f.name}: no <title>")

    def test_readme_mentions_every_figure(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for f in (ROOT / "docs" / "img").glob("*.svg"):
            self.assertIn(f"docs/img/{f.name}", readme)

    def test_workflow_commands_exist(self):
        wf = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        out = subprocess.run([sys.executable, "-m", "autosci", "--help"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        known = set(re.search(r"\{([a-z,-]+)\}", out).group(1).split(","))
        for cmd in re.findall(r"python -m autosci (?:--root \S+ )?([a-z][a-z-]*)", wf):
            self.assertIn(cmd, known)
        for script in re.findall(r"python (scripts/\S+\.py)", wf):
            self.assertTrue((ROOT / script).exists())

    def test_quickstart_verifies_in_a_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "qs"
            shutil.copytree(ROOT / "examples" / "quickstart", dst, ignore=shutil.ignore_patterns("__pycache__"))
            for cmd in (["verify", "dice-sum"], ["lint", "dice-sum", "--strict"]):
                r = subprocess.run([sys.executable, "-m", "autosci", "--root", str(dst), *cmd],
                                   cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_no_personal_information(self):
        email = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
        allowed = ("users.noreply.github.com", "example.invalid", "example.com")
        bad_path = re.compile(r"/(?:home|root|Users)/[\w.-]+|/tmp/claude|C:\\\\Users")
        for f in tracked_text_files():
            if f.name.endswith(".jsonl") and "ledger" in f.name:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            for m in email.findall(text):
                self.assertTrue(any(a in m for a in allowed), f"{f.relative_to(ROOT)}: email-like string {m}")
            if f.name != "test_repo_structure.py":
                self.assertIsNone(bad_path.search(text), f"{f.relative_to(ROOT)}: local path")
            self.assertNotIn("claude.ai/code/" + "session", text, f.name)


if __name__ == "__main__":
    unittest.main()
