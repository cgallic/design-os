---
school: motion-design
title: "Motion: Disney Principles + Material / IBM Carbon / Apple Motion Specs"
status: active
---

# Canon: Motion — Disney Principles + Material / IBM Carbon / Apple Motion Specs

## Why this school is in the canon

Motion is the layer of UI design with the most codified numeric law and the most frequent abuse. Disney's 12 principles (Frank Thomas & Ollie Johnston, *The Illusion of Life*, 1981) supply the perceptual physics — easing, staging, follow-through — and the three dominant design systems (Google Material, IBM Carbon, Apple) have converted them into exact millisecond durations and cubic-bezier curves. This school exists so that no agent ever types an ad-hoc `transition: all 0.5s linear` again: nearly every motion decision has an enforceable token, threshold, or ban.

## Philosophy

Motion in UI is a usability instrument, not decoration. Its jobs are exactly four: keep the user oriented during state change (where did this come from, where did it go), give feedback that input was received, direct attention to the one thing that matters right now, and express brand character at a small number of deliberate moments. Issara Willenskomer's UX in Motion Manifesto sharpens the point: UI animation is a distinct medium from character animation — "UI Animation is to the '12 UX in Motion Principles' as construction is to architecture" — and the Disney principle that survives fully intact is slow-in/slow-out (easing). Objects in an interface still obey perceived physics: nothing real starts or stops instantaneously, so linear movement reads as broken.

The systems converge on a shared physics. Speed is a function of distance: the larger the change in distance traveled or size scaled, the longer the animation — but always inside a hard band, because users see transitions hundreds of times a day. Material's ceiling: transitions that exceed 400ms feel too slow; Carbon's floor: micro-interactions must respond in 70–120ms or the interface feels dead. Asymmetry is deliberate: entrances get longer durations and decelerating (ease-out) curves because the user's attention is arriving with the element; exits get shorter durations and accelerating (ease-in) curves because the user has already moved on. Carbon splits all motion into two modes — productive (fast, subtle, task-focused; the default) and expressive (slower, vibrant, reserved for singular significant moments) — and treats expressive motion as a rhythmic break to be rationed, not a default voice.

The final tenet is restraint and consent. Apple's HIG: avoid adding motion to interactions that occur frequently, make motion optional, and never let animation be the only carrier of information. Springs replaced duration curves in iOS precisely because real interaction is interruptible — motion must inherit gesture velocity and retarget mid-flight rather than lock the user out. And accessibility is a hard gate: parallax, scaling, spinning, and auto-playing motion must degrade to fades or nothing under reduced-motion settings, per Apple, Material, and WCAG alike.

## The verified token tables (reference data)

**Material Design 3 easing tokens** (md.sys.motion.easing.*):
| Token | Value |
|---|---|
| linear | cubic-bezier(0, 0, 1, 1) |
| standard | cubic-bezier(0.2, 0, 0, 1) |
| standard-decelerate | cubic-bezier(0, 0, 0, 1) |
| standard-accelerate | cubic-bezier(0.3, 0, 1, 1) |
| emphasized | path M 0,0 C 0.05,0 0.133333,0.06 0.166666,0.4 C 0.208333,0.82 0.25,1 1,1 (≈ standard, stronger tail) |
| emphasized-decelerate | cubic-bezier(0.05, 0.7, 0.1, 1) |
| emphasized-accelerate | cubic-bezier(0.3, 0, 0.8, 0.15) |

**Material Design 3 duration tokens** (md.sys.motion.duration.*): short1–4 = 50/100/150/200ms; medium1–4 = 250/300/350/400ms; long1–4 = 450/500/550/600ms; extra-long1–4 = 700/800/900/1000ms. Pair enter/persistent transitions with emphasized-decelerate at longer tokens (~400–500ms); exits/dismissals with emphasized-accelerate at shorter tokens (~200ms).

**Material 1.x/2.x numeric baselines**: mobile standard transition 300ms; entering elements 225ms; leaving elements 195ms; full-screen up to 375ms; "transitions that exceed 400ms may feel too slow." Tablet +30%, wearables −30%, desktop 150–200ms. Legacy curves: standard cubic-bezier(0.4, 0, 0.2, 1); decelerate (0, 0, 0.2, 1); accelerate (0.4, 0, 1, 1); sharp (0.4, 0, 0.6, 1).

**IBM Carbon duration tokens** (verified from @carbon/motion source):
| Token | Value | Use |
|---|---|---|
| fast-01 | 70ms | micro-interactions: buttons, toggles |
| fast-02 | 110ms | micro-interactions: fades |
| moderate-01 | 150ms | small expansions, short-distance moves |
| moderate-02 | 240ms | expansion, system communication, toasts |
| slow-01 | 400ms | large expansions, important notifications |
| slow-02 | 700ms | background dimming only |

**IBM Carbon easing curves** (verified from @carbon/motion source):
| Curve | Productive | Expressive |
|---|---|---|
| standard (visible throughout) | cubic-bezier(0.2, 0, 0.38, 0.9) | cubic-bezier(0.4, 0.14, 0.3, 1) |
| entrance (element appears) | cubic-bezier(0, 0, 0.38, 0.9) | cubic-bezier(0, 0, 0.3, 1) |
| exit (element disappears) | cubic-bezier(0.2, 0, 1, 0.9) | cubic-bezier(0.4, 0.14, 1, 1) |

Exception: a panel that stays "ready to reappear" (side panel) exits with standard, not exit, easing.

**Apple springs** (WWDC23 "Animate with springs"): two parameters, duration + bounce. Bounce ~15% is imperceptible-but-organic, ~30% is noticeably bouncy, above ~40% feels exaggerated for UI. Bounce 0 (critically damped) is "the most versatile" default. Springs are the only animation type that preserves continuity for both static starts and gesture-velocity handoff; SwiftUI tracks gesture velocity automatically and springs inherit it when retargeted mid-animation.

## Operational rules

| Rule | Category | Check | Threshold | Severity | Source |
|---|---|---|---|---|---|
| No linear easing on any animation of position, scale, or size; linear is permitted only for opacity-only or color-only fades. | motion | deterministic | timing-function on transform/layout properties must not be `linear` / cubic-bezier(0,0,1,1) | block | Disney principle 6 (slow in/slow out); Willenskomer UX in Motion Manifesto; M3 easing tokens |
| Entering elements use a decelerate (ease-out) curve; exiting elements use an accelerate (ease-in) curve; elements visible throughout use a standard (ease-in-out) curve. | motion | deterministic | enter curves: M3 (0,0,0,1)/(0.05,0.7,0.1,1) or Carbon (0,0,0.38,0.9)/(0,0,0.3,1); exit curves: M3 (0.3,0,1,1)/(0.3,0,0.8,0.15) or Carbon (0.2,0,1,0.9)/(0.4,0.14,1,1); or curves within ±0.1 per control point | block | Material M1–M3 easing guidance; Carbon entrance/exit easings |
| Every duration and easing value must come from a declared token scale (≤16 duration values, ≤8 easing curves per product); no ad-hoc values like 347ms. | motion | deterministic | all `transition`/`animation` durations ∈ declared token set; scale bounded 50–1000ms | flag | M3 duration/easing tokens; @carbon/motion package |
| Micro-interaction feedback (button press, toggle, hover state, control state change) completes in 70–150ms; visible response begins within 100ms of input. | motion | deterministic | duration ∈ [70, 150]ms for control-state animation; first frame of feedback ≤100ms after event | block | Carbon fast-01/fast-02 + "90–120ms immediate feedback"; M2 (switch 100ms) |
| No user-blocking transition exceeds 400ms on desktop/web productive UI; full-screen or expressive transitions may reach 600ms; absolute ceiling for any UI transition is 1000ms. | motion | deterministic | standard transitions ≤400ms; full-screen ≤600ms (M3 long4); background dimming ≤700ms (Carbon slow-02); hard cap 1000ms | block | M1: "transitions that exceed 400ms may feel too slow"; M3 duration scale; Carbon slow-01/02 |
| Exit/dismiss/collapse animations are shorter than the corresponding enter/expand animation of the same element. | motion | deterministic | exit duration < enter duration (Material reference ratio ≈ 195:225 mobile, ≈ 200:400–500 in M3 emphasized pairing) | flag | M1 duration guidance; M3 applying easing & duration |
| Duration scales monotonically with distance traveled or size change: within one flow, an animation covering a larger area must not be shorter than one covering a smaller area. | motion | deterministic | for animations in same view: duration ordering matches area/distance ordering, within the token scale | flag | Carbon "the larger the change in distance or size, the longer the animation"; M3 "consistent sense of speed" |
| Default to productive/functional motion; expressive (slower, more dramatic) motion is reserved for singular significant moments — at most one expressive motion moment per view. | motion | vision | count of expressive-class animations (duration >400ms or emphasized/expressive curve on large elements) per view ≤1 | flag | Carbon productive vs expressive; M3 emphasized set usage |
| Every animation involving scaling, spinning, parallax, depth/blur effects, or peripheral movement must have a reduced-motion branch that replaces it with a fade or removes it. | accessibility | deterministic | `prefers-reduced-motion: reduce` (or platform equivalent) handled for all transform-based animations; parallax/auto-effects disabled under it | block | Apple HIG Motion ("make motion optional"); M3 accessibility guidance; WCAG 2.3.3 |
| Auto-playing or looping motion that lasts longer than 5 seconds must have a visible pause/stop/hide control. | accessibility | deterministic | autoplay animation duration >5s ⇒ pause control present | block | WCAG 2.2.2 (referenced by Material and Apple accessibility guidance) |
| Nothing on screen flashes more than 3 times in any one second. | accessibility | deterministic | flash frequency ≤3/s | block | WCAG 2.3.1 |
| Do not add custom animation to interactions that occur many times per session (typing, scrolling, routine hovers, list row interactions) beyond instant state feedback. | motion | vision | frequent-path interactions have no decorative animation >150ms; judged against interaction frequency | flag | Apple HIG: "avoid adding motion to interactions that occur frequently" |
| Gesture-driven and interruptible animations use springs (or equivalent velocity-preserving curves), inherit gesture velocity, and must never lock input while settling. | motion | deterministic | gesture-released animation uses spring/velocity handoff; no input-blocking during settle | flag | Apple WWDC23 "Animate with springs" |
| If a spring animates productive UI, bounce ≤0.4 (dampingFraction ≥~0.6); default to bounce 0 when in doubt; at most one visible overshoot. | motion | deterministic | spring bounce parameter ∈ [0, 0.4]; bounce 0 default | flag | Apple WWDC23: >40% bounce "feels too exaggerated"; bounce 0 "most versatile" |
| No bounce, elastic, stretch, or sudden-stop easing in productive/task-focused UI (no cubic-bezier control points outside y ∈ [0,1] on task surfaces). | motion | deterministic | cubic-bezier y-values ∈ [0,1] for productive contexts; overshoot curves only in expressive moments | flag | Carbon: "avoid bounce, stretch, or sudden stop easing curves" |
| One focal element per transition (staging): no more than one primary animated group at a time; secondary elements follow the primary via stagger/offset (~20–50ms steps), never as simultaneous competing motion. | motion | vision | ≤1 primary moving group; secondary elements delayed 20–50ms per step; competing simultaneous large motions = fail | flag | Disney principle 3 (staging) + 5 (follow-through/overlap); Willenskomer offset & delay |
| New elements must have a spatial or causal origin: anything that appears mid-flow should transform, expand, mask, or clone from an existing element or screen edge rather than popping in — unless it is a system interruption (alert, toast). | motion | vision | appearing element traceable to trigger location, screen edge, or fade-in; unexplained pop-in = fail | advise | Willenskomer (parenting, cloning, masking); M3 transition patterns |
| Animate only compositor-friendly properties: transform and opacity. Animating layout properties (width, height, top, left, margin) is banned unless a FLIP-style transform technique is used. | motion | deterministic | animated CSS properties ⊆ {transform, opacity, filter}; layout property in @keyframes/transition = fail | flag | Material "Implementing Motion" (Naimark) and platform performance guidance |
| Scale durations per platform: desktop/web 150–200ms baseline for standard transitions, mobile ~300ms, tablet +30%, wearables −30%. | motion | deterministic | platform baseline within stated band | advise | M2 Speed: platform duration scaling |
| Motion must never be the sole carrier of information: any state communicated by animation is also communicated by a persistent visual (color, icon, text, position). | accessibility | vision | after animation completes, the state change remains legible from a static screenshot | block | Apple HIG: motion optional, not the only way to communicate |

## Workflow practices

1. **Tokens before animation.** Define the product's motion token set first — durations (Carbon's 6 or Material's 16) and easing curves (standard/entrance/exit × productive/expressive, or Material's standard/emphasized sets) — and forbid raw values in component code. All three systems ship motion as importable tokens (`@carbon/motion`, `md.sys.motion.*`, SwiftUI presets), not as per-component decisions.
2. **Classify the moment before designing it.** For every animation, first ask: productive (task-focused, subtle, fast) or expressive (a significant moment worth celebrating)? Carbon labels every motion spec blue (productive) or magenta (expressive) before any curve is drawn. Expressive moments are rationed deliberately.
3. **Write motion specs as engineering tables.** IBM's handoff format (Stephanie Cree, IBM Design): per element, a table of property animated, duration token, easing token, and delay — never "make it feel snappy." A motion spec that an engineer cannot implement without asking questions is incomplete.
4. **Compute, don't guess, distance-based durations.** Carbon provides a Motion Generator that calculates duration from distance/size change; Material scales duration with transition area. When an animation travels farther, look up the longer token — do not eyeball it.
5. **Review at reduced speed and frame-by-frame.** Animation review means stepping through the curve (dev-tools timeline, 10x slowdown) to verify the easing actually matches the spec'd curve, not judging at full speed where anything looks fine once.
6. **QA pass with reduce-motion enabled.** Every review includes a run with `prefers-reduced-motion` / iOS Reduce Motion on; the app must remain fully usable and communicative. Apple App Store accessibility evaluation makes this an audit criterion.
7. **Prototype on the target device at real speed.** Durations feel different per platform (M2: mobile 300ms, desktop 150–200ms); a curve approved in a desktop prototype is not approved for watch or mobile.
8. **Prefer springs for anything a finger touches.** For gesture-driven UI, spec spring parameters (duration + bounce) instead of duration + bezier, so interruption and velocity handoff come for free (Apple WWDC23). Use bounce 0 unless the moment is explicitly playful.

## Anti-patterns (reject on sight)

- `transition: all 0.5s linear` — linear easing on movement, `all` transitions, and out-of-band durations in one line.
- Ad-hoc durations (280ms, 347ms, 0.45s) that belong to no token scale.
- Any blocking transition over 400ms in task UI; any UI animation at or over 1 second.
- Exit animations slower than entrances — making the user wait to leave.
- Ease-in (accelerate) curves on entering elements, or ease-out on exits — inverted physics.
- Bounce/elastic/overshoot easing on form controls, tables, or any productive surface.
- Buttons or controls whose press feedback takes longer than ~150ms, or arrives later than 100ms.
- Parallax, spinning, zooming, or auto-playing motion with no `prefers-reduced-motion` fallback.
- Decorative animation on high-frequency interactions (every keystroke, every hover in a list, every scroll tick).
- Multiple elements animating simultaneously with equal visual weight — no staging, no focal point.
- Animating `width`/`height`/`top`/`left`/`margin` directly (layout thrash) instead of transforms.
- Uninterruptible animations that swallow input while they finish; gesture releases that snap to a canned curve, discarding the user's velocity.
- Motion as the only signal of a state change (nothing persists once the animation ends).
- Skeleton/loading animations that flash faster than 3 times per second.

## In their words

- "Transitions that exceed 400ms may feel too slow." — Material Design (M1, Duration & Easing)
- "The larger the change in distance (traveled) or size (scaling) of the element, the longer the animation takes." — IBM Carbon Design System, Motion
- "Expressive motion delivers enthusiastic and vibrant movement... Use expressive motion for significant moments." — IBM Carbon Design System, Motion
- "Avoid adding motion to interactions that occur frequently... avoid making people spend extra time watching unnecessary motion every time they interact with something." — Apple Human Interface Guidelines, Motion
- "When you're unsure what to use, a spring with bounce 0 provides a great general-purpose spring that's the most versatile." — Apple, WWDC23 "Animate with springs"
- "UI Animation is to the '12 UX in Motion Principles' as construction is to architecture." — Issara Willenskomer, UX in Motion Manifesto
- "What seems real to the mind can be as important as any material fact." — Walt Disney (via *The Illusion of Life* tradition)
