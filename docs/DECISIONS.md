# Decision Log

Every project decision lives in this one file. Each entry is an **ADR** (Architecture Decision
Record): the context, the options considered, what was chosen, and the consequences.

**Rules**
- Never delete or rewrite an accepted decision. If it changes, add a new ADR and mark the old one
  `Superseded by ADR-XXX`. The history is the point.
- Add new decisions at the bottom with the next number, and add a row to the index.
- Link to a decision as `docs/DECISIONS.md#adr-002`.

## Index

| ADR | Decision | Status | Date |
|---|---|---|---|
| [001](#adr-001) | Build a cascaded baseline first, then replace parts with trained models | Accepted | 2026-11-01 |
| [002](#adr-002) | Real-time inference on the laptop's 4 GB GTX 1650; all training on Kaggle | Accepted; amended by ADR-009 (budget against free VRAM) | 2026-11-01 |
| [003](#adr-003) | Same layout as ticket-triage: uv, Pydantic, one CLI, tests, lint, CI | Accepted | 2026-11-01 |
| [004](#adr-004) | Serve the LLM with the prebuilt llama.cpp server, not `llama-cpp-python` | Accepted (changes the original plan) | 2026-11-09 |
| [005](#adr-005) | Pin llama.cpp build b12211, CUDA 12.4 | Accepted | 2026-11-09 |
| [006](#adr-006) | LLM weights = Qwen2.5-1.5B-Instruct Q4_K_M from the official GGUF repo | Accepted | 2026-11-09 |
| [007](#adr-007) | Python packages and why each was chosen | Accepted | 2026-11-09 |
| [008](#adr-008) | Run benchmarks plugged in and record the power state | Accepted | 2026-11-09 |
| [009](#adr-009) | Budget VRAM against free memory, not total (amends ADR-002) | Accepted; `doctor` implements it | 2026-11-09 |
| [010](#adr-010) | Whisper small on the GPU: cap `av<19`, reuse llama.cpp's cuBLAS DLLs | Accepted; `av` cap applied | 2026-11-13 |

## Changes from the original plan

The plan (ADR-001 to ADR-003, `PLAN.md`, `STEPS.md`) was written before anything ran on this
machine. This table lists every place reality made us change it, so the plan and the project
never silently disagree. The phases themselves (cascade → speech-in LLM → learned turn-taking →
RL → memory) are **unchanged**.

| Topic | Original plan | Now | Why | ADR |
|---|---|---|---|---|
| LLM runtime | `llama-cpp-python` in the `realtime` extra | Prebuilt `llama-server` + the `openai` client | No C++ compiler or cmake on this machine; building CUDA bindings on Windows is slow and fragile | [004](#adr-004) |
| llama.cpp version | "download the llama.cpp CUDA build" | Exact build b12211, CUDA 12.4, checksum-verified | GitHub's "latest" tag has no binaries; the driver supports CUDA ≤ 13.4 | [005](#adr-005) |
| LLM weights | Qwen2.5-1.5B Q4_K_M (estimated 1800 MiB) | Same model; official file downloaded and verified (1.04 GiB) | Source and integrity were unspecified | [006](#adr-006) |
| PyTorch | Not a dependency | Arrives CPU-only through `silero-vad`; GPU PyTorch only on Kaggle | VAD runs on the CPU, so a CPU build is enough for Phase 1 | [007](#adr-007) |
| Benchmarking | No rule | Plugged in, performance mode, power state recorded | On battery the GPU memory clock dropped to 810 MHz and generation was about 3× slower | [008](#adr-008) |
| VRAM budget | "needs ~3300 MiB, GPU has 4096: ok" | Windows already uses ~800 MiB; only 3296 MiB is free, so the margin is about zero | `doctor` compared against total VRAM | [009](#adr-009) |
| Speech recognition on the GPU | "faster-whisper small int8 on the GPU" | Same, but needs `av<19` and cuBLAS DLLs borrowed from the llama.cpp folder | PyAV 19 broke `faster-whisper`; no CUDA Toolkit installed | [010](#adr-010) |
| VRAM estimates | ~2800 MiB for the GPU stack | Measured ~1567 MiB (LLM 1154 + Whisper 413) | Estimates were conservative | [009](#adr-009) |
| Docs | README, STEPS, DECISIONS | Added `PLAN.md`, `ARCHITECTURE.md`, `WORKING-WITH-CLAUDE.md` | The *how*, the structure, and working practices needed their own homes | none |

## Project log

What changed and when. Commit hashes are in the VoiceLoop repo.

| Date | What |
|---|---|
| 2026-11-06 | Scaffold committed (`4003fc5`): package, `voiceloop doctor`, tests, CI, roadmap, ADRs 001–003. Private GitHub repo created and pushed. |
| 2026-11-06 | Development plan added (`69453b7`). |
| 2026-11-09 | Step 01 started. ffmpeg found (already installed). `realtime` extra installed. `llama-cpp-python` replaced by `openai` in the extra (`766973d`, ADR-004). |
| 2026-11-09 | llama.cpp b12211 (CUDA 12.4) and the Qwen2.5-1.5B Q4_K_M GGUF downloaded and SHA-256 verified into the git-ignored `models/` folder (ADR-005, ADR-006). |
| 2026-11-09 | First GPU benchmark was slow; traced to the laptop running on battery (ADR-008). Free VRAM found to be ~3.3 GB (ADR-009). Server reply test and VRAM measurement still pending. |
| 2026-11-09 | Local-only documents written, not yet committed: ADRs 004–009, `ARCHITECTURE.md`, `WORKING-WITH-CLAUDE.md`, `CLAUDE.md`. |
| 2026-11-09 | `voiceloop doctor` now checks free VRAM (ADR-009) and warns on battery (ADR-008); 13 tests. `dev-dependencies` moved to `dependency-groups` to silence a uv deprecation warning. Not committed. |
| 2026-11-13 | Plugged in and re-measured (ADR-008): Qwen Q4_K_M generates at 78 tok/s on the GPU (was 19.5 on battery) and 26 on the CPU. Server ready in 2 s. LLM VRAM measured at 1128 MiB (ADR-009). First streamed replies through the `openai` client: 3 runs, ~75 tok/s. |
| 2026-11-13 | Whisper small (Systran, MIT) downloaded and verified into `models/whisper-small/`. Needed `av<19` and cuBLAS from the llama.cpp folder to run on the GPU: 11.6× real time, +413 MiB (ADR-010, proposed). Both GPU models together measured at ~1.57 GB. |
| 2026-11-13 | ADR-010 applied: `av<19` pinned in the `realtime` extra; measured VRAM (LLM 1154, Whisper 413) put in `configs/models.yaml`, so `doctor` now needs ~2067 MiB. The free-memory test now builds its numbers from the config. 13 tests pass; Whisper transcribes on the GPU from the plain project environment. Not committed. |

## Template

```
<a id="adr-NNN"></a>
## ADR-NNN — Title
**Status:** Proposed | Accepted | Superseded by ADR-XXX · **Date:** YYYY-MM-DD · **Step:** NN

### Context
### Options
### Decision
### Consequences
```

<a id="adr-001"></a>
## ADR-001 — Cascaded baseline first, then replace parts with trained models
**Status:** Accepted · **Date:** 2026-11-01 · **Step:** 00

### Context
End-to-end speech-to-speech models (Moshi, Qwen-Omni and similar) are trained with far more
compute than this project has. The goal is to understand the architecture, train the parts that
matter, and measure latency and turn-taking carefully.

### Options
1. Start with an end-to-end model — no baseline to compare against, and too expensive to train.
2. Cascade only (VAD → ASR → LLM → TTS) — fast to build, but doesn't show model training.
3. **Cascade first, then swap in trained parts one phase at a time.**

### Decision
Option 3. Phase 1 builds the cascade and the measurement harness. Every later phase replaces one
part (speech-in LLM, end-of-turn model, RL-tuned policy, memory) and is judged on that harness.

### Consequences
- Every phase has a before/after number.
- The Step 05 harness must stay stable; changing it means re-running earlier phases.

<a id="adr-002"></a>
## ADR-002 — Real-time inference on a 4 GB GTX 1650; training on Kaggle
**Status:** Accepted · **Date:** 2026-11-01 · **Step:** 00

### Context
`voiceloop doctor` / nvidia-smi: GTX 1650, 4096 MiB, Turing (fp16 only, no bf16). Ryzen 5 5600H,
15 GB RAM. Real-time conversation needs ASR and LLM on the GPU together.

### Options
1. Larger models (3B+ LLM, Whisper medium) — do not fit next to each other in 4 GB.
2. **Small quantized models on GPU, VAD and TTS on CPU.**
3. Everything on CPU — latency too high for turn-taking work.

### Decision
Option 2: faster-whisper small (int8) and Qwen2.5-1.5B-Instruct Q4_K_M on the GPU; Silero VAD and
Kokoro-82M on the CPU. Estimated total ~2.8 GB plus headroom (`configs/models.yaml`). Training
(Phases 2–4) runs on Kaggle; the laptop only runs inference.

### Consequences
- The VRAM numbers are estimates until Step 01 measures them.
- Training deps (torch, transformers, peft, trl) are not project dependencies.

<a id="adr-003"></a>
## ADR-003 — Same layout as ticket-triage
**Status:** Accepted · **Date:** 2026-11-01 · **Step:** 00

### Context
The ticket-triage layout (installable package, one CLI, tests, ruff, CI) worked well and keeps
code readable.

### Decision
Reuse it: `src/voiceloop/`, a `voiceloop` CLI whose handlers only parse options, all paths in
`paths.py`, pytest + ruff in CI. Audio/model libraries go in the `realtime` extra so CI stays light.

### Consequences
- Code that needs a mic or GPU must be split so its logic can be tested on plain values.

<a id="adr-004"></a>
## ADR-004 — Serve the LLM with the prebuilt llama.cpp server
**Status:** Accepted · **Date:** 2026-11-09 · **Step:** 01 · **Changes the original plan**

### Context
The scaffold put `llama-cpp-python` in the `realtime` extra (commit `4003fc5`). On this machine
there is no C++ compiler (`cl.exe`) and no `cmake`, and a CUDA build of the Python bindings also
needs the multi-gigabyte CUDA Toolkit.

### Options
1. **`llama-cpp-python` built from source** — needs Visual Studio Build Tools, cmake and the CUDA
   Toolkit; hours of setup and the most likely thing to break on Windows.
2. **Third-party prebuilt wheels** — less setup, but we would trust an unofficial binary and have to
   match its CUDA version to the driver.
3. **Ollama** — easy, but it hides the flags we need for benchmarking and adds its own background
   service.
4. **llama.cpp's own prebuilt `llama-server`** — the project's official Windows binaries; no
   compiler; exposes an OpenAI-compatible HTTP API.
5. **vLLM** — no native Windows support.

### Decision
Option 4. The LLM runs as a separate process on `127.0.0.1:8080` and Python talks to it with the
`openai` client, exactly as ticket-triage talks to its models. The `realtime` extra now lists
`openai` instead of `llama-cpp-python` (commit `766973d`).

### Consequences
- The agent must start, health-check (`/health`) and stop the server process.
- Streaming works over the same API, so sentence-by-sentence TTS (Step 03) is unaffected.
- Pointing the agent at a hosted model for comparison only needs a different URL.
- The extra HTTP hop on localhost is expected to be small; Step 05 will measure it, not assume it.
- The server binds to localhost only. It warns that no API key is set and CORS is open, which is
  acceptable on localhost but must change before the port is ever exposed.

<a id="adr-005"></a>
## ADR-005 — Pin llama.cpp build b12211, CUDA 12.4
**Status:** Accepted · **Date:** 2026-11-09 · **Step:** 01

### Context
GitHub's "latest release" for ggml-org/llama.cpp (`v0.9.0`) has a single file and no Windows
binaries. The real builds are numbered pre-releases (`bNNNNN`), one per change. `nvidia-smi`
reports CUDA UMD 13.4 for the installed driver. A program built for a newer CUDA than the driver
supports may fail to load; one built for an older CUDA runs.

### Options
1. **CUDA 12.4 build** (289 MB program + 391 MB CUDA runtime DLLs) — older than the driver.
2. CUDA 13.5 build (171 MB + 426 MB) — newer than the driver's 13.4.
3. Vulkan build (38 MB) — no CUDA runtime needed, expected to be somewhat slower.
4. CPU-only build (25 MB) — too slow for real-time work.

### Decision
Option 1, **build b12211** (2026-11-08), installed to `models/llama.cpp/bin/` (git-ignored, 1.2 GB
unpacked). Both zips were checked against GitHub's published SHA-256 values and their contents
listed for unsafe paths before extraction. The CDN link returned HTTP 504 for the main zip after
retries; the same file downloaded through GitHub's API endpoint and passed the checksum.
`llama-server --list-devices` reports `CUDA0: NVIDIA GeForce GTX 1650`.

### Consequences
- Upgrading llama.cpp is a new ADR with a before/after benchmark; "latest" is never used.
- The Vulkan build stays available as a fallback and a comparison point.
- The build prints a hint that it was compiled with virtual GPU architectures, so the driver
  compiles GPU code on first use. The first server start took about a minute and NVIDIA's compute
  cache grew to 366 MB. On 2026-11-13 the server was ready **2 seconds** after launch. That is
  consistent with a one-time compile, though Windows also had the model file in its disk cache by
  then, so the two causes are not separated. Either way the agent should start the server once and
  keep it running.

<a id="adr-006"></a>
## ADR-006 — LLM weights: Qwen2.5-1.5B-Instruct Q4_K_M, official GGUF
**Status:** Accepted · **Date:** 2026-11-09 · **Step:** 01

### Context
ADR-002 chose a ~1.5B model in 4-bit form for the GPU. The exact file and its source were not
decided.

### Options
1. **Qwen2.5-1.5B-Instruct, Q4_K_M** — 1,117,320,736 bytes (1.04 GiB).
2. Qwen2.5-0.5B — faster, but weak at following instructions.
3. Qwen2.5-3B or Llama 3.2 3B — do not fit next to Whisper in ~3.3 GB of free VRAM.
4. Same model at Q5_K_M (1.3 GB) or Q8_0 (1.9 GB) — better quality, more memory and slower.

### Decision
Option 1, from Qwen's own repository (`Qwen/Qwen2.5-1.5B-Instruct-GGUF`), not a third-party
conversion. SHA-256 `6a1a2eb6…407e` matched the value Hugging Face publishes, and the file begins
with the `GGUF` marker. Stored at `models/qwen/` (git-ignored). Reasons: the same family as
ticket-triage and as the Phase 2 backbone (Whisper encoder → adapter → Qwen), so what we learn
transfers; Q4_K_M is the usual quality/size sweet spot and keeps the VRAM budget.

### Consequences
- Step 05 should compare Q4_K_M with Q5_K_M and Q8_0 for quality and latency before the choice is
  considered final.
- The licence of the base model must be confirmed before the project is published.

<a id="adr-007"></a>
## ADR-007 — Python packages and why
**Status:** Accepted · **Date:** 2026-11-09 · **Step:** 00–01

### Context
Each dependency is code we must trust, install and keep working. The rule: a package earns its
place by doing one job we need now, and training-only libraries stay out (ADR-002).

### Decision

| Package | Group | Job | Why this one | What we did not pick |
|---|---|---|---|---|
| `pydantic` | core | Validate `configs/models.yaml` and later event and memory records | Same as ticket-triage; clear errors | Hand-written dict checks |
| `pyyaml` | core | Read config files | Standard, tiny | TOML or JSON (YAML allows comments in configs) |
| `numpy` | core | Audio buffers and metrics (from Step 02) | Every audio library speaks it. Declared now, **not used by code yet** | Plain lists (too slow for audio) |
| `sounddevice` | `realtime` | Microphone input and speaker output | Callback API suits a real-time loop; installs from a wheel on Windows | `pyaudio` (harder Windows install) |
| `faster-whisper` | `realtime` | Speech recognition | CTranslate2 backend, int8 on a small GPU, no PyTorch needed for inference, streaming-friendly | `openai-whisper` (PyTorch, slower), Vosk (lower accuracy) |
| `silero-vad` | `realtime` | Detect when speech starts and stops | Small, accurate, runs on CPU in milliseconds | `webrtcvad` (older, less accurate) |
| `openai` | `realtime` | Client for the llama.cpp server | Same API as ticket-triage; works with any compatible server (ADR-004) | `llama-cpp-python` (ADR-004) |
| `pytest`, `ruff` | dev | Tests; lint and format | Same as ticket-triage | — |
| `hatchling`, `uv` | build | Package build; installs and lockfile | Same as ticket-triage; `uv.lock` makes installs repeatable | pip and requirements.txt |

Everything audio- or model-related is in the `realtime` extra so CI installs only the core
packages and stays fast. The TTS engine (Kokoro, with Piper as the fallback) is decided in the plan
but **not yet added** as a dependency.

### Consequences
- `silero-vad` pulls in PyTorch, which installed as the **CPU-only** build (`2.15.0+cpu`).
  That is enough because VAD runs on the CPU. GPU PyTorch is needed only for Phase 2 training
  (Kaggle) and, possibly, local inference of the speech-in model; that is a later decision.
- `faster-whisper` has its own CUDA requirements on Windows. Step 01 must confirm it runs on the GPU
  before the budget in ADR-009 is trusted.

<a id="adr-008"></a>
## ADR-008 — Run benchmarks plugged in, and record the power state
**Status:** Accepted · **Date:** 2026-11-09 · **Step:** 01

### Context
The first benchmark of the Qwen model on the GPU gave 19.5 tokens/s generating, slower than the
CPU's 30.2 tokens/s (prompt reading: GPU 302, CPU 122 tokens/s). Sampling `nvidia-smi` during the
run showed the memory clock at **810 MHz of a possible 6001 MHz**, performance state P5, and
throttle reason `0x24` (software power cap). Windows reported the battery as discharging at 58%.
Text generation is limited by memory bandwidth, and 13% of the clock predicts the speed we saw.
(Our first guess, GPU-code compilation on first run, was tested and ruled out: the numbers did not
change once the cache was warm.)

### Options
1. Ignore it and accept slow numbers — latency results would reflect the battery, not the design.
2. **Benchmark plugged in, in Windows "Best performance" mode, and record the state with every run.**
3. Also run a battery benchmark as a labelled worst case.

### Decision
Options 2 and 3. Reports say whether they were measured on AC power and in which power mode. A
battery run is allowed only as a separate, labelled result. Changing power settings is the user's
action, never the assistant's.

### Consequences
- The event log and report header gain a `power_state` field in Step 05.
- `voiceloop doctor` warns when the machine is on battery (done, 2026-11-09; uses the Windows
  `GetSystemPowerStatus` call, so it needs no extra package).
- The battery numbers above are **not** the model's real speed. Re-measured on 2026-11-13, plugged
  in (`doctor` said `ok: plugged in`), same build, same model, 3 repetitions:

  | | Reading the prompt | Generating |
  |---|---|---|
  | GPU, plugged in | 327 tok/s | **78 tok/s** (±6.6) |
  | CPU, plugged in | 176 tok/s | 26 tok/s |
  | GPU, on battery | 302 tok/s | 19.5 tok/s |

  Plugged in, generation is about 4× faster than on battery. A GPU memory clock of 5000 MHz was
  seen as the run ended, against 810 MHz when throttled. The hypothesis is confirmed.

<a id="adr-009"></a>
## ADR-009 — Budget VRAM against free memory, not total (amends ADR-002)
**Status:** Accepted; `doctor` implements it · **Date:** 2026-11-09 · **Step:** 01

### Context
`voiceloop doctor` originally compared the stack's estimated need (about 2800 MiB plus 500 MiB headroom =
3300 MiB) with the GPU's *total* memory (4096 MiB) and says "ok". But Windows already uses about
800 MiB for the desktop, so `llama-server --list-devices` shows **3296 MiB free**. The margin is
about zero, and our per-stage numbers are still estimates.

### Options
1. Keep comparing against the total — optimistic and misleading.
2. **Compare against free memory at the time of the check, and replace estimates with measured
   usage.**
3. Close other GPU-using apps — helps, but cannot be assumed.

### Decision
Option 2. `doctor` now reads `memory.free` from `nvidia-smi` and compares the stack against it; a
regression test covers the 4096 MiB card with 3000 MiB free. Free memory is not constant: it was
3296 MiB with a browser and the desktop open and 3935 MiB a little later with nothing else on the
GPU, so a pass or a fail depends on what is running. Step 01 ends by loading the models
together and recording the measured VRAM in `configs/models.yaml`. **Measured on
2026-11-13: loading the Qwen server (all layers on the GPU, 2048 context, 4 slots) raised VRAM
use from 800 to 1928 MiB, so the LLM costs 1128 MiB**, below the 1800 MiB estimate. **Whisper small on the
GPU adds 413 MiB** (after a transcription). With both loaded, the GPU stack uses about 1567 MiB
over the desktop baseline (209 MiB at the time), against the ~2800 MiB estimated in ADR-002.

### Consequences
- If the measured total does not fit, in order: Whisper base instead of small, a smaller context
  window than 2048, then the 0.5B LLM. VAD and TTS already run on the CPU.
- ADR-002's choices stand, and its "will fit" claim is now confirmed by measurement: even with
  the desktop using 800–1100 MiB there is about 1 GB of headroom. Kokoro (CPU) is still to be added.

<a id="adr-010"></a>
## ADR-010 — Whisper small on the GPU: cap `av`, reuse llama.cpp's cuBLAS
**Status:** Accepted; the `av` cap is applied, the DLL helper comes with the ASR wrapper in Step 02 · **Date:** 2026-11-13 · **Step:** 01

### Context
Testing `faster-whisper` 1.2.1 with the Systran `faster-whisper-small` weights (MIT licence,
483.5 MB, all four files checksum-verified, in `models/whisper-small/`) found two Windows problems.

1. **Decoding fails:** `faster-whisper` requires `av>=11` with no upper limit, so uv installed
   PyAV 19.0.2. That version no longer accepts the `metadata_errors` argument `faster-whisper`
   passes, giving `TypeError: open() got an unexpected keyword argument 'metadata_errors'` on every
   audio file. With `av<19` (resolved to 18.1.0) it works.
2. **GPU fails:** loading on CUDA succeeds, but the first computation raises
   `RuntimeError: Library cublas64_12.dll is not found`. CTranslate2 needs NVIDIA's cuBLAS, which
   is not installed on this machine.

### Options
- For 1: **cap `av<19` in the `realtime` extra**; or decode audio ourselves and pass arrays to
  `faster-whisper` (we will for microphone audio anyway, but file replay and the library's own
  helpers would still break); or wait for an upstream fix.
- For 2: install the multi-GB CUDA Toolkit; pip-install NVIDIA's cuBLAS and cuDNN wheels (another
  download of several hundred MB); or **reuse `cublas64_12.dll` and `cublasLt64_12.dll` from the
  llama.cpp CUDA 12.4 build already on disk** (ADR-005, checksum-verified).

### Decision
Add `av<19` to the `realtime` extra (applied 2026-11-13; uv moved from 19.0.2 to 18.1.0), and have the ASR wrapper add `models/llama.cpp/bin`
to the DLL search path (`os.add_dll_directory`) before loading the model. Both were tested without
changing the project: with `av<19` and that folder on `PATH`, GPU transcription was correct and
needed **no cuDNN and no extra download**.

### Consequences
- Whisper's GPU path depends on the llama.cpp folder. Upgrading llama.cpp to another CUDA version
  (ADR-005) must retest Whisper, and the loader should print what to do if the DLLs are missing.
  If that coupling becomes a problem, the NVIDIA pip wheels are the fallback.
- The `av` cap should be removed when `faster-whisper` handles PyAV 19.
- **Measured** on a 9.3 s test clip, int8: GPU 2.0 s on the first run (warm-up) and **0.81 s on the
  second, 11.6× faster than real time**; CPU 2.7–3.2 s, 3.0–3.5× real time; model load 1.5 s. VRAM
  +413 MiB (ADR-009).
- The test audio was a synthetic Windows voice ("Microsoft David"), transcribed exactly. Accuracy
  on real microphone speech is untested; word error rate is measured in Step 05.
