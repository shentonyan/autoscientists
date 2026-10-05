# Survey of related projects

Surveyed on 2026-10-05. Source ids in brackets refer to `state/sources.jsonl`; the
evidence for each is `state/evidence/<id>.txt`.

## How far to trust this

- Each evidence file holds a **summary** produced by a fetch tool (a small model's
  summary of the page) and written down by a delegate. It is not the project's own
  text, and it can omit or distort. Every source is recorded with evidence kind
  `tool-summary` for that reason.
- "Not described in the summary" is the strongest negative statement made here. It
  does not show that a project lacks the feature; the project may have it.
- Star counts, benchmark figures and dates shown on the pages are not repeated.
  None was verified.
- Sections A and B report what the summaries said. Sections C to E are decisions and
  judgments of this project, not findings.

## A. What the summaries say

### Loop-style systems

| project | what the summary says it does | mechanisms of interest | limits it states or implies |
|---|---|---|---|
| karpathy/autoresearch [karpathy-autoresearch] | An agent edits one training file, runs a fixed-length training job and keeps or discards the change on a validation metric. Every run, failures included, is logged. | A fixed compute budget makes runs comparable; evaluation code is declared off-limits. | The off-limits rule is an instruction; no check that the evaluator was left untouched was described. |
| WillStephenn/research-loop [research-loop] | Shell scripts and markdown skills around a graph of hypotheses with dependencies, woken on a schedule. | A conjecture cannot be registered without a falsifier and is capped at three attempts; a falsified hypothesis is final; there is deliberately no "predicted impact" field; the target can only be raised, and only after two consecutive evaluations met the current bar; the journal is append-only; metrics and categories come from a closed list; the goal file is human-owned. | Names confirmation bias at scale as the core problem. Tamper evidence for the journal was not described. |
| Orchestra-Research autoresearch skill [orchestra-autoresearch] | An inner loop (hypothesis, experiment, measure, record) and an outer loop (synthesise, then deepen, broaden, pivot or conclude). | The protocol is committed before execution; results are labelled confirmatory or exploratory; metrics are sanity-checked first; fabricated references are prohibited. | Enforced by instruction; nothing was described that checks the protocol commit precedes the results. |
| ARIS [aris] | A large set of markdown skills; one model family executes and a different one reviews, with no communication during review. | A citation-check script that looks papers up in three services and tags unmatched ones as unverified instead of deleting them; a claim audit that maps each claim to evidence in files; an experiment audit for after-the-fact threshold tuning; a writer that inserts placeholders rather than invent data; findings that close only with hashed evidence or a recorded human waiver; stall detection. | The summary is the project describing itself; maturity is unverified. Prompts and scripts were not read. Whether "hashed evidence" means a chain or per-item hashes is unclear. |
| raiyanyahya/loop [loop-runner] | A runner that loops a coding agent until executable checks pass. | The harness runs the checks itself; files matching protected globs are restored and the iteration rejected; an independent critic can veto completion; failed iterations are reverted; limits on iterations, time, cost and stalls. | States that the defenses raise the cost of cheating without guaranteeing anything, and recommends hold-out checks the agent cannot see. Its figure on how much more lenient self-grading is came from the page and was not verified. |

### End-to-end research systems

| project | what the summary says it does | mechanisms of interest | limits it states or implies |
|---|---|---|---|
| SakanaAI AI-Scientist-v2 and v1 [sakana-v2, sakana-v1] | Idea, tree search over experiments, write-up, review. v1 is template based. | The write-up is given only summaries of the experiment logs and told not to report anything absent from them; citations come only from search-service hits; unused or invalid figure references are audited. | Mostly prompt-level rather than hard verification. Executes model-written code, so a sandbox with restricted network is advised. v1 reviews showed positivity bias with some models. |
| HKUDS/AI-Researcher [hkuds-airesearcher] | Staged pipeline from literature to a written paper, with a validation and refinement phase. | A benchmark anchored to expert papers across several domains. | No guard against invented citations or reward hacking appeared in the summary. Docker is required. |
| SamuelSchmidgall/AgentLaboratory [agent-laboratory] | Human-assisted workflow of literature review, experiments and report. | Checkpoint and resume; a co-pilot mode in which a human gates steps. | No verification or safety discussion appeared in the summary. |
| renee-jia/scholar-loop [scholar-loop] | A multi-agent loop that screens many ideas cheaply and spends full compute on survivors. | A frozen metric the code under test cannot see or alter; an allowlist of editable files; a registry that requires reported numbers to trace to measurements; a governor that stops on cost, rounds or lack of progress; predictions by agents scored against the frozen metric; a bundled "cheater" that shows reward hacking being detected; deterministic tests with a mock model. | States that residual boundaries need container sandboxing and that it is a research preview. Whether its ledgers are hash-chained was not shown. |
| ResearAI/DeepScientist [deepscientist] | Local-first research studio; each quest is its own git repository. | Git history as provenance; failed paths are kept; a human can pause, edit and resume. | Lists hallucination in autonomous proposals as a risk and advises an isolated environment. |
| WecoAI/aideml [aideml] | Each ML script is a node in a tree; model patches make children; metric feedback steers the search. | Tree search with the metric as the selection signal. | No leakage protection was described in the summary. |

### Self-modifying and evolutionary systems

| project | what the summary says | what may change itself, and what judges it | safety statements |
|---|---|---|---|
| jennyzzt/dgm [dgm] | The agent edits its own code and validates each change on coding benchmarks. | Its own implementation; benchmark scores accept or reject. No evaluator protection described. | Docker required; warns that untrusted generated code may behave destructively. No oversight discussion in the summary. |
| MaximeRobeyns/self_improving_coding_agent [sica] | Benchmark, archive, the agent works on its own codebase, benchmark again. | Its own codebase; benchmark suites decide. | Container advised. An asynchronous overseer appears in a visualization; whether it can halt a run was not confirmed. |
| codelion/openevolve [openevolve] | Evolves a user's program against a user-supplied evaluator, with a grid-and-islands population. | The user's program, not the tool itself; constraints on what not to change are given as prompt text. | No sandboxing or evaluator protection described. |
| SakanaAI/ShinkaEvolve [shinkaevolve] | Mutates marked blocks of a program with an ensemble of models; islands, archive, novelty rejection by embedding similarity. | Marked blocks only; an evaluate script scores. | Evaluator protection not described. |
| BarishNamazov/interpretable-autoresearch [interpretable-autoresearch] | Agents follow a versioned human-readable program file. | Declared edit targets only; improvements inside the noise floor are reverted; an append-only event log with causal links; predictions recorded before each run and compared after; edits outside scope appear as diffs with no matching event. | States that the log catches behavioral divergence but does not stop prompt injection, deception or sandbagging, and claims no sandboxing. |
| armgabrielyan/autoloop [autoloop] | A CLI for bounded optimisation loops: one change per iteration, keep or discard on a metric and guardrail commands. | The repository under optimisation; no protection against the agent editing evaluation commands was described. | Human review comes after the run, as review branches. |
| Godel_Agent and microsoft/stop [godel-agent, stop] | A self-referential agent that rewrites its own behavior; an improver program applied to itself. | Their own behavior; evaluator protection not described in either summary. | STOP's summary mentions that sandbox bypass was examined; details were not obtained. |
| yibie/awesome-autoresearch [awesome-autoresearch] | An index of autoresearch-style projects. | n/a | n/a |

## B. Observations across the summaries

These hold for the summaries read, not for the projects.

1. Protection of the evaluator is mostly by instruction (karpathy/autoresearch,
   openevolve). Mechanical protection was described for loop-runner (restore and
   reject), scholar-loop (frozen metric, allowlist) and interpretable-autoresearch
   (declared targets, diffs checked against the event log).
2. No summary described a hash-chained journal. Pre-registration appears only as a
   commit convention in the Orchestra skill.
3. For the self-modifying systems (dgm, sica, godel-agent, stop), the summaries
   describe benchmark-validated acceptance and, for some, containers. They do not
   describe a frozen evaluator or a human approval gate.
4. Several projects name self-grading leniency or confirmation bias as the problem
   they are built around (research-loop, loop-runner, scholar-loop).

## C. What this project took

These are design decisions, not findings.

| idea | from | here |
|---|---|---|
| falsifier required for every hypothesis | research-loop | `validate` (already in v0.1) |
| predictions recorded before a run and compared after | interpretable-autoresearch, scholar-loop | `predicted_verdict` is part of the locked card; `calibration` reports the hit rate and refuses to read meaning into fewer than ten predictions |
| a governor that stops the loop | scholar-loop, loop-runner | `govern`: stop after a streak of inconclusive cards, after cards with nothing supported, or when a card is too deep in a chain of revisions; limits live in a protected file |
| a graph of hypotheses with dependencies | research-loop | `depends_on`: a card cannot run unless the cited hypothesis of an earlier card has the required verdict |
| protected files | loop-runner, scholar-loop | `guard`: a manifest of the frozen core, checked against the approved branch; it reports changes rather than restoring them, so the decision stays with a human |
| no invented numbers or citations in prose | ARIS, Sakana v2, scholar-loop | `lint`: every number in the notes must appear in the recorded results; background claims need a `[src:ID]` to a verified source |
| leads that were not read are kept but not cited | ARIS | source registry (v0.1), now with `evidence_kind` |
| an archive of variants with lineage | dgm, sica, shinkaevolve | `evolve`: a hash-chained archive of variants with their parents and benchmark results |
| an independent reviewer | ARIS, loop-runner | a step in `loop/AGENT.md`: a separate agent with fresh context reviews the card, report and notes. It is the same model family and nothing enforces it, so it is weaker than a cross-family review |

## D. What this project added

These have no source here and have not been tested outside this repository's own
tests.

- **Mutation self-test.** The verifier is attacked on purpose and must catch each
  corruption by the check meant to catch it. The known blind spots are printed with
  every score.
- **Gate against the approved base.** A proposed change to the frozen core is
  compared with the manifest on the approved branch, so updating the manifest in the
  same change does not hide it.
- **Evidence kind.** A source records whether its evidence is the source's own text
  or a tool's summary of it.
- **Rounding rule in the lint.** A number in the notes is supported if some recorded
  number rounds to it at the precision written; truncation is not accepted.

## E. Not taken, and why

- **Tree search or population evolution of experiments** needs a model in the loop
  and tasks with automatic scores. Revisit when there are such tasks.
- **Cross-family review** needs a second model family, which this workspace does not
  offer.
- **A schedule-driven heartbeat**: the maintainer has deferred the frequency.
- **A container sandbox**: experiments here are code that is reviewed before merge.
  Revisit if experiment code starts to be generated in volume.
- **Paper-writing pipelines**: outside the scope of this stage.
