# design-os — the design harness

This repository is the de facto design authority for everything we ship: product
UI, marketing pages, brand assets, dashboards. It is a **harness, not a prompt**.
The difference matters and it is enforced:

- A prompt asks a model to care about quality. A harness makes not-caring
  mechanically impossible: rules have IDs, thresholds, and severities; numeric
  rules are *computed* by lint code, never narrated; judgment rules demand
  per-rule verdicts with visible evidence; workflow rules are validated against
  a process log; and nothing with an unwaived `block` failure ever auto-ships.
- Creative flexibility is real but priced: any rule can be broken **through a
  waiver** — scoped, rationale-carrying, expiring, human-approved. Breaking a
  rule silently is the only thing that is never allowed.

## The four layers

| Layer | Where | What it is |
|---|---|---|
| **Canon** | `design_os/canon/*.md` | The distilled philosophies, rules, and workflows of the masters — Rams, the Swiss school, Refactoring UI, the Linear/Stripe/Vercel craft culture, Apple HIG, the brand identity masters, the typography canon, design-system governance, critique practice, motion, and information design. Human- and agent-readable; the *why* behind every rule. |
| **Catalog** | `design_os/rules/catalog.yaml` | Every enforceable rule, deduped across schools, with a stable ID (`TYPE-001`…), a category, a check type (`deterministic` / `vision` / `process`), a threshold where one exists, a severity (`block` / `flag` / `advise`), and its sources. Validated strictly by `design_os/rules/loader.py`: a deterministic rule without a threshold, or a `block` without a mechanically arguable criterion, fails to load. |
| **Engine** | `design_os/lint/`, `design_os/critique/lenses.py`, `design_os/harness.py` | Deterministic rules run as real code over a live style snapshot (`lint/extract.py` + `lint/checks.py`, bound to rule IDs in `lint/bindings.yaml`). Vision rules are judged by a three-lens critique panel (structure / craft / brand), each lens armed with its canon and required to return a verdict *per rule* with evidence. Verdicts merge; waivers apply visibly. |
| **Process** | `design_os/process/protocol.py` | The workflow itself is gated: brief with a testable taste contract (adjectives can't carry a constraint), ≥3 genuinely divergent directions before convergence, kills recorded with reasons, tokens-first build with argued inventions, self-lint with zero unwaived block failures, multi-lens critique with every fail addressed. Validated mechanically from a process log. |

## Iron rules (non-negotiable, enforced in code)

1. **No unwaived `block` failure ever auto-ships.** `run_target` forces the
   approval item onto the human-held path regardless of composite score
   (`design_os/orchestrator/run.py`).
2. **Numbers are computed, not judged.** If a rule has a threshold, it runs in
   `lint/checks.py`. A vision model is never asked to eyeball a contrast ratio.
3. **Every verdict carries evidence.** A lens that can't name the failing
   element hasn't found a failure.
4. **Waivers are the only escape hatch** — scoped (never `*`), rationale ≥ 5
   words, expiring, attributed. Expired waivers are hard errors, not warnings.
5. **Gaps are visible.** A deterministic rule with no bound check reports
   `unimplemented`; a lens that returns nothing yields `n/a`, never a silent pass.
6. **Taste is subordinate to function** (kai-taste's iron law, inherited
   unchanged). The harness holds work back; it never auto-polishes judgment
   calls — those flag for humans.

## If you are an agent doing design work

1. Read the canon files relevant to your task (all of `design_os/canon/` if unsure).
2. Load the catalog; know which rules are `block` before you start.
3. Keep a process log (shape documented in `design_os/process/protocol.py`) as
   you work — brief → divergence → convergence → build → self-lint → critique.
4. Self-lint before critique: `extract_style_snapshot(url)` + `run_lint(...)`.
5. Run the lens panel; address every fail — fix it, waive it (with a real
   rationale in `waivers.yaml`), or argue it to a human. Never ignore it.
6. Validate your process log with `validate_process_log` before calling the work done.

## Extending the harness

- **New rule**: add it to `catalog.yaml` with sources pointing at canon. If it
  has a threshold, bind a check in `lint/bindings.yaml` (implement in
  `lint/checks.py` if needed). Loader validation is the review.
- **New school**: add a canon file, cite it from rules. Canon without rules is
  decoration; rules without canon are dogma — keep both ends attached.
- **Disagreement between schools**: record it in the rule's `tension` field.
  The catalog carries honest tensions; it does not silently pick winners.
