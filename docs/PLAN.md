# Development Plan

How VoiceLoop gets built: architecture, the work in each step, what "done" means, and the risks.
The checklist lives in [STEPS.md](STEPS.md); decisions live in [DECISIONS.md](DECISIONS.md).
This file is the *how*. Update it when a step teaches us something.

**Goal:** a full-duplex voice agent built from open-weight models. Every phase replaces one part of
a working baseline and is judged on the same harness (ADR-001).

**Constraints:** 4 GB GTX 1650 for real-time inference, Kaggle for all training (ADR-002).
Time estimates assume part-time work and are guesses until Phase 1 is done.

---

## 1. Architecture

### Runtime: one loop, timestamped events

```
mic ──► ring buffer ──► VAD ──► ASR (streaming) ──► turn manager ──► LLM (streaming) ──► sentence splitter ──► TTS ──► speaker
                          │                              ▲   │                                                     │
                          └──── speech_start ────────────┘   └──────────── barge-in: stop LLM + playback ◄─────────┘
```

- **Audio thread** (sounddevice callback) only copies frames into a queue. Nothing slow runs there.
- **Main loop** pulls frames, runs the VAD, and drives a **turn manager**: a small state machine
  (`listening → user_speaking → thinking → agent_speaking`, plus `interrupted`).
- **ASR, LLM and TTS** run in worker threads so a slow stage never blocks listening.
- **Every stage emits a timestamped event**: `speech_start`, `speech_end`, `asr_partial`,
  `asr_final`, `llm_first_token`, `llm_first_sentence`, `tts_first_chunk`, `playback_start`,
  `barge_in`, `playback_stop`. Every latency and turn-taking metric is computed from this event log
  afterwards, so measuring never changes the code being measured.

### Replay mode: the key to testing

The audio source is an interface. `MicSource` reads the microphone; `FileSource` plays a recorded
`.wav` into the pipeline in real time (or faster). The eval harness, the tests and debugging all
use `FileSource`. That gives repeatable numbers, CI tests without a mic, and the same recorded
conversations for every phase.

### Planned package layout

```
src/voiceloop/
  audio/        sources (mic, file), playback, ring buffer
  stages/       vad.py, asr.py, llm.py, tts.py  — one wrapper per model, same small interface
  turn.py       the turn manager state machine (pure logic, fully unit-tested)
  events.py     event types and the event log writer
  agent.py      wires sources, stages and the turn manager together
  evals/        latency.py, turns.py, report.py  — read event logs, write reports
  speechllm/    Phase 2: encoder wrapper, projector, data building
  memory/       Phase 5: store, extraction, retrieval
```

Model code stays behind thin wrappers so Phase 2 can swap `asr + llm` for one speech-in model
without touching the turn manager.

### Serving the LLM

Run the llama.cpp server (prebuilt CUDA binary) and talk to it through an OpenAI-compatible
client, as in ticket-triage. That avoids building `llama-cpp-python` with CUDA on Windows, and
makes it easy to point at Kaggle or a hosted model when comparing. *To record as ADR-004 in Step 01.*

---

## 2. Measurement (built in Phase 1, used by every phase)

| Metric | Definition | Phase 1 target |
|---|---|---|
| Time to first audio (TTFA) | `speech_end` → `playback_start` | p50 ≤ 1.2 s, p95 ≤ 2.0 s |
| Barge-in stop time | user `speech_start` while agent speaks → `playback_stop` | p95 ≤ 300 ms |
| False cut-in rate | agent starts speaking while the user is mid-turn (pause, not finished) | ≤ 10 % of turns |
| Late response gap | turn ends where TTFA exceeds 2 s | ≤ 10 % of turns |
| WER | ASR word error rate on the recorded set | measured, no target |
| Per-stage time | VAD tail, ASR final, LLM first sentence, TTS first chunk | measured |

Targets are first guesses. Step 05 replaces them with what the baseline actually achieves; later
phases must beat the baseline, not the guesses.

**Eval set:** 30–50 short recorded conversations (your own voice), each with a script that marks
where the turns really end, including deliberate mid-sentence pauses to test cut-ins. Audio stays
out of git; the scripts and reports are committed.

Reports go to `evals/reports/<run>.md` + `.json`, same as ticket-triage.

---

## 3. Phases

### Phase 0 — Foundations (≈ 2–3 days)

**00 Scaffold** ✅ — package, `voiceloop doctor`, tests, CI, docs.

**01 Environment setup**
- Install ffmpeg; upgrade uv (0.2.20 is old).
- `uv sync --extra realtime`; download the llama.cpp CUDA build; put the HF cache on E:.
- Get each model running on its own: Silero VAD on a wav, faster-whisper small int8 on CUDA,
  Qwen2.5-1.5B Q4_K_M in llama.cpp server, Kokoro speaking one sentence.
- Measure real VRAM with all GPU models loaded together; replace the estimates in
  `configs/models.yaml`. Extend `voiceloop doctor` to list microphones and the CUDA device.
- **Done when:** each model runs alone, `doctor` reports the measured VRAM, ADR-004 written.

### Phase 1 — Cascaded baseline (≈ 2–3 weeks)

**02 Mic → VAD → ASR loop**
- Audio sources (mic + file), ring buffer, Silero VAD with start/end hysteresis.
- Stream speech segments to faster-whisper; print partial and final transcripts.
- `voiceloop listen` command.
- **Done when:** live transcripts appear while speaking; the same file in replay mode gives the
  same transcript every time.

**03 LLM + TTS, streamed by sentence**
- Stream LLM tokens, cut into sentences, send each sentence to TTS as soon as it is complete.
- Playback queue that can be cleared instantly.
- `voiceloop chat` command: a working spoken conversation.
- **Done when:** first audio starts before the LLM has finished the reply.

**04 Barge-in and endpointing**
- Turn manager state machine; while the agent speaks, user speech stops the LLM and clears
  playback.
- Endpointing v1: silence timeout after VAD end (configurable, start at ~600 ms).
- Echo: use headphones at first. Speaker echo triggering false barge-ins is a known problem; an
  echo canceller is a later improvement, not a blocker.
- **Done when:** interrupting the agent stops it within the target time; unit tests cover every
  state transition.

**05 Latency and turn-taking harness**
- Record the eval set; `voiceloop eval run --source recordings/` replays it and writes event logs.
- `voiceloop eval report` computes the metrics in section 2.
- Sweep the silence timeout (300–1000 ms) to show the trade-off between cut-ins and gaps; this
  curve is the baseline Phase 3 must beat.
- **Done when:** a committed baseline report and a short demo video.

> **Checkpoint:** a working voice agent with measured latency is already a strong portfolio
> piece. Write the README results table here.

### Phase 2 — Speech-in LLM (≈ 3 weeks, Kaggle)

Replace `ASR → text → LLM` with one model that takes audio directly.

**Design:** frozen Whisper-small encoder → stack every 4 frames (50 Hz → 12.5 Hz) → 2-layer MLP
projector → Qwen2.5 input embeddings. The audio embeddings are spliced into the prompt where an
`<audio>` placeholder sits.

**06 Adapter on ASR**
- Stage A: train only the projector on LibriSpeech train-clean-100 with a "transcribe" prompt.
- Kaggle notebook in the ticket-triage style; checkpoint the projector weights (small).
- **Done when:** WER on LibriSpeech test-clean within reach of Whisper-small itself
  (the encoder is the same, so a large gap means the projector is the problem).

**07 Spoken instruction following**
- Stage B: projector + LoRA on Qwen. Data: an open text instruction set, user turns turned into
  speech with Kokoro using several voices and speeds, plus some real recordings.
- Mix in ASR examples so transcription ability is not forgotten.
- **Done when:** the model answers spoken questions sensibly without a transcript step.

**08 Compare with Phase 1**
- Same questions through (a) cascade and (b) speech-in model: answer quality (LLM judge +
  spot checks), latency on the laptop.
- Running it locally is the hard part: 4 GB will not hold the encoder plus a 1.5B model in fp16.
  Options in order: 4-bit Qwen via bitsandbytes, Qwen2.5-0.5B, or encoder on CPU. Decide with
  measurements and record the ADR.
- **Done when:** a comparison report, honest about where the cascade still wins.

### Phase 3 — Learned turn-taking (≈ 1–2 weeks)

**09 End-of-turn model**
- Input: the last ~2 s of audio features (energy, pitch, VAD probability, or Whisper encoder
  features) + the partial transcript. Output: probability the user has finished.
- Labels: from the scripted eval-style recordings (true turn ends known) plus extra recordings
  with deliberate thinking pauses. Keep the Phase 1 eval set held out.
- Small model (GRU or logistic regression on features first, then the text-aware version);
  trains on CPU or Kaggle.
- **Done when:** at the same false cut-in rate, the response gap is shorter than the best silence
  timeout from Step 05 (shown as a curve against the timeout sweep).

### Phase 4 — RL and self-improvement (≈ 3 weeks, Kaggle)

**10 GRPO on spoken tasks**
- Tasks with checkable outcomes: a small sandbox of tools (timer, unit conversion, calendar in a
  local file, simple lookups). Requests are synthesized as speech with varied voices.
- Rewards: task solved (checked against the sandbox state), correct tool arguments, short spoken
  answer (latency proxy), and an LLM-judge score for helpfulness at a low weight.
- Trainer: TRL's GRPO, or OpenPipe ART if its agent loop fits better; decide in an ADR.
- **Done when:** task success on a held-out task set beats the Phase 2 model.

**11 Self-learning loop**
- Log real sessions (event log + transcripts) locally.
- Detect failures automatically: user repeats or corrects, tool errors, low judge score.
- Relabel failures (a teacher model, with approval before any paid call), add to training data,
  retrain, re-evaluate on a **frozen** held-out set so the loop cannot quietly overfit.
- **Done when:** a chart of held-out success across 2–3 rounds.

### Phase 5 — Persistent memory (≈ 1–2 weeks)

**12 Memory store and recall benchmark**
- Store per user in SQLite: extracted facts (with embeddings from a small CPU embedding model)
  and short session summaries.
- Write policy: after each session, extract facts; update or retire facts that contradict new ones.
- Read policy: retrieve the top facts for the current turn and add them to the prompt; measure
  the latency this adds.
- Benchmark: scripted multi-session conversations with questions about earlier sessions.
  Metrics: recall accuracy, false-memory rate, added latency.
- **Done when:** recall is clearly better than no memory, with added latency under ~100 ms.

---

## 4. Working rules

- **Measure before changing.** No phase starts until the harness can score it.
- **Logic is testable without hardware.** Turn manager, sentence splitter, metrics and memory
  policies are pure functions or state machines tested in CI; model wrappers are thin.
- **One CLI.** Each step adds a `voiceloop` subcommand; handlers only parse options.
- **Decisions get ADRs.** Model swaps, serving choices and trainer choices are recorded.
- **Data hygiene.** Audio, weights and raw logs stay out of git; only scripts, configs and
  reports are committed. Only record your own voice or openly licensed audio.
- **Paid API calls need explicit approval**, every time.

---

## 5. Risks

| Risk | Impact | Plan |
|---|---|---|
| 4 GB VRAM too tight once everything runs together | Phase 1 latency, Phase 2 local inference | Measure in Step 01; move TTS/VAD to CPU (already planned), smaller models, 4-bit |
| Speaker echo triggers false barge-ins | Bad turn-taking numbers | Headphones first; WebRTC/speex echo canceller later |
| Windows audio and CUDA build friction | Lost days in Step 01 | llama.cpp server binary instead of building bindings; WASAPI via sounddevice |
| Kokoro needs extra system packages on Windows | TTS setup | Piper as the fallback TTS |
| Kaggle GPU quota and session limits | Slow Phase 2/4 iteration | Small data first, checkpoint often, keep notebooks resumable |
| Synthetic (TTS) speech differs from real speech | Phase 2/4 models fail on real voices | Mix in real recordings; evaluate on the real recorded set only |
| Turn-taking labels are subjective | Noisy Phase 3 results | Scripted recordings with known turn ends; same set for every comparison |

---

## 6. Milestones

| Milestone | After | What you can show |
|---|---|---|
| M1 — Working voice agent | Step 05 | Demo video, latency + turn-taking report |
| M2 — Speech-in LLM | Step 08 | Architecture write-up, cascade vs end-to-end comparison |
| M3 — Learned turn-taking | Step 09 | Curve beating the silence-timeout baseline |
| M4 — Self-improving agent | Step 11 | GRPO results and gains across loop rounds |
| M5 — Memory | Step 12 | Recall benchmark |

M1 + M2 already match the core of the target role; M3–M5 cover the rest of its bullets.
