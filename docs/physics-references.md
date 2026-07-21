# Physics References — Stopping Distance, TTC, Distance Estimation

Backs the claims in `CLAUDE.md` and the formulas in `src/distance.py`. Full
citations are in `docs/references.bib`. Written up because the two data
placeholders that were in `references.bib` (`icbc2026wildlife`'s "24 fatal"
note and `stoppingdistance2022`, a journal-less "PMC, 2022" stub) didn't hold
up when checked against the actual sources — see corrections below.

---

## 1. Stopping distance (backs CLAUDE.md section 2's "71 metres")

**Formula** (`wikipedia2026braking`):

```
D_total = D_reaction + D_braking
D_reaction = v * t_reaction
D_braking  = v^2 / (2 * mu * g)
```

where `v` = speed (m/s), `t_reaction` = driver reaction time (s), `mu` =
tire-road friction coefficient, `g` = 9.81 m/s^2.

**At 100 km/h (v = 27.78 m/s), dry asphalt:**

| t_reaction | mu | D_reaction | D_braking | D_total |
|---|---|---|---|---|
| 1.5 s (textbook baseline) | 0.7 | 41.7 m | 56.2 m | **97.9 m** |
| 1.5 s | 0.8 (good tires) | 41.7 m | 49.2 m | **90.8 m** |
| 1.0 s (alert driver) | 0.9 (ABS + good tires) | 27.8 m | 43.7 m | **71.5 m** |

**The "71 m" figure in CLAUDE.md matches the third row** — a 1.0s reaction
time and mu=0.9 (modern ABS car, good dry-asphalt grip). That's a real,
defensible combination, not made up, but it's the *optimistic* end of the
range: an inattentive driver (1.5s+ reaction) or an older/worn-tire vehicle
(mu=0.7) is closer to 90-98 m. A real-world measured figure
(`martinreillymotors.com`) puts a typical 100-0 km/h stop at 77.7 m,
consistent with something between the second and third rows.

**Recommendation:** state the assumption explicitly wherever "71 m" is used
in the report ("...71 m assuming 1.0 s reaction time and mu=0.9..."), and
consider citing the more conservative 90-98 m range as the worst-case the
system needs to beat, since that's the safety-relevant bound.

---

## 2. Time-to-contact / tau (backs `src/distance.py`'s `ttc_distance_m()`)

**Source:** Lee, D.N. (1976), *A Theory of Visual Control of Braking Based
on Information about Time-to-Collision*, Perception 5(4), 437-459.
DOI: 10.1068/p050437 (`lee1976tau`).

Tau is the inverse of the relative rate of expansion of an object's image:
for a rigid object closing at constant speed, time-to-collision can be
recovered purely from how fast its projected size grows, with no need to
know its real size, distance, or velocity independently.

**Discrete form used in the code:**

```
tau = dt / (1 - h_prev / h_curr)
```

This is the standard two-frame approximation of Lee's continuous tau: if the
object's bounding-box height grew from `h_prev` to `h_curr` over `dt`
seconds, and growth continues at that rate, `tau` seconds remain until
contact. `src/distance.py:37-56` implements this correctly, including the
"not approaching" guard (`height_ratio >= 1.0` -> return `None`, matching
the approach-vector filter's shrinking-bbox rule in CLAUDE.md section 4).

No correction needed here — implementation matches the cited theory.

---

## 3. Thin-lens / pinhole distance (backs `src/distance.py`'s `thin_lens_distance_m()`)

**Source:** Hartley & Zisserman, *Multiple View Geometry in Computer
Vision*, 2nd ed., Cambridge University Press, 2004 (`hartley2004multiview`)
— standard pinhole camera model.

```
H_sensor / f = H_real / D   =>   D = (H_real * f) / P
```

where `P` is the observed object height in pixels and `f` is focal length
in pixels (from checkerboard calibration, per `docs/interface_contract.md`
section 2 — not done yet, hence `focal_length_px` being a required argument
rather than a constant in the code).

`src/distance.py:15-22` implements `D = (shoulder_height_m * focal_length_px)
/ bbox_height_px` — matches the formula exactly. No correction needed.

---

## 4. ICBC wildlife collision statistics (backs CLAUDE.md section 2)

**Source:** ICBC newsroom, *ICBC Urges Drivers to Watch for Wildlife as
Spring Brings More Animals onto B.C. Roads* (2026-04-29)
(`icbc2026wildlife`): https://icbc.com/about-icbc/newsroom/2026-04-29-wildlife-collisions

Verified correct: **12,519 wildlife-vehicle collisions in BC in 2024**, a
high vs. the decade average of 11,600/yr, with deer accounting for 75%
(9,400+ strikes).

**Needs correcting: the "24 fatal" figure is a 2015-2024 cumulative total**
(alongside "112,000+ total crashes" over that decade) — the source does not
break out a 2024-specific fatality count. CLAUDE.md section 2 currently
reads "...a record, with 24 fatal," which implies 24 fatalities in 2024
alone. Recommend rewording to something like: "24 fatal collisions across
2015-2024" (decade context) rather than attaching it to the 2024 figure.
