# Two-minute competition demo shot list

Target finished duration: exactly `120 seconds`. Record the default SCHP-ATR
OpenVINO CPU path and keep MediaPipe ready as the explicit recovery command.
Keep claims within `docs/submission.json` and use the ignored offline fallback
video if camera or venue conditions are unreliable.

| Time | Picture/action | Spoken point and required evidence |
| --- | --- | --- |
| 0:00-0:10 | Two easily confused clothing colours, then title | State the clothing-colour problem and that ChromaLens is assistive software, not diagnosis. Do not claim completed target-user validation. |
| 0:10-0:22 | Launch command and profile/severity controls | Local laptop prototype; the user selects protan/deutan/tritan and severity. Show `python -m chromalens --webcam`. |
| 0:22-0:40 | Live `original` then `mask` view | Show current-frame semantic garment classes from SCHP-ATR. Say OpenVINO runs the verified FP32 conversion locally on Intel CPU; do not turn five-fixture conversion equivalence into a broad accuracy claim. |
| 0:40-0:58 | `diagnostic` and `original` views | Explain global Gray-world correction, extraction of original corrected garment colours, 11-name mapping, and separate lighting/mask/colour fields. |
| 0:58-1:16 | `risk` then `assistive` view | Show relational CVD risk and selective recolour. Say recolour is restricted to the mask and that simulation and assistive output are different operations. |
| 1:16-1:28 | Matching suggestions | Explain that matching uses original corrected colour, never the recoloured display value, and is transparent guidance rather than an objective fashion rule. |
| 1:28-1:41 | Mask failure screenshot beside a good case | Explain why AI localization is necessary, then show limits: SCHP can miss or confuse garment classes under pose, scale, or domain shift; MediaPipe fallback is coarser and can include hands/objects/background. |
| 1:41-1:53 | Curated T09 summary and architecture | Label the 19.73/14.01 FPS webcam figures as historical MediaPipe T09 evidence. Separately label the current 20-frame SCHP/OpenVINO observation as 0.89 FPS and p50/p95 render-complete 1195.00/1411.65 ms. State sensor-to-photon is not measured. |
| 1:53-2:00 | Final assistive view and title | State the intended impact as a prototype goal. Close with the next honest validation: target users, physical lighting, and declared demo hardware. |

## Recording procedure

1. Install and run the verification block in `README.md` before recording.
2. Generate the fallback/screenshots and verify their manifest:

   ```powershell
   conda run --name lens python scripts/t11_prepare_handoff.py
   ```

3. Prefer the webcam command. If capture, lighting, background, or venue
   reliability is poor, run:

   ```powershell
   conda run --name lens python -m chromalens --video artifacts/t11-handoff/fallback_mediapipe.avi
   ```

   The fallback visibly labels its public source and uses an explicitly
   engineered T05 red/olive sanity pair. Present it as a reproducible fallback,
   never as a physical capture or accuracy case.

   If the SCHP asset/runtime gate fails at the venue, switch explicitly rather
   than claiming SCHP output:

   ```powershell
   conda run --name lens python -m chromalens --video artifacts/t11-handoff/fallback_mediapipe.avi --backend mediapipe-selfie-torso
   ```

4. Show controls `1`-`5`, `p`, `[`, `]`, and `r`; do not open a private/raw
   artifact folder on screen.
5. Check the exported file duration using the same approved environment:

   ```powershell
   conda run --name lens python -c "import cv2,sys; c=cv2.VideoCapture(sys.argv[1]); fps=c.get(cv2.CAP_PROP_FPS); frames=c.get(cv2.CAP_PROP_FRAME_COUNT); print({'fps':fps,'frames':frames,'duration_seconds':frames/fps if fps else None}); c.release()" C:\path\to\submission-video.mp4
   ```

6. The owner watches the complete export, confirms sound/text readability,
   verifies its accepted duration in the live form, and confirms every person,
   voice, logo, music track, screenshot, and footage item has consent and
   redistribution permission.
