---
school: critique-process
title: Critique & Review — Braintrust, IDEO, Design Crits, WCAG 2.2
status: active
---

# Canon: Critique & Review — Braintrust, IDEO, Design Crits, WCAG 2.2

## Why this school is in the canon
Great design organizations differ less in raw talent than in how they examine work in progress. Pixar's Braintrust (Ed Catmull, *Creativity, Inc.*), IDEO/Stanford d.school facilitation methods, and modern industry crit practice (Figma, Jared Spool, Meta) converge on a small set of enforceable process rules that turn feedback from politics into diagnosis. WCAG 2.2 AA belongs here because it is the one part of design review that is fully numeric — the objective floor every review must check before taste enters the conversation.

## Philosophy
The core belief is Catmull's: "Early on, all of our movies suck." First versions are bad by nature, so the organization's job is to build a machine that reliably moves work "from suck to non-suck" — and that machine is candid, structured critique held early and often. Candor only survives under two protections. First, feedback is aimed at the work, never the person: "it's the film, not the filmmaker, that is under the microscope." Second, the reviewers have no authority. A Braintrust note is a diagnosis — what is wrong, what is missing, what isn't clear, what makes no sense — never a mandate. The maker retains full ownership of the fix, which is what makes it psychologically safe to hear that the baby is ugly. Strip either protection and candor collapses into either politeness (useless) or design-by-committee (worse).

The second belief, from IDEO and the d.school, is that divergence and convergence are different modes that must never share a room. Brainstorms run under "defer judgment, encourage wild ideas, go for quantity"; critiques run under the opposite discipline — focused, timeboxed, diagnostic. Feedback itself is scaffolded ("I like / I wish / What if", I-statements, listen without rebutting) so critical and appreciative input arrive in equal measure and in a form the maker can actually use. Jared Spool adds the framing move: separate "what are we trying to do?" from "does this rendition accomplish it?" — critique without an agreed problem statement is just opinion exchange.

Third: critique and review are different meetings. Critique asks "how can we make this better?" — it is generative, peer-to-peer, non-binding. Review asks "is this good enough to ship?" — it is a gate, with named decision-makers and explicit acceptance criteria. Conflating them produces the worst of both: gates with no criteria and critiques where nobody feels safe. The one set of review criteria that is never negotiable is the WCAG 2.2 AA numeric floor: contrast, target size, focus visibility, reflow, and text spacing are measured, not debated.

## Operational rules
| Rule | Category | Check | Threshold | Severity | Source |
|---|---|---|---|---|---|
| Every critique session opens with a stated problem/goal ("what are we trying to do?") before the artifact is shown; feedback that ignores the stated goal is ruled out of scope | process-workflow | process | Problem statement present in session record before first feedback item | block | Jared Spool, "Moving from Critical Review to Critique" (UIE) |
| Each feedback item must diagnose, not mandate: it states what is wrong, missing, unclear, or nonsensical; any proposed fix is labeled as illustration only | process-workflow | process | Note contains at least one of {wrong, missing, unclear, makes-no-sense}; imperative "change X to Y" without diagnosis fails | block | Ed Catmull, *Creativity, Inc.* (good-notes definition) |
| Critique output is advisory: the maker records a disposition (accept / adapt / decline + reason) for every note; no reviewer's note is auto-binding | process-workflow | process | 100% of logged notes have a maker-recorded disposition; no note marked "required" by a non-owner | block | Catmull, *Creativity, Inc.* (Braintrust has no authority) |
| Feedback is phrased about the artifact, not the maker: I-statements ("I wish…", "I'm confused by…"), no second-person fault-finding ("you didn't…") | process-workflow | process | Zero feedback items in the log that attribute fault to a person rather than the work | flag | Stanford d.school "I Like, I Wish, What If"; Catmull |
| Every participant's feedback includes both appreciative and critical items (I like + I wish/What if); all-negative or all-positive rounds are incomplete | process-workflow | process | Per participant per session: ≥1 "like" item and ≥1 "wish/what-if" item | flag | Stanford d.school / IDEO feedback protocol |
| Presenter declares up front what feedback is wanted and what is explicitly out of scope; out-of-scope feedback is deferred, not discussed | process-workflow | process | Session record contains "feedback wanted" and "feedback not wanted" fields before feedback begins | flag | Figma, "How we do design critiques at Figma" (Noah Levin) |
| Clarifying questions are a separate phase from feedback: no evaluative statements until the question phase closes | process-workflow | process | Session agenda: context (10–15 min) → clarifying questions (2–5 min) → feedback (10+ min) | flag | Figma crit structure |
| Critiques are timeboxed: at most 2 topics per 60-minute session; 20–30 minutes per topic | process-workflow | process | ≤2 topics / 60 min; 20–30 min per topic | advise | Figma, "How we do design critiques at Figma" |
| A session is declared as either critique (improve) or review (ship gate) before it starts; ship decisions may not be made in a session declared as critique | process-workflow | process | Session type field ∈ {critique, review}; decision log of a critique session contains no ship/no-ship verdict | block | The Crit / Spool (critique vs critical review distinction) |
| Divergent-phase work is brainstormed under defer-judgment rules (quantity target, wild ideas welcome); polish-level critique of early sketches is out of order | process-workflow | process | Work tagged "exploration" gets jam/workshop format, not polish critique; brainstorm targets high idea count (IDEO benchmark: up to 100 ideas/60 min) | advise | IDEO 7 rules of brainstorming |
| Drive-by feedback is invalid: notes count only from reviewers who attended the session (or its async equivalent) with the full context; out-of-band vetoes are escalations, not notes | process-workflow | process | Every logged note maps to a session participant; no post-hoc anonymous mandates | flag | Industry anti-pattern "swoop and poop"; Braintrust membership norms |
| The presenter does not rebut during the feedback round: responses are limited to thanks and clarifying questions; rebuttal/decisions happen after the session | process-workflow | process | No defense/justification turns by presenter inside the feedback phase of the log | advise | Stanford d.school (listen without responding) |
| Work is critiqued early and at regular intervals — first critique happens at low fidelity, before visual polish | process-workflow | process | ≥1 critique logged before high-fidelity mockups exist; recurring cadence on calendar (Braintrust: every few months per project; product crits: weekly) | advise | Catmull ("early on, all our movies suck"); Figma weekly crits |
| Text contrast: normal text ≥ 4.5:1 against background; large text (≥18pt/24px regular, or ≥14pt/18.66px bold) ≥ 3:1 | accessibility | deterministic | ≥4.5:1 normal; ≥3:1 large (large = ≥24px or ≥18.66px bold) | block | WCAG 2.2 SC 1.4.3 (AA) |
| Non-text contrast: UI component boundaries/states and meaningful graphical objects ≥ 3:1 against adjacent colors | accessibility | deterministic | ≥3:1 | block | WCAG 2.2 SC 1.4.11 (AA) |
| Pointer targets ≥ 24×24 CSS px, or an undersized target sits inside a 24px spacing circle that overlaps no other target (inline-text links exempt) | accessibility | deterministic | ≥24×24 CSS px or spacing exception | block | WCAG 2.2 SC 2.5.8 Target Size Minimum (AA) |
| Keyboard focus is always visible and never entirely obscured by author content (sticky headers, overlays); indicator should cover ≥ area of a 2 CSS px perimeter of the component and change with ≥3:1 contrast | accessibility | deterministic | Visible indicator on every focusable element; not fully hidden (2.4.11); 2px-perimeter area + 3:1 change (2.4.13 target) | block | WCAG 2.2 SC 2.4.7, 2.4.11 (AA); 2.4.13 (AAA, aspirational) |
| Reflow: content works at 320 CSS px viewport width (≈400% zoom) with no two-dimensional scrolling for text content | accessibility | deterministic | No horizontal scroll at 320 CSS px width (256 px height for horizontal-scroll content) | block | WCAG 2.2 SC 1.4.10 (AA) |
| Layout survives user text-spacing overrides with no clipping or overlap: line-height 1.5×, paragraph spacing 2×, letter spacing 0.12×, word spacing 0.16× font size; and text resizes to 200% without loss | accessibility | deterministic | 1.5 / 2.0 / 0.12 / 0.16 × font-size; 200% text resize | block | WCAG 2.2 SC 1.4.12, 1.4.4 (AA) |
| Color is never the only visual carrier of information (state, error, link, chart series) — a second cue (icon, underline, label, pattern) must exist | accessibility | vision | Every color-encoded meaning has a redundant non-color cue verifiable in grayscale | block | WCAG 2.2 SC 1.4.1 (A) |
| Any drag interaction has a single-pointer non-drag alternative (click/tap equivalents) unless dragging is essential | accessibility | deterministic | 100% of drag operations have a non-drag path | flag | WCAG 2.2 SC 2.5.7 (AA) |

## Workflow practices
1. **Standing cadence, scheduled early.** Crits recur on the calendar (Figma: topics claimed Monday morning as mini-deadlines; Pixar: Braintrust convenes every few months per film, plus dailies). Regularity is what makes candor survivable — feedback from strangers is an attack; feedback from a standing group is a service.
2. **Standard crit structure (Figma):** presenter shares background, problem/objective, level of effort, and project stage (10–15 min) → clarifying questions only (2–5 min) → feedback (10+ min, round-the-room at ~2 min/person or popcorn) → thanks (1 min). Max 2 topics per hour; use a physical timer; budget 10 extra minutes per topic.
3. **Match format to stage.** Six named formats (Figma): standard crit, jams/workshops (divergent, e.g. Crazy 8s — 8 ideas in 8 minutes), pair design (2–3 people), silent crit (simultaneous written comments in the file), paper crit (printouts + stickies, ≤1×/month), FYI share (~5 min, context only, no feedback solicited). Divergent work gets IDEO brainstorm rules: defer judgment, encourage wild ideas, build on others ("and", not "but"), stay on topic, one conversation at a time, be visual, go for quantity (up to 100 ideas/hour).
4. **Braintrust protocol (Pixar):** reviewers are peers who have made the thing themselves ("experts with empathy"), the meeting exists to identify problems not to fix them, and the group has zero authority — the director leaves with notes and full ownership of what to do about them. Good notes are specific, timely (early enough to act on), and diagnostic.
5. **Feedback scaffold (d.school):** contributions phrased as "I like… / I wish… / What if…", kept to succinct headlines, delivered as I-statements; the receiver listens without responding beyond "thank you" until the round completes.
6. **Separate goals from execution (Spool):** first agree on what the design is trying to accomplish, then critique whether this rendition accomplishes it. The presenter opens rationale, not just pixels.
7. **Document and disposition.** Assign a note-taker; record every note; the maker publishes a disposition (accept / adapt / decline + why) afterward. Undispositioned feedback is treated as lost work.
8. **Run the WCAG floor before the taste conversation.** Automated pass on contrast (4.5:1 / 3:1), target size (24px), focus visibility, reflow (320px), and text spacing (1.5/2.0/0.12/0.16) precedes any subjective critique in a ship review — numbers first, opinions second.

## Anti-patterns (reject on sight)
- **Swoop and poop:** a stakeholder with no session context drops mandate-style feedback and disappears. Notes from non-participants are escalations, not critique.
- **Design by committee:** treating critique output as votes to be tallied or orders to be executed; the Braintrust model exists specifically to prevent this — reviewers diagnose, the maker decides.
- **Prescription without diagnosis:** "make the button blue" with no statement of what problem the note is solving.
- **Vague notes:** "it doesn't pop", "make it cleaner" — fails the Catmull specificity test (no identifiable wrong/missing/unclear element).
- **Critique-as-ambush review:** a "feedback session" that ends with a ship/kill verdict nobody agreed was on the table.
- **Polish critique of exploration work:** nitpicking type and spacing on a divergent-phase sketch (judging in a defer-judgment phase).
- **Presenter litigating every note in-session:** defending instead of listening; rebuttal belongs after the round.
- **All-negative rounds:** critique logs with zero "what's working" items — Spool's two concurrent themes (positive impressions + concerns) are both mandatory.
- **Personal attributions:** "you didn't think about mobile" instead of "I don't see how this works at 320px".
- **Debating accessibility numbers:** treating 4.5:1 contrast, 24px targets, or visible focus as stylistic preferences open to taste-based waiver.
- **Late notes:** feedback delivered after the point where it can still be acted on (fails Catmull's "timely" test).

## In their words
- "A good note says what is wrong, what is missing, what isn't clear, what makes no sense. A good note is offered at a timely moment… it doesn't make demands; it doesn't even have to include a proposed fix… Most of all, a good note is specific." — Ed Catmull, *Creativity, Inc.*
- "Early on, all of our movies suck." — Ed Catmull, *Creativity, Inc.*
- "The Braintrust has no authority… it is up to [the director] to figure out how to address the feedback." — Ed Catmull, *Creativity, Inc.*
- "It's the film, not the filmmaker, that is under the microscope." — Ed Catmull, *Creativity, Inc.*
- "Candor isn't cruel. It does not destroy." — Ed Catmull, *Creativity, Inc.*
- "Defer judgment… encourage wild ideas… go for quantity." — IDEO, Seven Rules of Brainstorming
- "Feedback is best given in I-statements: 'I wish there was an easier way to search' rather than 'You didn't include an easy-to-use search function.'" — Stanford d.school, "I Like, I Wish, What If"
- "In critique you are not there to find flaws, but to learn from the design… separate 'what are we trying to do with this design?' from 'does this rendition accomplish it?'" — Jared Spool, UIE
- "Critique asks 'How can we make this better?' Review asks 'Is this good enough to move forward?'" — The Crit, "Design Critique vs Design Review"
- "The size of the target for pointer inputs is at least 24 by 24 CSS pixels." — WCAG 2.2, SC 2.5.8
