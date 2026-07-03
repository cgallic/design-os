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
| **Catalog** | `design_os/rules/catalog.yaml` | Every enforceable rule, deduped across schools, with a stable ID (`TYPE-001`…), a category, a check type (`deterministic` / `vision` / `process` / `behavioral`), a threshold where one exists, a severity (`block` / `flag` / `advise`), an artifact scope (`applies_to`: page, dashboard, chart, identity, print, flow, project, org — so ceremony and identity gates never misfire on a page audit), and its sources. Validated strictly by `design_os/rules/loader.py`: a deterministic rule without a threshold, or a `block` without a mechanically arguable criterion, fails to load. |
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

## The workflow canon (how the masters actually work)

Distilled from the canon's workflow practices — the process mechanics worth
treating as gates. The first six are enforced by `design_os/process/protocol.py`
today; the rest are the bar to hold yourself to (and future gate candidates):

1. **Decide on artifacts, never descriptions** (Rams, Apple). No direction
   passes a decision gate without a rendered artifact with real content.
   Enforced: every divergence direction requires an `artifact`.
2. **Documented divergence before convergence** (Apple's 10→3→1). Enforced:
   ≥3 directions with distinct premises; kills recorded with reasons.
3. **Run the deterministic floor before the taste conversation** (critique
   canon). Numbers first, opinions second. Enforced: `self_lint` must be clean
   (or waived) before `critique`.
4. **Declare the session type** (Pixar/Spool): a *critique* improves and is
   non-binding; a *review* is a ship gate with a named decider. Never blur them.
5. **Taste contracts, not adjectives** (Vignelli's semantic-first discipline).
   Enforced: brief constraints must carry a checkable core.
6. **Reuse argues for free; invention argues for itself** (system governance).
   Enforced: every invented component needs a written reason.
7. **Verify the real surface** (Vercel/Stripe): no sign-off from code
   inspection — attach a screenshot or recording of the rendered artifact.
8. **Grayscale first** (Refactoring UI): hierarchy must work in gray before
   color is admitted.
9. **Back-of-the-drawer states** (Apple/Linear): empty, loading, error,
   permission-denied, offline, max-text-size — designed before ship, not after.
10. **Design by erasure with a stopping rule** (Tufte): iterate deletions;
    ship the version one step before information loss.
11. **Semantics → format → grid → content** (Swiss school): the brief precedes
    the canvas precedes the grid precedes the layout.
12. **Body text first** (Bringhurst/Butterick): approve the body spec before
    any display styling exists.
13. **Cold-read exit** (Vignelli's pragmatic test): a fresh reader states what
    the artifact says with zero explanation, or it isn't done.
14. **Friction logs on a cadence** (Stripe): walk the essential journeys
    end-to-end, score coarsely, track the trend, triage everything.
15. **Scope-cut, never polish-cut** (Linear): under pressure, drop features —
    never states, accessibility, or detail passes.

## Known gaps (roadmap, not shame)

The completeness audit identified schools with enforceable substance not yet
in the catalog: Norman/Nielsen error-UX and system-status rules (undo over
confirmation, progress-indicator ladders), UX writing/microcopy (reading grade,
verb-first labels, error-copy anatomy), form design (Wroblewski/Baymard),
Gestalt proximity ratios (within-group spacing < between-group spacing),
internationalization readiness (+30–50% string expansion, RTL), and
quantitative HCI laws (Hick/Fitts ceilings). Sound/haptics, dark-mode parity,
and breakpoint discipline are uncovered. Add them as new canon files + catalog
rules; do not bolt unsourced rules onto existing schools.

## Extending the harness

- **New rule**: add it to `catalog.yaml` with sources pointing at canon. If it
  has a threshold, bind a check in `lint/bindings.yaml` (implement in
  `lint/checks.py` if needed). Loader validation is the review.
- **New school**: add a canon file, cite it from rules. Canon without rules is
  decoration; rules without canon are dogma — keep both ends attached.
- **Disagreement between schools**: record it in the rule's `tension` field.
  The catalog carries honest tensions; it does not silently pick winners.
