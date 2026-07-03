---
school: interface-craft
title: Modern Interface Craft — Rauno Freiberg, Emil Kowalski & the Design-Engineer School
status: active
---

# Canon: Modern Interface Craft — Rauno Freiberg, Emil Kowalski & the Design-Engineer School

## Why this school is in the canon

This is the school of the working design engineer: people who both design and build production interfaces (Vercel, Linear, The Browser Company, Raycast orbit) and who wrote their craft down as literally checkable rules. Rauno Freiberg's Web Interface Guidelines (interfaces.rauno.me, later expanded into Vercel's Web Interface Guidelines) is the closest thing the field has to a lintable spec for interface feel; Emil Kowalski's Sonner and Vaul (tens of millions of npm downloads/week) are existence proofs that his animation rules produce components people love by default. Where Rams supplies restraint and Swiss supplies structure, this school supplies the harness's rules for *interaction*: touch targets, focus, keyboard, motion timing, optimistic UI, and perceived performance.

## Philosophy

The core belief is that quality lives in accumulated invisible details. "Executing well on details like these make products feel like a natural extension of ourselves" (Freiberg). No single detail is decisive — a correct `type` attribute, a hit target that extends past the visual edge, an ellipsis character instead of three periods — but users register their sum as trust. The corollary is robustness: Freiberg argues most interactions are brittle and fail under real-world stress, and if a UI works only 80% of the time the perception of quality breaks; core interactions — scrolling, text input, navigation — must work every time. Craft that collapses when you click mid-animation or rotate the phone is not craft.

Motion is a tool with a stated purpose, never a default. Emil Kowalski's defining contribution is knowing when *not* to animate: "Sometimes the best animation is no animation." An animation must explain something, give feedback about a state change, preserve spatial continuity, or (rarely, on infrequent surfaces) delight — and before animating you must name which. Frequency of use is the governing variable: interactions performed hundreds of times a day (command menus, keyboard shortcuts, context menus) should have little or no motion, because novelty decays into latency — "Raycast has no animations and it feels right." When motion is justified, its physics must be right: "Easing is the most important part of any animation," durations stay under ~200–300ms, only compositor properties move, and everything is interruptible, because "great interactions are modeled after properties from the real world, like interruptibility."

The workflow is inseparable from the philosophy: this school designs in the final medium. Freiberg skips wireframes entirely — "If you have an idea for a chair, you don't just draw pictures — you build prototypes out of wood or plastic. The material reveals strengths and limitations that shape the idea. With software, the material is code." Perceived performance beats measured performance: interfaces respond optimistically and instantly (toggles apply immediately, mutations render locally and roll back on error), and feedback appears where the user is looking — relative to its trigger. Taste is then shipped as defaults, in libraries and guidelines, so the craft compounds beyond one product.

## Operational rules

| Rule | Category | Check | Threshold | Severity | Source |
|---|---|---|---|---|---|
| Interaction-feedback animations (hover, press, toggle, open/close of small surfaces) complete in ≤200ms; no UI animation exceeds 300ms unless it is explicitly demonstrative/onboarding motion. | motion | deterministic | feedback ≤200ms; hard cap 300ms; measured from CSS/JS durations | block | Freiberg, Web Interface Guidelines ("Animation duration should not be more than 200ms for interactions to feel immediate"); Kowalski, "You Don't Need Animations" (under 300ms) |
| Keyboard-initiated actions have zero animation: command palettes, shortcut-triggered navigation, and keybound state changes render instantly (0ms entrance). | motion | deterministic | 0ms transition/animation on keyboard-triggered state changes | block | Kowalski, "Great Animations" / "You Don't Need Animations" ("You should never animate them"); Freiberg on command menus |
| High-frequency surfaces (context menus, dropdowns, tab switches, list hovers used many times per session) get no entrance animation; at most a subtle exit fade ≤150ms. | motion | deterministic | 0ms entrance on enumerated high-frequency components; exit ≤150ms | flag | Freiberg, "Invisible Details of Interaction Design" (macOS context menus); Kowalski frequency principle |
| Animate only compositor properties: `transform` and `opacity`. Never animate layout properties (`top`, `left`, `width`, `height`, `margin`, `padding`) and never use `transition: all`. | motion | deterministic | 0 layout-property animations; 0 `transition: all` declarations | block | Vercel Web Interface Guidelines; Kowalski, "Great Animations" (hardware acceleration) |
| No `linear` easing on spatial movement; entrances and user-initiated movement use a deceleration curve (ease-out family); elements already on screen use ease-in-out; prefer custom cubic-bezier over built-in CSS keywords. | motion | deterministic | 0 `linear` timing functions on transform movement; entrance curves decelerate | flag | Kowalski, "Good vs Great Animations" ("default to ease-out"; built-in curves "not strong enough") |
| Motion originates where it belongs: `transform-origin` matches the trigger's position (dropdown grows from its button), scale-in starts near identity (dialogs from ~0.8, pressed buttons to ~0.96–0.9, never from 0), and feedback displays adjacent to its trigger. | motion | deterministic | transform-origin points at trigger; scale range within [0.8, 1] for dialogs, [0.9, 1] for press states | flag | Kowalski, "Good vs Great Animations" (origin-aware); Freiberg, Web Interface Guidelines (scale values; "Display feedback relative to its trigger") |
| Animations and gestures are interruptible: new input during an animation retargets it immediately; input is never blocked while an animation completes; gesture-driven surfaces track the finger/pointer 1:1 before thresholds fire. | motion | vision | 0 input-blocking animations; mid-animation input visibly retargets | block | Freiberg, "Invisible Details" ("Great interactions are modeled after properties from the real world, like interruptibility"); Kowalski on interruptibility |
| `prefers-reduced-motion` is honored: motion-heavy animations get a reduced variant (opacity fade) or are disabled entirely. | accessibility | deterministic | 100% of transform-based animations gated or replaced under the media query | block | Kowalski, "Great Animations"; Vercel Web Interface Guidelines (MUST) |
| Switching color theme triggers no transitions or animations on elements. | motion | deterministic | 0 animated properties fire on theme toggle | flag | Freiberg, Web Interface Guidelines |
| Hit targets: ≥44px on touch, ≥24px on pointer devices; if the visual target is smaller, expand the hit area; interactive list items have no dead zones between them (extend `padding`, not `margin`); label and control share one hit target. | components-affordance | deterministic | touch ≥44px, pointer ≥24px, 0 dead zones in interactive lists | block | Vercel Web Interface Guidelines; Freiberg, Web Interface Guidelines (dead areas) |
| Every interactive element shows a visible focus ring under `:focus-visible`; `outline: none` without a visible replacement is forbidden; the ring follows the element's border radius (box-shadow technique where outline cannot). | accessibility | deterministic | 0 focusable elements without a visible :focus-visible style | block | Vercel Web Interface Guidelines (NEVER `outline: none` without replacement); Freiberg (box-shadow focus rings respect radius) |
| Full keyboard support: Enter submits a focused input (inputs wrapped in `<form>`; ⌘/Ctrl+Enter in textareas), sequential lists navigate with ↑/↓, composite widgets follow WAI-ARIA APG patterns, and modals trap then return focus. | accessibility | deterministic | 100% of flows completable by keyboard; APG pattern conformance for menus/dialogs/lists | block | Freiberg, Web Interface Guidelines; Vercel Web Interface Guidelines (APG) |
| Native form mechanics are never broken: clicking a label focuses its input, inputs carry the correct `type` and `inputmode`, paste is never blocked, mobile input font-size ≥16px (prevents iOS zoom), inputs never autofocus on touch devices. | components-affordance | deterministic | 0 violations across the enumerated list; input font-size ≥16px on mobile | block | Freiberg, Web Interface Guidelines; Vercel Web Interface Guidelines (NEVER block paste) |
| Optimistic by default: toggles take effect immediately without confirmation dialogs; mutations update the UI locally and roll back with visible feedback on server error; after submit, the button disables with a spinner while keeping its original label. | components-affordance | deterministic | visual state change ≤100ms after input; rollback + feedback path exists; 0 toggle-confirmation dialogs | flag | Freiberg, Web Interface Guidelines ("Toggles should immediately take effect"; "Optimistically update data locally and roll back on server error with feedback") |
| Perceived-performance budget: every input gets visual acknowledgment within 100ms; mutation round-trips target <500ms; lists >50 items are virtualized; if removing an animation makes a frequent flow feel faster, remove it. | craft-detail | deterministic | feedback ≤100ms; mutations <500ms; virtualization at >50 items | flag | Vercel Web Interface Guidelines; Freiberg, "Invisible Details" (bookmarking-tool anecdote: motion removed, same action felt faster) |
| UI typography: no font weights below 400; weight never changes on hover/selected state (layout shift); `font-variant-numeric: tabular-nums` on any column, timer, or comparing numbers; a real ellipsis character (…), not three periods. | typography | deterministic | 0 weights <400; 0 weight changes on state; tabular-nums on numeric alignment contexts | flag | Freiberg, Web Interface Guidelines; Vercel Web Interface Guidelines |
| State survives navigation: URL reflects app state (filters, tabs, pagination, expanded panels are deep-linkable) and Back/Forward restores prior scroll position. | content-information | deterministic | shareable URL reproduces view; scroll restored on history navigation | flag | Vercel Web Interface Guidelines |
| Touch is a first-class mode: hover-only affordances are forbidden (gate hover styles behind `@media (hover: hover)`); custom gestures set `touch-action`; safe-area insets respected; interactive inner content disables `user-select`; decorative overlays disable `pointer-events`. | components-affordance | deterministic | 0 hover-dependent critical affordances; safe-area env() present on fixed edge UI | flag | Freiberg, Web Interface Guidelines; Vercel Web Interface Guidelines |
| Empty states are never blank: they state what belongs there and prompt creation of the first item (optionally with templates). | content-information | vision | every list/collection view has a designed empty state with a primary action | advise | Freiberg, Web Interface Guidelines |

## Workflow practices

1. Design in the final medium, immediately. Skip wireframes and static mocks; open a code prototype on day one, because "the material is code" and the material pushes back with constraints a picture never reveals (Freiberg, ui.land interview).
2. Prototype to production *feel*, not production code. A few days to get an intricate interaction "very close to the feeling of production" while explicitly ignoring code quality, tests, and edge-case engineering — feel is what is being reviewed (Freiberg).
3. State the animation's purpose before animating. The review question for any motion: is it explaining, giving state feedback, preserving spatial continuity, or delighting on a rare surface? No named purpose → no animation (Kowalski, "You Don't Need Animations").
4. Run a frequency audit on every animated interaction: estimate how many times per day a real user triggers it. Hundreds of times → strip the motion; occasional → motion may earn its place (Kowalski; Freiberg on command/context menus).
5. Review choreography in slow motion. Play transitions at reduced speed to catch timing misalignments between simultaneously animating elements; add "just a touch of delay" to sequence related elements (Kowalski, "Good vs Great Animations"; Freiberg, Devouring Details).
6. Stress-test robustness like an adversary: click mid-animation, spam the button, resize the window, rotate the device, use keyboard only, use touch only. Core interactions (scroll, text input, navigation) must survive 100% of this, because 80%-reliable interactions destroy perceived quality (Freiberg).
7. Dissect great products as a standing habit. Rebuild details from iOS, macOS, Arc, Raycast, Linear to understand *why* they feel right (loupe, rubber-banding, app-switcher interruptibility); keep a bookmark/inspiration library of details (Freiberg, "Invisible Details"; Coursey).
8. Ship taste as defaults. Encode the school's decisions into reusable primitives and written guidelines (Sonner, Vaul, cmdk, interfaces.rauno.me) so the polish is the path of least resistance for every future screen — and match a component's easing/duration to the product's overall character, as Sonner deliberately uses slower `ease` "to make it feel more elegant" (Kowalski).
9. Sweat the long tail after the happy path works: animated icons, branded scrollbars, `::selection` styling, focus polish, keyboard shortcuts, tooltips — the accumulation is the brand (Coursey, ui.land interview).

## Anti-patterns (reject on sight)

- An animated command palette, or any animation on a keyboard-triggered action.
- Entrance animations on context menus, dropdowns, or other hundreds-of-times-a-day surfaces.
- `transition: all`, and animating `width`/`height`/`top`/`left`/`margin`/`padding`.
- `linear` easing on spatial movement; dialogs scaling in from 0; motion with default `transform-origin: center` growing out of nowhere instead of from its trigger.
- Non-interruptible animation that blocks input until it completes (the iOS Settings push, per Freiberg, vs. the interruptible App Switcher).
- `outline: none` with no visible focus replacement; focus rings that ignore border radius.
- Confirmation dialogs on toggles; spinners where an optimistic local update was possible.
- Blocking paste in inputs; wrong or missing input `type`; sub-16px mobile input text (iOS zoom); autofocus on touch.
- Dead zones between interactive list items (margin where padding belongs); visual targets under 24px with no expanded hit area.
- Hover-only affordances that leave touch users stranded; hover states firing on touch press.
- Ignoring `prefers-reduced-motion`.
- Theme switches that ripple transitions across the whole page.
- Filters, tabs, and scroll position lost on Back — state that isn't in the URL.
- Polish that is brittle: interactions that break when clicked mid-animation, resized, or driven by keyboard — the 80%-of-the-time UI.
- Animation added because it was possible ("animation for animation's sake"), graded by how impressive it looks rather than what it explains.

## In their words

- "Animation duration should not be more than 200ms for interactions to feel immediate." — Rauno Freiberg, Web Interface Guidelines (interfaces.rauno.me)
- "Toggles should immediately take effect, not require confirmation." — Rauno Freiberg, Web Interface Guidelines
- "Optimistically update data locally and roll back on server error with feedback." — Rauno Freiberg, Web Interface Guidelines
- "Great interactions are modeled after properties from the real world, like interruptibility." — Rauno Freiberg, "Invisible Details of Interaction Design"
- "Executing well on details like these make products feel like a natural extension of ourselves." — Rauno Freiberg, "Invisible Details of Interaction Design"
- "If you have an idea for a chair, you don't just draw pictures — you build prototypes out of wood or plastic. The material reveals strengths and limitations that shape the idea. With software, the material is code." — Rauno Freiberg (ui.land interview)
- If a UI only works 80% of the time, the perception of quality breaks; core interactions like scrolling, text input, and navigation must always work. — Rauno Freiberg on robustness (ui.land interview, paraphrase)
- "Sometimes the best animation is no animation." — Emil Kowalski, "You Don't Need Animations"
- "Easing is the most important part of any animation. It can make a bad animation feel great and a great animation feel bad." — Emil Kowalski, "Good vs Great Animations"
- "You should never animate them." — Emil Kowalski on keyboard-initiated actions, "Great Animations"
- "Raycast has no animations and it feels right." — Emil Kowalski, "Great Animations"
- "Nothing in the world around us disappears or appears instantly." — Emil Kowalski, "Great Animations"
- "Everyone's software is good enough these days… To stand out, you need to make your product feel great." — Emil Kowalski, "Good vs Great Animations"
- "Wonderful interactions don't have to be entirely practical." — Rauno Freiberg, "Invisible Details of Interaction Design" (on fidgetability — delight is allowed, on the right surfaces)
