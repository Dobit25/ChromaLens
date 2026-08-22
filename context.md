# ChromaLens AI — Competition and Product Context

Last updated: 2026-08-16  
Document role: Product and competition source of truth

## 1. Competition context

ChromaLens AI is being prepared for the AI Changemakers — Student category of Intel® Vietnam AI Impact Festival 2026.

Officially published information:

- Organizers/partners: National Innovation Center (NIC), Saigon Hi-Tech Park Management Board (SHTP), Saigon Hi-Tech Park Incubation Center (SHTP-IC), and Intel Vietnam.
- Theme: “Enriching Lives with AI Innovation” / “Làm phong phú cuộc sống thông qua đổi mới sáng tạo với AI”.
- Student category: participants aged 18 or older who are currently enrolled in a university, college, pre-university program, or equivalent.
- Team size: individual or team of no more than three students.
- Submission deadline: 25 August 2026.
- Required entry information includes:
  - Project/solution name of no more than 10 words.
  - Project/solution description of no more than 150 words.
  - A two-minute video/vlog following the form's video criteria.
  - Registration information and required signed consent.
- National recognition: the three most outstanding solutions in each age category are recognized as national winners.
- The highest-ranked team in each category may have the opportunity to represent Vietnam at Intel® AI Global Impact Festival 2026.
- Published award: VND 13,000,000 and a certificate for each member of a winning team, subject to program terms.

Official links:

- [Competition page — SHTP-IC](https://shtpic.org/vi/intel-vietnam-al-impact-festival-2026/)
- [Competition announcement — Saigon Hi-Tech Park](https://shtp.hochiminhcity.gov.vn/intel-vietnam-ai-impact-festival-2026-be-phong-cho-the-he-tai-nang-tre-935.htm)
- [Official evaluation rubric](https://drive.google.com/file/d/1gCYKVKU2nWTmMZ6mSAGkanWC8js962j1/view?usp=sharing)
- [Intel 2026 ethical and responsible AI guidelines](https://www.sustainablelivinglab.org/view/handbook/guidelines-ethicalai-intelglobalaiimpactfest-2026)

The Google registration form may impose additional video or consent requirements. The team must verify the live form before submission and must not assume this document replaces it.

## 2. Team and operating constraints

- Team: three final-year university students.
- Current plan date: 16 August 2026.
- Submission deadline: 25 August 2026.
- Available implementation window: approximately nine calendar days, with 25 August reserved for final submission rather than core development.
- Skill constraint: several computer-vision and color-science components are new to the team.
- Desired outcome: a strong, credible national-level entry, with architecture and evidence that can be extended for the global stage.
- MVP demo target: one declared Intel laptop using a webcam or local video, with local/offline inference.

These constraints make a stable vertical slice more valuable than a wide but unreliable feature set.

## 3. Project one-sentence definition

ChromaLens AI is a personalized, real-time color-vision assistance system that uses AI garment parsing and explainable color science to identify clothing colors, detect CVD-confusing color relationships, selectively recolor risky regions, and add non-color cues such as outlines, labels, and confidence information.

## 4. Problem statement

People with color-vision deficiency may see distinct colors as perceptually similar, making everyday clothing tasks harder: identifying a garment's color, distinguishing patterns, comparing a top with trousers, and selecting combinations confidently. Camera color is also affected by illuminant color, exposure, shadows, and sensor processing, so naïve RGB lookup or a fixed “red-to-purple” rule is not reliable.

The project must demonstrate the existence and relevance of this problem using cited research and/or user evidence in the final submission. Code alone is not evidence of user need.

## 5. Target users

Primary user:

- A person who already knows or chooses a CVD profile: protan, deutan, or tritan.
- Wants to inspect clothes naturally using a camera rather than clicking individual pixels.
- Needs both an assistive view and explicit information about the estimated original color.
- May use a general-purpose laptop with intermittent or no network connection.

Secondary users/stakeholders:

- Family or friends helping with clothing decisions.
- Accessibility researchers and educators.
- Clothing retailers or e-commerce platforms as a possible future integration path.

The MVP is an assistive prototype, not a medical diagnosis tool and not a replacement for professional vision assessment.

## 6. Core user journey

1. User opens the local application.
2. User selects `protan`, `deutan`, or `tritan` and adjusts severity.
3. User points the webcam at a person or garment and moves naturally.
4. The system segments the garment and maintains a sufficiently stable region through the video.
5. The system estimates lighting quality and corrects the frame used for color measurement.
6. It extracts dominant original garment colors and assigns basic color names.
7. It simulates the selected CVD profile and compares relevant colors to find confusion risk.
8. It selectively recolors only the risky garment region in the assistive view.
9. It adds a high-contrast outline, original color label, color confidence, risk level, and lighting quality.
10. It may provide an explainable clothing-color suggestion based on the original corrected color, not the assistive display color.

## 7. Functional requirements

### P0 — Mandatory for a valid MVP

| ID | Requirement |
| --- | --- |
| FR-01 | Read frames from a laptop webcam and a local video file. |
| FR-02 | Let the user select CVD profile and severity; do not infer or diagnose it. |
| FR-03 | Use an AI segmentation backend to create a garment/clothes mask and expose backend confidence when available. |
| FR-04 | Estimate/correct illumination for color measurement and report lighting quality. |
| FR-05 | Extract at least one dominant color inside an eroded valid garment mask using CIELAB. |
| FR-06 | Map the dominant original color to one of 11 basic color names and expose a color score/margin. |
| FR-07 | Simulate the selected CVD profile using a documented Machado/Brettel implementation. |
| FR-08 | Compare relevant color pairs using CIEDE2000 and produce a separate risk score/level. |
| FR-09 | Recolor only a risky garment/sub-color mask; preserve access to the original frame and original color. |
| FR-10 | Render a high-contrast double outline and a readable tag with original color, confidence, risk, and lighting quality. |
| FR-11 | Keep live processing bounded: no unbounded frame queue and no continuously increasing display delay. |
| FR-12 | Save optional debug/evaluation artifacts without uploading camera frames. |

### P1 — Competition-strengthening, after P0 vertical slice

| ID | Requirement |
| --- | --- |
| FR-13 | Distinguish upper clothes, trousers, skirt, or dress through SCHP-ATR rather than one merged clothes mask. |
| FR-14 | Extract two dominant clusters for simple multicolor garments and create a submask for each retained cluster. |
| FR-15 | Compare top-versus-bottom and garment-versus-adjacent-background color risk. |
| FR-16 | Generate rule-based CIELCH clothing suggestions from `suggestions.csv`, with a Vietnamese explanation. |
| FR-17 | Apply temporal smoothing to white-balance gains, masks, color estimates, and display transformation. |
| FR-18 | Collect p50/p95 latency, processed FPS, memory, and backend/device measurements. |
| FR-19 | Run the segmentation model through ONNX/OpenVINO when it demonstrably preserves mask quality and improves deployment on Intel hardware. |

### P2 — Explicitly outside the first MVP

- WebRTC/mobile browser delivery.
- Cloud inference, accounts, or a database.
- Multi-person tracking with ByteTrack.
- SAM 2 tap-to-select mode.
- Training a new segmentation model.
- End-to-end neural recoloring.
- E-commerce purchasing integration.
- Medical screening or diagnosis.

These are roadmap items, not current Definition of Done.

## 8. Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-01 | The default demo operates locally/offline after dependencies and weights are installed. |
| NFR-02 | Camera frames are not stored or transmitted by default. Saving requires an explicit debug/evaluation option. |
| NFR-03 | Minimum demonstration floor: at least 5 processed FPS and p50 capture-to-display latency at or below 350 ms on the declared demo laptop, or an explicit limitation report if the AI backend prevents this. Target: at least 10 FPS and p50 at or below 200 ms. |
| NFR-04 | A two-minute live run must not show continuously growing latency or unbounded memory use. |
| NFR-05 | Outside-mask pixel differences caused by recoloring should be zero except for deliberate outline/tag overlays. |
| NFR-06 | All key thresholds and profile settings are configurable and recorded in evaluation output. |
| NFR-07 | The app must fail visibly and recoverably when the camera/model is unavailable; it must not silently return fabricated output. |
| NFR-08 | Model, dataset, algorithm, and external code licenses/credits must be documented. |

Performance thresholds are MVP engineering targets, not claims from the competition organizer. They must be reported together with hardware, resolution, backend, and test conditions.

## 9. Responsible-AI requirements

The official 2026 guidance covers environmental impact, equity and inclusion, privacy, transparency/explainability, security/safety/reliability, human oversight, human rights, data integrity/bias mitigation, and plagiarism/credit.

Project-specific implications:

- Inclusion: validate on varied skin tones, garment colors, patterns, body shapes, and lighting; report gaps rather than claiming universal performance.
- Privacy: local inference by default; no hidden frame upload; explicit saving behavior.
- Explainability: distinguish measured original color, CVD simulation, risk heuristic, display recolor, and all confidence components.
- Human oversight: profile/severity is user-controlled and the user can disable assistive recolor.
- Reliability: warn when lighting or mask quality is poor.
- Data integrity: record source, license, and limitations of every dataset/weight.
- Environmental impact: avoid training from scratch; measure and report the hardware/backend used; prefer efficient inference after correctness.
- Attribution: credit SCHP/ATR, MediaPipe, DaltonLens, color-naming resources, OpenCV, ONNX/OpenVINO, papers, and any reused code/data.

## 10. Product success definition

The MVP succeeds when a judge can observe, in one short demonstration:

- Natural camera input.
- AI-based garment localization.
- Original-color recognition under declared lighting conditions.
- Personalization by CVD profile/severity.
- An explainable risk comparison rather than unconditional recoloring.
- Selective recoloring plus a non-color cue.
- Separate confidence/risk/lighting information.
- Local deployment evidence and honest limitations.

The project does not need perfect medical or photometric accuracy to be a credible competition prototype. It does need a clear problem, a working and reproducible implementation, evidence, ethical treatment, and a defensible explanation of where AI is essential.
