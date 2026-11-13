# CLAUDE.md

VoiceLoop: a full-duplex voice agent built from open-weight models (cascaded baseline first, then
a speech-in LLM, learned turn-taking, RL, memory). Read these before changing anything:
[docs/PLAN.md](docs/PLAN.md) (how each step is built), [docs/STEPS.md](docs/STEPS.md) (roadmap
checklist), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/DECISIONS.md](docs/DECISIONS.md).

## Commands

Windows. Use `uv`, never bare `pip`. The shell may be PowerShell or Git Bash.

- Install: `uv sync` (core + dev) · real-time stack: `uv sync --extra realtime`
- Check the machine: `uv run voiceloop doctor`
- Tests: `uv run pytest -q`
- Lint and format: `uv run ruff check src tests` and `uv run ruff format --check src tests`
- Run both of those and the tests before saying a change is done.
- LLM server (separate process, localhost only):
  `models/llama.cpp/bin/llama-server.exe -m models/qwen/qwen2.5-1.5b-instruct-q4_k_m.gguf -ngl 99 -c 2048 --host 127.0.0.1 --port 8080`
  Check it with `GET /health`. Stop it when finished (`taskkill /F /IM llama-server.exe`).
- ffmpeg is installed by winget, and a new terminal is needed to see it on PATH.

## Hardware

HP Victus 16, GTX 1650 with 4 GB VRAM (only about 3.3 GB free), Ryzen 5 5600H, 15 GB RAM.
Inference runs here; all training runs on Kaggle (ADR-002). Training libraries (transformers,
peft, trl, GPU PyTorch) are not project dependencies.

**Benchmark only when the laptop is plugged in.** On battery the GPU memory clock drops to
810 MHz and generation is about 3x slower (ADR-008). Check `Win32_Battery` before any speed or
latency test, and record the power state with the result. Never change Windows power settings;
ask me to.

## Conventions

- `src/voiceloop/cli.py` only parses options and calls a function. No logic in the CLI layer.
- Every path comes from `voiceloop.paths`. Never build a path elsewhere.
- Keep logic apart from hardware: parsing, state machines and metrics take plain values and are
  tested without a GPU or microphone (see how `doctor.py` splits parsing from running
  `nvidia-smi`). Model wrappers stay thin.
- Production structure, plain code: package, one CLI, tests, CI, but readable loops and simple
  functions. No clever one-liners.
- Tests never need the network, a GPU or a microphone. CI installs only the core dependencies.
- Add a test with each feature.
- Python 3.12, line length 110 (ruff). Match the surrounding code's comment density and naming.

## Rules

- **Ask before anything paid**, and state the estimated cost.
- **Ask before any download**, stating the source, filename and size. Verify it afterwards
  (size and SHA-256 against the publisher's value) and list an archive before extracting it.
- Pin versions: an exact llama.cpp build number and a model checksum, never "latest" (ADR-005).
- Never commit audio, model weights, `.env`, `data/` or `models/`.
- Commit or push only when I ask. Never add a Co-Authored-By trailer or any Claude attribution to
  commits or pull requests.
- Do not change system settings or install system software without asking.
- Decisions go in `docs/DECISIONS.md` as a new ADR. Never rewrite an accepted one. If reality
  forces a change to the plan, add a row to its "Changes from the original plan" table.
- When a step finishes, tick `docs/STEPS.md` and note what was learned in `docs/PLAN.md`.

## How to work with me

I am learning, so teach as you go.

- Say what you are about to do, where, and why, before you do it. Name the concept behind it.
- Show real output. Verify with a command, not with "it should work".
- If a guess turns out wrong, say so and drop it.
- When something fails twice, change approach or stop and ask. Do not retry blindly.
- When I ask what you ran, list the commands.
