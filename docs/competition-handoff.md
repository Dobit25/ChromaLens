# Competition handoff

Canonical machine-readable submission copy, limits, shot timing, and claim
links are frozen in [`submission.json`](submission.json). Do not strengthen a
claim in the form or narration unless its evidence record is updated first.

## Submission-ready copy

Project name: **ChromaLens AI** (`2` words; public maximum `10`).

The English description in `submission.json` is below the public `150`-word
limit. Its count and every shot boundary are enforced by
`tests/test_t11_handoff.py`; copy it from the JSON value without editing it in
the form.

## Evidence-backed benchmark summary

These are observations on development host `LENOVO 83DV`, Intel Core
i5-13450HX, 15.78 GiB RAM, locked `mediapipe-selfie-torso/cpu`. They are not
official demo-hardware acceptance results.

| Run | Processed FPS | Read-return to render p50/p95 | Read-return to display-submit p50/p95 |
| --- | ---: | ---: | ---: |
| Webcam GUI | 19.728 | 47/78 ms | 47/78 ms |
| Webcam headless | 14.013 | 62/187 ms | `NOT_MEASURED` |
| Generated video GUI | 15.944 | 47/78 ms | 47/78 ms |
| Generated video headless | 24.169 | 47/63 ms | `NOT_MEASURED` |

Every sensor-to-photon value is `NOT_MEASURED`; no synchronized external
apparatus was used. The webcam GUI RSS continuous-growth diagnostic failed in
that run, and degraded-frame rates were recorded rather than hidden. Exact
conditions and values are in
`evaluation/results/curated/performance_responsible_ai/`.

Evaluation also records 20/20 segmentation cases with manual adequacy 9/20,
three annotated IoUs, 10/10 end-to-end contract cases, 11/11 deterministic
colour-name contract cases, and all six CVD sanity cases. The 33 physical
colour/lighting cases remain honestly `NOT_RUN`, and no physical-camera colour
accuracy is claimed.

## Claim-to-evidence rule

Each allowed submission claim and its code/result paths are enumerated under
`claims` in `submission.json`. The architecture source is
[`architecture.md`](architecture.md); evaluation scope and formulae are in
`evaluation/protocol.md`; consolidated results are in
`evaluation/results/curated/summary.md`; licenses are in
[`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

Avoid these unsupported statements:

- diagnosis, clinical benefit, guaranteed perception, or validated target-user
  benefit;
- physical-camera colour accuracy or population/demographic accuracy;
- sensor-to-photon, camera exposure-to-display, or official demo-hardware
  performance;
- semantic garment parsing, calibrated confidence, or universal fashion
  advice;
- an active SCHP, ONNX, OpenVINO, optimized, or quantized backend.

## Known limitations to disclose

- MediaPipe returns a person silhouette adapted by torso heuristics, so it can
  miss garments or include hands, objects, other people, and background.
- Gray-world correction can fail under mixed light or strongly coloured
  scenes; the physical 11-by-3 lighting set was not acquired.
- Colour names, CVD risk, recolour choice, and matching rules are explainable
  heuristics, not calibrated probabilities or universal truths.
- Target-user validation, manual ROI timing, energy use, and sensor-to-photon
  latency are not measured.
- One development-host RSS trend diagnostic failed; venue camera/display and
  official demo-hardware behavior remain to be checked.
- SCHP/OpenVINO is deferred because no complete checksum-verified checkpoint
  was acquired; MediaPipe remains the only accepted backend.

## Official requirement and owner checklist

The public SHTP-IC page was checked on 24 August 2026 and states: student age
18+, currently enrolled, maximum three team members, project name at most 10
words, description at most 150 words, two-minute video/vlog, signed consent,
and deadline 25 August 2026. The linked Google Form returned HTTP 401 during
T11, so fields or video criteria visible only inside the form are not verified.

Before submission, the repository owner must:

- [ ] sign in and compare every live form field and video criterion with the
  current official form;
- [ ] confirm all members are eligible and the final team has no more than
  three people;
- [ ] copy the exact name and description from `submission.json`;
- [ ] export/watch the final video and verify the live form's duration rule;
- [ ] obtain and retain the required signed consent outside Git;
- [ ] confirm provenance/consent/license for every final video asset, person,
  voice, logo, font, screenshot, and music track;
- [ ] run the README verification and fallback command on the laptop actually
  used at the venue, then record that hardware as demo hardware only after the
  check passes;
- [ ] submit before the displayed deadline and retain the confirmation receipt.

Official references:

- [SHTP-IC competition page](https://shtpic.org/vi/intel-vietnam-al-impact-festival-2026/)
- [SHTP announcement](https://shtp.hochiminhcity.gov.vn/intel-vietnam-ai-impact-festival-2026-be-phong-cho-the-he-tai-nang-tre-935.htm)
- [Ethical AI handbook](https://www.sustainablelivinglab.org/view/handbook/guidelines-ethicalai-intelglobalaiimpactfest-2026)

No core implementation is scheduled for 25 August. Remaining work is human
form access, consent custody, recording/export review, declared-laptop dry run,
and submission.
