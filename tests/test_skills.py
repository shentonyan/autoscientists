"""Mechanical checks on the Claude Code packaging: skills, agent, settings."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, f"{path}: no frontmatter"
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields, text[m.end():]


def cli_commands():
    import subprocess
    import sys
    out = subprocess.run([sys.executable, "-m", "autosci", "--help"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    m = re.search(r"\{([a-z,-]+)\}", out)
    assert m, "could not read subcommands from --help"
    return set(m.group(1).split(","))


class SkillTests(unittest.TestCase):
    def skill_files(self):
        files = sorted(SKILLS.glob("*/SKILL.md"))
        self.assertGreaterEqual(len(files), 3)
        return files

    def test_frontmatter_and_names(self):
        for f in self.skill_files():
            fm, body = frontmatter(f)
            self.assertEqual(fm.get("name"), f.parent.name, f)
            self.assertTrue(re.fullmatch(r"[a-z0-9-]{1,64}", fm["name"]))
            desc = fm.get("description", "")
            self.assertGreater(len(desc), 80, f"{f}: description too thin to trigger")
            self.assertLessEqual(len(desc) + len(fm.get("when_to_use", "")), 1536, f)
            self.assertLess(len(body.splitlines()), 500, f)
            self.assertNotIn("<", desc)

    def test_commands_exist(self):
        known = cli_commands()
        for f in self.skill_files():
            for cmd in re.findall(r"python -m autosci (?:--root \S+ )?([a-z][a-z-]*)", f.read_text()):
                self.assertIn(cmd, known, f"{f}: unknown command {cmd}")

    def test_referenced_paths_exist(self):
        files = list(self.skill_files()) + [ROOT / "AGENTS.md", ROOT / "loop" / "AGENT.md"]
        for f in files:
            for p in re.findall(r"`((?:\.\./|[\w.-]+/)+[\w.-]+\.(?:md|json|py|jsonl))`", f.read_text()):
                if any(c in p for c in "<*"):
                    continue
                ok = (ROOT / p).exists() or (f.parent / p).exists()
                self.assertTrue(ok, f"{f.name}: missing referenced path {p}")
            for p in re.findall(r"`([\w-]+\.md)` next to this file", f.read_text()):
                self.assertTrue((f.parent / p).exists(), p)

    def test_disclosure_line_everywhere_it_matters(self):
        line = "Disclosure: produced by the AutoScientists research loop; this PR was prepared with an AI assistant and is reviewed by the maintainer."
        for p in [SKILLS / "autoscientists" / "SKILL.md", ROOT / "loop" / "AGENT.md",
                  ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"]:
            self.assertIn(line, p.read_text(), p)

    def test_reviewer_is_read_only(self):
        fm, _ = frontmatter(ROOT / ".claude" / "agents" / "autosci-reviewer.md")
        tools = {t.strip() for t in fm["tools"].split(",")}
        self.assertTrue(tools <= {"Read", "Grep", "Glob"}, tools)

    def test_settings_protect_core(self):
        s = json.loads((ROOT / ".claude" / "settings.json").read_text())
        deny = set(s["permissions"]["deny"])
        for need in ["Edit(autosci/**)", "Edit(.claude/settings.json)", "Edit(state/governor.json)"]:
            self.assertIn(need, deny)
        for rule in s["permissions"]["allow"]:
            self.assertNotIn("git push", rule)

    def test_claude_md_imports_agents_md(self):
        self.assertEqual((ROOT / "CLAUDE.md").read_text().strip(), "@AGENTS.md")


if __name__ == "__main__":
    unittest.main()
