# Roadmap

Legend: 🧑 = you do it · 🤖 = Claude does it (after explaining) · 🤝 = together

How each step is built and what "done" means: [PLAN.md](PLAN.md).

Each phase ends with a result you can compare against the one before it. Stopping after Phase 2
or 3 still leaves a complete project.

## Phase 0 — Foundations
- [x] 🤖 **00 Scaffold** — package, `voiceloop` CLI, `voiceloop doctor`, tests, CI, docs.
- [x] 🧑 **01 Environment setup** — ffmpeg, the `realtime` extra, the prebuilt llama.cpp CUDA server (no compiler needed), HF cache on E:, each model run on its own, VRAM measured. *Result: Qwen 78 tok/s on the GPU, Whisper small 11× real time on the GPU, Kokoro 2.3× real time on the CPU; GPU stack ~1.57 GB of VRAM; ADRs 004–011.*

## Phase 1 — Cascaded baseline with real-time turn-taking
- [ ] 🤝 **02 Mic → VAD → ASR loop** — streaming faster-whisper behind Silero VAD; print partial transcripts.
- [ ] 🤝 **03 LLM + TTS, streamed by sentence** — first audio out before the reply is finished.
- [ ] 🤝 **04 Barge-in and endpointing** — the user can interrupt; the agent stops speaking.
- [ ] 🤝 **05 Latency and turn-taking harness** — per-stage timings, time to first audio (p50/p95), interruptions and missed turn ends on a fixed set of recorded conversations.

## Phase 2 — Speech-in LLM (Whisper encoder → adapter → Qwen)
- [ ] 🤝 **06 Adapter on ASR** — frozen Whisper encoder, trained projector + LoRA on Qwen (Kaggle, LibriSpeech).
- [ ] 🤝 **07 Spoken instruction following** — instruction data turned into speech with TTS.
- [ ] 🧑 **08 Compare with Phase 1** — accuracy and latency on the Step 05 harness.

## Phase 3 — Learned turn-taking
- [ ] 🤝 **09 End-of-turn model** — audio features + partial transcript → "has the user finished?"; ROC vs the VAD timeout.

## Phase 4 — RL and self-improvement
- [ ] 🤝 **10 GRPO on spoken tasks** — rewards you can check: task success, latency/length, an LLM judge.
- [ ] 🤝 **11 Self-learning loop** — log failures, relabel, retrain, track gains per round.

## Phase 5 — Persistent memory
- [ ] 🤝 **12 Memory store and recall benchmark** — facts kept across sessions; ask about them days later.
