# ChromaLens AI

ChromaLens AI is a local, explainable color-vision assistance prototype for
clothing. The current repository state is T00: package bootstrap and stable
cross-module contracts. Camera and video execution begin in T01.

The MVP is assistive software, not a medical diagnosis tool. The user selects
their CVD profile and severity.

## Requirements

- Windows development environment used by the project.
- Conda.
- The committed Conda and pip lock files under `requirements/`.

Do not install project dependencies into the Anaconda base environment.

## Locked collaboration environment

All contributors and coding agents must create `lens` from the committed
Windows/Python 3.10 baseline. Do not use `pip freeze` as a replacement for the
lock file and do not install unrecorded packages manually.

From the repository root:

```powershell
conda create --name lens --file requirements/conda-win-64.lock
conda run --name lens python -m pip install --require-hashes --requirement requirements/py310-win64.lock
conda run --name lens python -m pip install --no-build-isolation --no-deps --editable ".[dev]"
```

The explicit Conda lock pins every bootstrap artifact, build, URL, and MD5,
including Python 3.10.20 and pip 26.1.2. `environment.yml` is the concise,
human-readable declaration of the supported interpreter and bootstrap tools.
The hashed pip lock pins every currently approved base/development Python
package and transitive dependency. The final command installs only the local
ChromaLens package; dependency resolution is deliberately disabled.

If `lens` already exists and matches the Conda lock, re-run the two pip
commands to apply the committed lock. Recreate the environment if Python,
pip, or any Conda package build differs from the lock.

Verify the environment:

```powershell
conda run --name lens python --version
conda run --name lens python -m pip check
conda run --name lens python -m chromalens --help
conda run --name lens python -m pytest -q
```

## Dependency change policy

`pyproject.toml` is the source of direct dependency intent. The lock file is
the source of the exact resolved install. Both must change in the same owner-
reviewed dependency commit.

Only the integration owner regenerates the shared lock. After an approved
direct dependency change:

```powershell
conda run --name lens python -m pip install --editable ".[lock]"
conda run --name lens pip-compile pyproject.toml --extra dev --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/py310-win64.lock
conda run --name lens pip-compile pyproject.toml --extra lock --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/lock-tools-py310-win64.lock
conda list --explicit --md5 --name lens
```

Review the final command's output and save it as
`requirements/conda-win-64.lock`; never overwrite the committed lock without
reviewing every artifact URL, build, and checksum. Then repeat the locked
install and all verification commands. Task branches
must not independently choose MediaPipe, DaltonLens, PyTorch, SCHP, ONNX, or
OpenVINO versions. Those dependencies are added to explicit optional groups
and the integration lock only when their owning task reaches its dependency
gate.

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
