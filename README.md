# VoiceLoop

A full-duplex voice agent built from open-weight models. The name covers both loops in the
project: the live listen → think → speak loop, and the self-learning loop that retrains on
its own failures. Built step by step:

1. **Cascaded baseline** — Silero VAD → faster-whisper → Qwen → Kokoro TTS, with barge-in and a
   latency / turn-taking harness.
2. **Speech-in LLM** — frozen Whisper encoder + trained adapter + LoRA on Qwen.
3. **Learned turn-taking** — an end-of-turn model instead of a silence timeout.
4. **RL and self-improvement** — GRPO on spoken tasks, plus a retrain-on-failures loop.
5. **Persistent memory** — recall across sessions.

Each phase is measured against the one before it. Roadmap: [docs/STEPS.md](docs/STEPS.md) ·
decisions: [docs/DECISIONS.md](docs/DECISIONS.md).

## Quick start

```bash
uv sync                      # core + dev tools
uv run voiceloop doctor      # check GPU, VRAM budget, ffmpeg, microphones
uv run pytest -q
```

The real-time stack is an extra, installed on the laptop only:

```bash
uv sync --extra realtime
```

## Hardware

Built for a 4 GB GTX 1650: small quantized models on the GPU, VAD and TTS on the CPU
(ADR-002). Training runs on Kaggle.
