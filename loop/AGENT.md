# Loop procedure

The canonical procedure is the `autoscientists` skill:
`.claude/skills/autoscientists/SKILL.md`, with `autosci-card-design` and
`autosci-sources` beside it and the read-only reviewer in
`.claude/agents/autosci-reviewer.md`. Agents without skill support should read those
files directly. `PROTOCOL.md` explains why each step exists.

Short form of the limits, kept here because the rest of the repository points to them:

- One card per wake-up. Run `python -m autosci govern` first; STOP means journal and stop.
- Stop at the first failed `verify`. Never push to `main`. Never merge.
- Never edit the frozen core listed in `state/protected.json`; propose in the journal.
- Only tier 1 files (this file, the skills, new experiments, docs) may change, as a
  variant: `python -m autosci evolve propose --component <file> --parent <id> --note "<what it should improve>" --base origin/main`.

## Commits and pull requests

- Every commit message and every pull request body contains this line as its own final paragraph (a `Co-Authored-By:` trailer may follow it in commits):

  `Disclosure: produced by the AutoScientists research loop; this PR was prepared with an AI assistant and is reviewed by the maintainer.`

  It is true only once the maintainer has reviewed the pull request, so pull
  requests stay in draft until then.
- Keep the repository free of personal information: no email addresses, machine
  details, local paths, or references to private projects. Commit under the
  maintainer's GitHub noreply identity.
- Do not put links to tooling sessions in commit messages or pull request text.
