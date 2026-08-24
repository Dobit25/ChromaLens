# ChromaLens MVP architecture

This diagram is both the source and the rendered GitHub architecture graphic.
It describes the default T08/T11 MediaPipe CPU path; the deferred SCHP
placeholder is deliberately outside the executable path.

```mermaid
flowchart LR
    A[Webcam or local video<br/>OpenCV BGR] --> B[FrameSource<br/>frame ID + monotonic timestamp]
    B -->|webcam: capacity-one newest frame| C
    B -->|video: ordered frames| C[MediaPipe person-derived<br/>torso mask on CPU]
    C --> D[Gray-world correction<br/>+ lighting quality]
    D --> E[Original garment colour<br/>median or deterministic K=2]
    E --> F[11-name mapping<br/>+ colour margin]
    E --> G[Machado CVD simulation<br/>of original colour pairs]
    G --> H[Relational risk<br/>CIEDE2000 collapse]
    E --> I[Rule-based matching<br/>from original corrected colour]
    H --> J[Selective assistive recolour<br/>inside garment/risk mask]
    C --> J
    J --> K[Renderer on a frame copy<br/>outline, tags, separate confidence fields]
    F --> K
    I --> K
    K --> L[OpenCV display or headless summary]
    B -. immutable original frame .-> K
    M[User controls<br/>profile, severity, recolour, view] --> G
    M --> J
    M --> K
    B -. read-return timestamp .-> N[Bounded latency/RSS metrics]
    K -. render-complete timestamp .-> N
    L -. GUI-submit timestamp .-> N
```

## Safety and evidence boundaries

- The original BGR frame is retained; analytical modules do not mutate it.
- CVD profile and severity are user settings, never a diagnosis.
- Simulation estimates relational risk. It is not the assistive recoloured
  output.
- Mask confidence, colour margin, lighting quality, and risk are distinct
  values; none is presented as a calibrated probability.
- `source_read_to_render_ms` and GUI-only
  `source_read_to_display_submit_ms` are software timing. Sensor-to-photon
  latency is not measured.
- No cloud, account, database, upload, or continuously growing frame queue is
  in the MVP runtime.

The detailed typed contracts are in `src/chromalens/contracts.py`; composition
is in `src/chromalens/pipeline.py`; the frozen evaluation definitions are in
`evaluation/protocol.md`.
