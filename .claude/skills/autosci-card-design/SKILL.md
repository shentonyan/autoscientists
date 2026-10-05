---
name: autosci-card-design
description: Design review for an AutoScientists research card before it is locked - refutation criteria, negative control, independent cross-check, sample size, predicted verdicts. Use this whenever you are about to write or lock a card, turn a research idea into hypotheses, design an experiment module, or the user asks whether a design is sound, even if they only say "set up the experiment".
---

# Card design review

Locking hashes the card and the experiment source, so a weak design cannot be quietly
repaired afterwards; it can only be superseded. Answer these briefly in the card
(`question`, `falsifier`) and at length in the journal *before* `lock`; notes do not
exist yet. Field shapes are in `../autoscientists/card-schema.md`.

1. **Refutation.** For each hypothesis, which concrete recorded number would make it
   false? If no outcome could, it is not a hypothesis; rewrite or drop it.
2. **Negative control.** Include at least one hypothesis you expect to be refuted, or a
   case where the answer is known to be no. If the pipeline cannot say "no", its "yes"
   means little. Use a claim that is false in the world (as in
   `cards/auction-calibration.json` H3), not just a pipeline sanity check.
3. **Independent cross-check.** `crosscheck` must reach the answer by a different route
   (closed form, exact enumeration, a second algorithm). If it imports the experiment's
   helper functions or shares its assumptions it only checks that the code agrees with
   itself. State what it does share.
4. **Noise.** Use a fixed seed and a sample size large enough that the decision
   threshold is several standard errors from the effect. Record the standard error.
   *Exact claims* ("is it exactly 1/6?"): a simulation can only show consistency
   within an interval. Say so in the hypothesis, and make the exact computation
   (enumeration, closed form) the cross-check.
5. **Answerable here?** Computation or sources that can be read. If the claim needs
   data you cannot get, say so and mark the card `blocked` rather than simulating the
   answer you want.
6. **Predictions.** Set `predicted_verdict` per hypothesis from your honest prior. Do
   not choose them after seeing results. Ids containing "calibration" are excluded from
   the calibration statistic.
7. **Dependencies.** `depends_on` for cards you build on, `supersedes` for ones you
   revise.

Prefer a small, exactly checkable claim over a broad one. Run `python -m autosci validate <id>`
before locking.
