---
school: information-design
title: Information Design — Tufte, Few & the Data Visualization Canon
status: active
---

# Canon: Information Design — Tufte, Few & the Data Visualization Canon

## Why this school is in the canon
Edward Tufte (statistician, Yale; *The Visual Display of Quantitative Information*, 1983) and Stephen Few (*Information Dashboard Design*; Perceptual Edge) wrote the operating manual for every serious chart and dashboard made since. Their principles are unusually testable — Tufte literally defined ratios and formulas (data-ink ratio, lie factor) and Few enumerated 13 named dashboard mistakes and 9+ numbered color rules. Backed by Cleveland & McGill's experimental hierarchy of graphical perception, this school converts "make it clean" into computable checks for any data-heavy UI.

## Philosophy

The data is the interface. Every pixel on a chart is either **data-ink** — "the non-erasable core of a graphic, the non-redundant ink arranged in response to variation in the numbers represented" — or it is overhead. Tufte's central move is an *erase test*: for every element, ask what would be lost if it were deleted. If the answer is "nothing," it is chartjunk — "ink that does not tell the viewer anything new" — and it goes. This is not minimalism for taste's sake; it is a theory of attention. The reader has a fixed perceptual budget, and every gradient, border, 3D bevel, and dark gridline spends it on nothing. The positive corollary is *density*: because clean graphics are cheap to read, you can show far more data than people assume — small multiples repeating one chart form across many slices, sparklines shrunk to word size inside sentences and tables. Shrink the frame, multiply the panels, keep the resolution.

Integrity is quantifiable. The visual size of an effect must be proportional to the numeric size of the effect — Tufte's lie factor (size of effect in graphic ÷ size of effect in data) should be 1.0, and anything outside 0.95–1.05 is distortion. Meanwhile, encodings are not interchangeable: Cleveland & McGill showed experimentally that people decode position along a common scale most accurately, then length, then angle/slope, then area, then volume and color saturation. This is why this school prefers bar and dot charts to pies and bubbles — it is not aesthetic prejudice, it is measured error rates (position judgments were roughly 1.4–2.5× more accurate than length and ~2× more accurate than angle).

Few extends the theory to the operational reality of dashboards: "a visual display of the most important information needed to achieve one or more objectives, consolidated and arranged on a single screen so the information can be monitored at a glance." A dashboard is a monitoring instrument, not a report — so everything must fit one screen, every number must carry context (versus target, versus prior period), precision is rounded to what a glance can use, color is a scarce signal reserved for meaning (soft muted colors for data, gray for everything that is not data, bright saturated color only for "look here"), and variety for its own sake is a defect: the same kind of data gets the same kind of display everywhere. The school knows its critics — Bateman et al.'s "Useful Junk?" study found embellished Holmes-style charts no worse for comprehension and more memorable weeks later — and the canon's answer is scope: for persuasive one-off graphics, memorability may justify decoration; for dashboards and data-dense UI read repeatedly under time pressure, efficiency wins and the erase test stands.

## Operational rules

| Rule | Category | Check | Threshold | Severity | Source |
|---|---|---|---|---|---|
| Erase test: every non-data element (border, background fill, shadow, icon, decoration) must change meaning when removed; remove any that do not | content-information | vision | element-by-element: deletion loses information, or element is deleted | block | Tufte, *Visual Display of Quantitative Information* (data-ink ratio) |
| Lie factor within 0.95–1.05: visual size of an effect proportional to numeric size; bar/area charts must have zero-baseline value axes | content-information | deterministic | (graphic effect % / data effect %) in [0.95, 1.05]; bar chart y-min = 0 | block | Tufte, VDQI ch. 2 (graphical integrity) |
| No 3D effects, perspective, or depth rendering on 2D data (3D bars, 3D pies, extruded surfaces for two-variable data) | content-information | deterministic | zero occluding/perspective-distorted marks when data has ≤2 quantitative dimensions | block | Tufte (lie factor); Few, mistake #7 "encoding quantitative data inaccurately" |
| Gridlines, axes, and borders must be visually lighter than data marks: thin and low-contrast, never competing with data | color | deterministic | gridline stroke ≤1px and luminance contrast vs. background ≤ 25% of data-mark contrast (e.g. #E0E0E0-or-lighter grid on white); no vertical+horizontal full grid unless values must be read off the chart | flag | Tufte "erase non-data-ink"; Few "reduce the non-data pixels, de-emphasize the rest" |
| Categorical color budget: distinct hues encoding categories per chart ≤ 7; beyond that, use small multiples or gray-plus-highlight | color | deterministic | count(distinct categorical hues) ≤ 7 | flag | Few, *Practical Rules for Using Color in Charts* (2008); Cleveland/McGill (color is the weakest encoding) |
| Never pair red and green as the only distinction between data series or statuses; any hue pair must survive a deuteranopia simulation or carry a redundant encoding (shape, label, position) | accessibility | deterministic | 0 red/green-only distinctions; colorblind-sim distinguishability or redundant channel present | block | Few, color rule #8 |
| Sequential quantitative color scales use a single hue (or closely related hues) varying in lightness — no rainbow/spectral palettes for ordered values | color | deterministic | scale hue range ≤ ~60° hue rotation with monotonic lightness ramp | flag | Few, color rule #6 |
| Data colors are soft/muted; fully saturated bright color appears only as deliberate emphasis on at most one thing per view | color | deterministic | ≥90% of data-mark area at moderate saturation (e.g. HSL S×L product in mid range); ≤1 high-saturation emphasis class per chart | flag | Few, *Practical Rules for Using Color in Charts*; *Information Dashboard Design* |
| Direct labeling over legends: label lines/areas at the mark when series count ≤ 5–7; if a legend is unavoidable, its order matches the visual order of the series | content-information | deterministic | series ≤7 → labels adjacent to marks (distance < one line-height where geometry allows); legend order = end-value order | flag | Few (formatting/layout); Datawrapper Academy defaults |
| Dashboard fits one screen: all information needed for the monitoring objective visible without scrolling, tabbing, or paging | spacing-layout | deterministic | 0 scroll required at target viewport for the KPI/monitoring layer | block | Few, mistake #1 "exceeding the boundaries of a single screen" |
| No naked numbers: every KPI/metric displays at least one comparison — target, prior period, or distribution (e.g. bullet graph, sparkline, delta) | content-information | deterministic | each metric tile has ≥1 of {target marker, % change vs. reference, trend line} | flag | Few, mistake #2 "supplying inadequate context for the data" |
| Glanceable precision: summary/KPI numbers rounded to 2–3 significant digits with unit abbreviation ($3.85M, not $3,848,305.93); full precision available on demand, not in the glance layer | content-information | deterministic | significant digits ≤3 on dashboard-level numbers | advise | Few, mistake #3 "displaying excessive detail or precision" |
| Encoding follows the perception hierarchy: primary quantitative comparisons use position or length; angle (pie), area (bubble), and color saturation only when position/length are exhausted by other variables | content-information | vision | chart's principal comparison encoded as position/length; justification recorded when using angle/area/color | flag | Cleveland & McGill (1984), *Graphical Perception* |
| Pie/donut charts only for a single part-to-whole message with ≤5 slices; any slice-to-slice magnitude comparison uses a bar chart instead | content-information | deterministic | pie ⇒ (slices ≤5 ∧ message is part-to-whole); comparisons of near-equal slices ⇒ bar | flag | Few, *Save the Pies for Dessert* (2007) |
| More than 4–5 overlapping series in one panel ("spaghetti") ⇒ split into small multiples; all panels of a small-multiple set share identical scales, aspect, and encoding | spacing-layout | deterministic | overlapping line series ≤5 per panel; multiples: identical axis min/max/ticks across panels | flag (shared-scale violation: block) | Tufte, *Envisioning Information* (small multiples); Few |
| No meaningless variety: the same data type/relationship uses the same display medium everywhere in a dashboard (don't rotate bar/pie/gauge/area for decoration) | components-affordance | vision | identical measure-types map to identical chart forms across the view | flag | Few, mistake #6 "introducing meaningless variety" |
| No radial gauges/speedometers for single measures on dashboards; use bullet graphs (bar + target marker + qualitative bands) which carry the same information in a fraction of the space | components-affordance | deterministic | 0 circular gauge widgets; single-measure-vs-target ⇒ bullet graph or equivalent linear form | flag | Few, *Information Dashboard Design* (bullet graph spec) |
| In-table/inline trends use sparklines: word-sized, axis-free line with at most min/max/last-point markers — never full-chrome mini-charts in table cells | content-information | deterministic | inline chart height ≤ line-height ×1.5; no axis lines/tick labels/legends inside cells | advise | Tufte, *Beautiful Evidence* (sparklines: "data-ink ratio = 1.0") |
| No moiré, hatching, or heavy pattern fills; no background images or gradients behind data | craft-detail | deterministic | 0 patterned fills / background imagery inside the plot area | block | Tufte, VDQI ("chartjunk: vibrations, grids, and ducks") |
| Most important information occupies the emphasis positions (top-left / upper region) and is visually largest; supporting detail is subordinated, not equal | hierarchy | vision | primary KPI group in top-left quadrant; visual weight ordering matches stated importance ordering | advise | Few, mistake #8/#9 (poor layout, failure to highlight) |

## Workflow practices

1. **Start from the monitoring question, not the data.** Few's process begins by enumerating the objectives and the specific questions the display must answer at a glance; every element is then justified against a question. A chart with no question attached is cut.
2. **Design by erasure.** The core Tufte ritual: take the default output of the tool, then iteratively delete — borders, backgrounds, redundant tick marks, legend boxes, axis lines — checking after each deletion whether information was lost. Ship the version one step before information loss.
3. **The redesign critique.** Both Tufte (in books and his famous one-day course) and Few (in Perceptual Edge blog critiques of vendor dashboards) work by taking a published graphic, itemizing each defect against named principles, and publishing a before/after redesign. Reviews in this school are itemized defect lists against the rulebook, not vibes.
4. **Compute the integrity numbers.** For any chart where an effect is claimed, calculate the lie factor (graphic effect ÷ data effect) and check axis baselines before arguing about anything aesthetic.
5. **The glance test.** A dashboard is validated by timed exposure: can a user extract the state of every key measure in seconds, without scrolling or clicking? If deviation-from-target can't be read at a glance, the display medium is wrong (Few's motivation for the bullet graph).
6. **Prototype at final size.** Tufte's shrink principle: design graphics large, then shrink them to their real display size (sparkline-scale if needed) and verify they still read. A chart that only works at 2× its shipped size fails.
7. **Same-form discipline.** Before adding a new chart type to a dashboard, check whether an existing form already displays that data type; introduce a new form only for a new type of relationship.
8. **Scope-check the minimalism.** When decoration is proposed for memorability (the Bateman "Useful Junk?" argument), classify the artifact: one-off persuasive/infographic → decoration may be admissible; repeated-use monitoring display → erase test applies in full.

## Anti-patterns (reject on sight)

- 3D pie charts, exploded pies, donut charts used for magnitude comparison of similar slices.
- Radial gauges and speedometer widgets — Few's canonical example of wasted pixels; replace with bullet graphs.
- Truncated bar-chart axes (bars starting above zero) or dual-scaled visuals where the picture overstates the numbers (lie factor > 1.05).
- Dark, heavy, or full-mesh gridlines that are as prominent as (or more than) the data; boxed borders around every panel.
- Rainbow/spectral palettes for sequential data; red+green as the sole status distinction.
- Background gradients, images, skeuomorphic "dashboard chrome" (brushed metal, glass reflections), drop shadows on bars.
- Legends floating far from the data when direct labels would fit; legend order contradicting visual order.
- KPI tiles showing a single naked number with no target, trend, or prior-period context.
- Eight-decimal precision on glance-level numbers ($3,848,305.9286).
- Scrolling dashboards where key measures live below the fold.
- One dashboard using bars, pies, gauges, area charts, and treemaps for the same kind of measure — variety as decoration.
- Cross-hatching, moiré-inducing patterns, and redundant data labels repeating what the axis already says.

## In their words

> "Above all else show the data." — Edward Tufte, *The Visual Display of Quantitative Information*

> "Graphical excellence is that which gives to the viewer the greatest number of ideas in the shortest time with the least ink in the smallest space." — Edward Tufte, *VDQI*

> "Clutter and confusion are failures of design, not attributes of information." — Edward Tufte, *Envisioning Information*

> "Chartjunk is ink that does not tell the viewer anything new." — Edward Tufte, *VDQI*

> "The representation of numbers, as physically measured on the surface of the graphic itself, should be directly proportional to the quantities represented." — Edward Tufte, *VDQI* (graphical integrity, source of the lie factor)

> "A dashboard is a visual display of the most important information needed to achieve one or more objectives; consolidated and arranged on a single screen so the information can be monitored at a glance." — Stephen Few, *Information Dashboard Design*

> "Use color only when needed to serve a particular communication goal… Don't use color to decorate the display." — Stephen Few, *Practical Rules for Using Color in Charts*

> "Save the pies for dessert." — Stephen Few, on pie charts as "by far the least effective" display for quantitative comparison

> Position along a common scale → position on nonaligned scales → length/direction/angle → area → volume/curvature → shading/color saturation: the measured order of decoding accuracy. — Cleveland & McGill, *Graphical Perception* (1984)
