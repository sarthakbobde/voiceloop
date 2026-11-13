# Architecture

How VoiceLoop is put together: the processes, the data flow, the code layout, and the rules that
keep it testable. The *why* behind each choice is in [DECISIONS.md](DECISIONS.md); the *how we
build it* is in [PLAN.md](PLAN.md).

**Status markers used below:** ✅ exists in the repo · 🔧 installed on the machine, no code yet ·
📝 planned only.

---

## 1. The system in one picture

```
                       ┌────────────────────────── voiceloop (Python process) ──────────────────────────┐
 microphone ─► audio ─►│ ring buffer ─► VAD ─► ASR ─► turn manager ─► LLM client ─► sentence ─► TTS ─► │─► speaker
   (sounddevice)       │                 │             ▲      │            │         splitter           │
                       │                 └─speech_start┘      └─ barge-in: stop LLM + clear playback ◄──┤
                       │                                                                                │
                       │   every stage writes timestamped events ─► event log ─► eval reports          │
                       └──────────────────────────────────────────────┬─────────────────────────────────┘
                                                                      │ HTTP, 127.0.0.1:8080 (OpenAI-compatible)
                                                              ┌───────▼────────┐
                                                              │  llama-server  │  separate process
                                                              │  Qwen2.5-1.5B  │  on the GPU
                                                              │  Q4_K_M (GGUF) │
                                                              └────────────────┘
```

Two processes, not one (ADR-004): the Python agent, and the prebuilt llama.cpp server that holds
the language model. The agent talks to the server with the `openai` client.

---

## 2. Components and status

| Component | What it does | Model / library | Runs on | Status |
|---|---|---|---|---|
| Audio in | Copies microphone frames into a queue; a file source replays `.wav` files for tests | `sounddevice` | CPU | 📝 (library 🔧) |
| VAD | Says whether the current audio frame is speech | Silero VAD (`silero-vad`) | CPU | 📝 (library 🔧) |
| ASR | Turns speech segments into text, with partial results | faster-whisper small, int8 | GPU | 🔧 files verified; runs on the GPU at 11.6× real time (needs ADR-010) |
| Turn manager | State machine deciding who has the floor | pure Python | CPU | 📝 |
| LLM | Generates the reply, streamed | Qwen2.5-1.5B-Instruct Q4_K_M in `llama-server` | GPU | 🔧 files downloaded and verified, server runs |
| Sentence splitter | Cuts the token stream into sentences for TTS | pure Python | CPU | 📝 |
| TTS | Speech from text, sentence by sentence | Kokoro-82M int8 via `kokoro-onnx` (Piper as fallback) | CPU | 🔧 installed; 0.42 real-time factor (ADR-011) |
| Audio out | Playback queue that can be cleared instantly | `sounddevice` | CPU | 📝 |
| Event log | Timestamped events from every stage | `pydantic` records written as JSON lines | disk | 📝 |
| Eval harness | Replays recordings, computes latency and turn-taking metrics | pure Python | CPU | 📝 |
| Config loader | Reads which model runs each stage and its VRAM estimate | `pydantic`, `pyyaml` | CPU | ✅ `config.py` |
| `voiceloop doctor` | Checks GPU, VRAM budget, ffmpeg, microphones | `nvidia-smi`, `sounddevice` | CPU | ✅ `doctor.py` |

---

## 3. Runtime behaviour (planned)

### Turn manager states

```
          speech_start                    silence ≥ timeout                reply ready
listening ───────────► user_speaking ───────────────────► thinking ───────────────► agent_speaking
    ▲                       ▲                                                           │
    │                       └───────────── barge-in (user speech_start) ────────────────┤
    └──────────────────────────── playback finished ◄───────────────────────────────────┘
```

- `listening`: waiting for the user.
- `user_speaking`: VAD says speech; ASR is producing partial text.
- `thinking`: the user stopped; the LLM is generating; no audio has played yet.
- `agent_speaking`: sentences are being synthesized and played.
- **Barge-in:** user speech while the agent speaks stops the LLM request and clears the playback
  queue, then returns to `user_speaking`.
- The "silence ≥ timeout" rule is the Phase 1 end-of-turn detector. Phase 3 replaces it with a
  learned model; the state machine itself does not change.

### Threads

- **Audio callback thread:** only copies frames into a queue. Nothing slow runs here.
- **Main loop:** reads frames, runs VAD, drives the turn manager.
- **Worker threads:** ASR, the LLM stream, and TTS, so a slow stage never blocks listening.

### The event log

Every stage emits a timestamped event: `speech_start`, `speech_end`, `asr_partial`, `asr_final`,
`llm_first_token`, `llm_first_sentence`, `tts_first_chunk`, `playback_start`, `barge_in`,
`playback_stop`. All latency and turn-taking metrics are computed from this log *afterwards*, so
measuring never changes the code being measured. Each log also records the machine's **power
state** (plugged in or battery), because it changes the results (ADR-008).

### Replay mode

The audio source is an interface with two implementations: the microphone, and a file that plays
a recorded `.wav` in real time. The evaluation harness, the tests and debugging use the file
source, which gives repeatable numbers and CI tests that need no microphone.

---

## 4. Code layout

### Today ✅

```
src/voiceloop/
  __init__.py   __main__.py      package marker; `python -m voiceloop` runs the CLI
  cli.py        the `voiceloop` command: parses options, calls one function (`doctor` so far)
  config.py     loads configs/models.yaml into validated Stack / StageModel objects
  doctor.py     machine checks; parsing and verdict functions take plain values so they are testable
  errors.py     UserError: a mistake the person running a command can fix
  paths.py      every file and folder, defined once
configs/models.yaml          which model runs each stage, where, and its VRAM estimate
tests/test_foundations.py    config, doctor parsing and verdicts, CLI parsing (8 tests)
.github/workflows/ci.yml     lint, format check, tests on every push
```

### Planned 📝

```
src/voiceloop/
  audio/       sources (microphone, file), playback, ring buffer
  stages/      vad.py, asr.py, llm.py, tts.py  — one thin wrapper per model, same small interface
  turn.py      the turn manager state machine (pure logic, fully unit-tested)
  events.py    event types and the event log writer
  agent.py     wires sources, stages and the turn manager together
  evals/       latency.py, turns.py, report.py — read event logs, write reports
  speechllm/   Phase 2: Whisper encoder + adapter + Qwen
  memory/      Phase 5: fact store, extraction, retrieval
```

Model wrappers stay thin so Phase 2 can replace `asr` + `llm` with one speech-in model without
touching the turn manager.

### Dependency direction

`cli` → feature packages (`audio`, `stages`, `evals`, …) → shared plumbing (`paths`, `config`,
`errors`). Shared plumbing imports nothing from the feature packages.

---

## 5. Files and folders on disk

| Path | Contents | In git? |
|---|---|---|
| `src/`, `tests/`, `configs/`, `docs/` | Code, tests, configs, documents | yes |
| `evals/reports/` | Summarised results | yes |
| `evals/runs/` | Raw event logs | no |
| `data/` | Recordings and datasets (audio) | no |
| `models/llama.cpp/bin/` | llama.cpp b12211 CUDA 12.4 binaries (1.2 GB) | no |
| `models/qwen/` | `qwen2.5-1.5b-instruct-q4_k_m.gguf` (1.04 GiB) | no |
| `models/whisper-small/` | faster-whisper small, 4 files (483.5 MB weights) | no |
| `models/kokoro/` | `kokoro-v1.0.int8.onnx` (92 MB), `voices-v1.0.bin` (28 MB), `sha256.txt` | no |
| `data/samples/` | Kokoro test audio (`kokoro_short.wav`, `kokoro_long.wav`) | no |
| `.venv/` | Python environment | no |
| `E:\hf_cache` (outside the repo) | Hugging Face model cache (`HF_HOME`) | n/a |

Audio, weights and logs never enter git (`.gitignore`); only the scripts that produce them and the
reports that summarise them do.

---

## 6. Hardware budget

Machine: HP Victus 16 — Ryzen 5 5600H (6 cores, 12 threads), 15 GB RAM, GTX 1650 with 4096 MiB
VRAM (Turing: fp16, no bf16, no tensor cores), Windows 11.

| Stage | Device | Estimated VRAM | Measured |
|---|---|---|---|
| Whisper small int8 | GPU | ~1000 MiB | **413 MiB** (after a transcription) |
| Qwen2.5-1.5B Q4_K_M + 2048 context | GPU | ~1800 MiB | **1128 MiB** (server loaded, 4 slots) |
| Silero VAD | CPU | 0 | n/a |
| Kokoro-82M int8 (ONNX) | CPU | 0 | no VRAM; 422 MiB of RAM at peak |

- **Both GPU models together use about 1567 MiB** over the desktop baseline (LLM 1154 + Whisper
  413, measured 2026-11-13). Free VRAM varies with other apps (3296 MiB with a browser open, over
  3900 with nothing), so even the worst case leaves about 1 GB of headroom (ADR-009).
- **On battery the GPU is throttled** (memory clock 810 of 6001 MHz). Benchmark plugged in
  (ADR-008).
- Qwen Q4_K_M speed, **plugged in**: generation 78 tokens/s on the GPU vs 26 on the CPU; prompt
  reading 327 vs 176 tokens/s. On battery the GPU generated at only 19.5 tokens/s.
- Streamed through the `openai` client: first complete sentence in about 0.3 s when the prompt is
  already cached, about 0.9 s on a cold first request; 3 runs of one prompt only, so this is a
  sanity check and not a latency result (see Step 05).

---

## 7. Rules that keep it maintainable

1. **No logic in the CLI layer.** `cli.py` only parses options and calls a function, so the
   function is testable without a terminal.
2. **No hard-coded paths.** Use `voiceloop.paths`; functions take paths as parameters with the
   project default, so tests can point them at a temp folder.
3. **Logic is separate from hardware.** The turn manager, sentence splitter, metrics and memory
   policies are pure functions or state machines tested in CI. Model wrappers are thin and tested
   with fakes. `doctor` already follows this: it parses `nvidia-smi` text in one function and
   runs the command in another.
4. **Measure through events, not timers scattered in code.** One event log, many reports.
5. **No network, GPU or microphone in tests.** CI runs on a plain Linux runner with only the core
   dependencies; the audio and model libraries live in the `realtime` extra (ADR-007).
6. **Pin what we download.** A llama.cpp build number and a model checksum, not "latest" (ADR-005,
   ADR-006).
7. **Every behaviour-changing choice gets an ADR**, and the original plan is never silently
   edited: changes are listed in the table at the top of DECISIONS.md.

---

## 8. How the architecture changes per phase

| Phase | What is replaced | What stays the same |
|---|---|---|
| 1. Cascaded baseline | — (builds everything above) | — |
| 2. Speech-in LLM | `asr` + `llm` become one model: frozen Whisper encoder → projector → Qwen | VAD, turn manager, TTS, event log, harness |
| 3. Learned turn-taking | The silence-timeout rule inside the turn manager | Everything else |
| 4. RL and self-improvement | The model's weights (trained on Kaggle) plus a log → relabel → retrain loop | Runtime architecture |
| 5. Persistent memory | A `memory/` store added before the LLM prompt is built | Everything else |

Each swap is judged on the same replay set and metrics (ADR-001), which is why the event log and
replay mode come first.

---

## 9. Known limits and open questions

- **Not measured yet:** localhost HTTP overhead to the LLM server; speech recognition accuracy on
  real microphone speech (only a synthetic voice was tested); how Kokoro sounds in a real
  conversation, which is judged by ear.
- **Whisper on the GPU borrows cuBLAS DLLs from the llama.cpp folder** and needs `av<19`
  (ADR-010). The `av<19` cap is applied; the DLL-path helper arrives with the ASR wrapper in
  Step 02, so until then a script must put `models/llama.cpp/bin` on `PATH` itself.
- **Echo:** the agent hearing itself through speakers will trigger false barge-ins. Headphones
  first; an echo canceller is a later improvement.
- **One-minute first server start:** probably one-time GPU-code compilation (ADR-005); later
  starts took 2 s. The agent should still start the server once and keep it running.
- **TTS speed:** Kokoro takes 2.7 s to make a 6.5 s sentence, so replies must be spoken in short
  chunks, a short first chunk starting audio in about 0.7 s (ADR-011). Piper remains the fallback.
- **Licences to confirm before publishing:** the Qwen2.5-1.5B licence, and espeak-ng (bundled by
  `espeakng-loader`, believed to be GPL-3.0). Whisper (MIT) and Kokoro (Apache 2.0) are confirmed.
