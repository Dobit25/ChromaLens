# Intel® Vietnam AI Impact Festival 2026 — Rubric and Evidence Map

Last updated: 2026-08-16  
Document role: Official scoring reference plus project evidence plan

## 1. Use of this document

The official AI Changemakers rubric totals 50 announced points across three metrics:

| Metric | Announced points |
| --- | ---: |
| 01. Enriching Lives — Impact & Inclusion | 15 |
| 02. AI Innovation — Application & Implementation | 20 |
| 03. Technical Knowledge and Skills | 15 |
| Total | 50 |

Official source: [Evaluation Rubrics for VAIIF26.pdf](https://drive.google.com/file/d/1gCYKVKU2nWTmMZ6mSAGkanWC8js962j1/view?usp=sharing)

The “ChromaLens evidence” columns below are internal strategy, not text from the organizer. Coding decisions must create observable evidence for the rubric without adding features that weaken the MVP.

## 2. Important ambiguities in the official PDF

The PDF contains internal point inconsistencies. Preserve these facts and do not silently rewrite the official rubric:

1. Metric 02 is labeled 20 points, but its visible row maxima do not clearly sum to 20. The GTM/deployment row describes `0`, `1`, and `2` levels while its points-range column says `0–1`.
2. Metric 03 is labeled 15 points. Its “Usage of emerged AI” description includes a `4-point` level, while its points-range column says `0–3`. The other visible maxima sum to 11, so a 4-point maximum would make the announced total 15.
3. “Can the solution work without AI as well? Is it a force-fit?” is grammatically ambiguous because the PDF shows `0 = no, 1 = yes`, although “yes” could imply the AI is force-fit.

Internal action:

- Use the organizer's announced metric totals in planning.
- Do not fabricate the missing interpretation.
- Frame the submission so that AI necessity, GTM/deployment, and technical sophistication are unambiguous regardless of the scoring typo.
- If possible, request clarification from the organizer before final submission.

## 3. Metric 01 — Enriching Lives: Impact & Inclusion

### 3.1 Significance of the problem statement

| Official criterion | Official range | ChromaLens evidence required |
| --- | ---: | --- |
| Is the problem clearly defined: what it is, where it exists, its relevance, and proposed solution? | 0–2 | A concise problem statement covering CVD clothing-color confusion, camera/lighting difficulty, target context, and the complete assistive pipeline. |
| Is evidence of the problem's existence given through citations or references? | 0–1 | Cited peer-reviewed research, prevalence/impact source, related solutions, and preferably a small interview/usability record from target users or accessibility stakeholders. |

Repository evidence:

- `context.md` problem statement.
- `docs/research.md` or final report references, to be created during submission preparation.
- An anonymized user-needs/testing summary if participants are available.

### 3.2 Diversity and inclusion

| Official criterion | Official range | ChromaLens evidence required |
| --- | ---: | --- |
| Is the target audience well defined: who they are and how they are affected? | 0–2 | Primary/secondary users, chosen use case, profile selection, limitations, and non-diagnostic positioning. |
| Does the solution provide equivalent UX for all? | 0–1 | Recolor plus non-color outline/text; readable high-contrast UI; original information remains available; keyboard-accessible controls where practical. Do not claim universal equivalence without testing. |
| Does it remove tech barriers for people with disabilities? | 0–1 | Directly demonstrate identification, risk detection, recolor, labels, and outlines for CVD-related barriers. |
| Is it financially viable for the target audience? | 0–1 | Local software on a general-purpose laptop; use open-source dependencies; document cost and future mobile pathway. |
| Does it work offline/low-bandwidth? | 0–1 | Live demo after disconnecting network; no cloud runtime dependency. |
| Does it support multilingual/multi-modal interaction? | 0–1 | Vietnamese labels plus visual recolor/outline/text. English labels can be a configuration/translation layer; do not add speech unless stable and useful. |

Repository evidence:

- Local run instructions and dependency list.
- UI screenshots/video showing profile selection, Vietnamese tag, double outline, and offline operation.
- `LICENSES.md`/attribution and a simple cost statement prepared later.

### 3.3 Impact on society and human lives

| Official criterion | Official range | ChromaLens evidence required |
| --- | ---: | --- |
| Is the impact on society clearly defined? | 0–1 | Explain improved autonomy/confidence in identifying and coordinating clothing; define what the MVP measures and what future impact should be studied. |
| Does the AI component create impact not achievable through traditional software alone? | 0–1 | Demonstrate AI human parsing under natural motion/backgrounds. Explain that fixed RGB thresholds cannot reliably isolate garments in unconstrained video. Keep deterministic color science where it is more explainable. |
| Is the innovation properly mapped to SDGs? | 0–1 | Map primary contribution to SDG 10 (Reduced Inequalities); optionally SDG 3 only with careful non-medical wording and SDG 9 for accessible innovation. Explain the causal link, not only display logos. |
| Are environmental implications considered? | 0–1 | No training from scratch, local efficient inference, declared hardware, latency/energy proxy, and optimization evidence. |
| Is innovation sustenance through sustainable pathways emphasized? | 0–1 | Modular architecture, open standards, cost pathway, maintenance/data roadmap, user validation plan, and future mobile/retail integration without claiming it is already built. |

## 4. Metric 02 — AI Innovation: Application & Implementation

### 4.1 Requirement and innovative use of AI

| Official criterion | Official range | ChromaLens evidence required |
| --- | ---: | --- |
| Can the solution work without AI as well? Is it a force-fit? | 0–1, wording ambiguous | Provide an ablation/baseline explanation: manual pixel selection or fixed thresholding fails to locate garments robustly in free-moving video; AI segmentation is necessary for the proposed UX. Do not claim every module needs AI. |
| Is AI primary or an accessory/additional tool? | 0–2 | AI garment understanding is the perception layer that enables automatic per-pixel assistance; color science then produces explainable decisions. |
| Idea classification: no AI, generic, adaptation, or new/original | 0–3 | Position as a defensible synthesis: natural video garment parsing + lighting correction + personalized CVD relational risk + selective temporal recolor + explicit non-color cues and matching. Acknowledge all prior work. |
| Did participants demonstrate AI knowledge and skills used for development? | 0–2 | Architecture diagram, preprocessing/inference/postprocessing explanation, model output inspection, confidence handling, fallback, benchmark, and team-authored code. |
| Is it clearly demonstrated how data is obtained and analyzed? | 0–1 | Model/dataset provenance, evaluation-set creation, consent/privacy, color test conditions, metrics, and saved results. |
| Is data selection, analysis, and usage explained or justified? | 0–1 | Explain why ATR/SCHP or MediaPipe is used, why RefCOCO is not core training data, how color samples are controlled, and limitations of demographic/lighting coverage. |

### 4.2 Complexity and responsible use of AI

| Official criterion | Official range | ChromaLens evidence required |
| --- | ---: | --- |
| Are ethical concerns addressed? | 0–1 | Responsible-AI section covering assistive/non-diagnostic use, failure warnings, misuse, inclusion, attribution, and environmental considerations. |
| Are data protection and privacy addressed? | 0–1 | Local inference, no default frame storage/upload, explicit debug-save switch, no identity recognition. |
| Are bias-mitigation steps discussed/taken? | 0–1 | Test matrix across lighting, skin tones, clothing types, patterns, and body presentations; report failures and planned expansion. |
| Is environmental impact considered? | 0–1 | Reuse pretrained models, measure backend/device, avoid unnecessary models, use OpenVINO only after validating correctness. |

### 4.3 Readiness

| Official criterion | Official range | ChromaLens evidence required |
| --- | ---: | --- |
| Working prototype demonstrated | 0–1 | Live or recorded end-to-end webcam demo, not slides or isolated notebooks. |
| Deployment status | 0–2 | At minimum test on the declared laptop under controlled conditions. Stretch: public/open-source repository or downloadable demo if rules and licenses allow. |
| GTM/deployment strategy | PDF description shows 0/1/2; range column 0–1 | Provide a realistic staged path: research MVP → user validation → efficient laptop/mobile inference → opt-in retail/e-commerce integration. A demonstrated local package is stronger than an unsupported market claim. |

## 5. Metric 03 — Technical Knowledge and Skills

| Official criterion | Official range as printed | ChromaLens evidence required |
| --- | ---: | --- |
| Is the tech stack explained? | 0–2 | `knowledge_plan_discussion.md`, architecture/data contracts, README, model card, and an explanation of how modules exchange masks, colors, scores, and frames. |
| What hardware is used? | 0–3 | Declare exact laptop CPU/GPU/NPU/RAM/camera; show OpenVINO Intel device/backend selection and benchmark. Do not claim AI-optimized hardware if not used. |
| What software is used? | 0–3 | Multiple team-authored Python modules integrating OpenCV, an AI segmenter, DaltonLens/color science, tests, data files, and optionally ONNX/OpenVINO. |
| Complexity of UI | 0–3 | A purpose-built interface/overlay with profile controls, debug modes, assistive display, confidence/risk/lighting separation, and readable bilingual-ready labels. |
| Usage of emerged AI | Range says 0–3; description includes 4 | Do not add GenAI/RAG/agents solely for points. Emphasize current vision segmentation, multimodal camera interaction, on-device inference, and the novel integrated assistance pipeline. If organizers interpret “multimodal AI” narrowly, camera plus text UI may not qualify as a multimodal foundation model; describe it accurately. |

## 6. High-score evidence checklist

Coding is not enough. Before submission, the team should possess:

- [ ] A reproducible live demo and sample-video mode.
- [ ] Architecture diagram and per-module explanation.
- [ ] Exact hardware/software/backend information.
- [ ] AI necessity comparison or ablation against a non-AI/manual baseline.
- [ ] Evaluation matrix and measured results, including failures.
- [ ] Offline demo evidence.
- [ ] Privacy and responsible-AI statement.
- [ ] Model/data/code licenses and credits.
- [ ] At least one form of user/stakeholder feedback if safely obtainable.
- [ ] Two-minute video that shows the problem, user, live solution, evidence, impact, and limitations.
- [ ] Name at most 10 words and description at most 150 words.
- [ ] Signed consent and all form fields verified against the live registration form.

## 7. Scoring strategy for engineering decisions

Use this order when choosing work:

1. Make the prototype visibly work end to end.
2. Produce evidence for impact, AI necessity, data use, privacy, and limitations.
3. Make the system reproducible and measurable.
4. Improve garment semantics, temporal stability, and Intel deployment.
5. Add only those UI or matching features that can be demonstrated reliably.

Adding a fashionable AI technology that does not improve the target user's outcome is likely to weaken the force-fit, readiness, explainability, and reliability story.
