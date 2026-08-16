# ChromaLens AI

ChromaLens AI is a local, explainable color-vision assistance prototype for
clothing. The current repository state is T00: package bootstrap and stable
cross-module contracts. Camera and video execution begin in T01.

The MVP is assistive software, not a medical diagnosis tool. The user selects
their CVD profile and severity.

## Requirements

- Windows development environment used by the project.
- Conda.
- Python 3.10 in the project-specific `lens` environment.

Do not install project dependencies into the Anaconda base environment.

## Fresh environment and editable install

From the repository root, create the isolated environment and install the
exact pinned base/development dependencies:

```powershell
conda create --name lens python=3.10 -y
conda run --name lens python -m pip install --editable ".[dev]"
```

If the `lens` environment already exists, run only the editable-install
command. The package requires Python 3.10 and rejects other minor versions.

## T00 verification

These commands require no webcam, network access at runtime, model weights, or
special inference hardware:

```powershell
conda run --name lens python -m chromalens --help
conda run --name lens python -m pytest -q
```

The console entry point is equivalent:

```powershell
conda run --name lens chromalens --help
```

## Current limitations

- Webcam and local-video modes are intentionally deferred to T01.
- MediaPipe and SCHP classes are T00 contract placeholders. Calling inference
  raises a backend-specific exception; no placeholder returns a fabricated
  mask.
- Model weights, datasets, generated artifacts, and private footage are not
  included.

## License

ChromaLens AI is licensed under the Apache License 2.0. Third-party model,
dataset, algorithm, and code attribution will be documented as each component
is integrated.
