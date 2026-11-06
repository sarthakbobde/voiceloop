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
| [002](#adr-002) | Real-time inference on the laptop's 4 GB GTX 1650; all training on Kaggle | Accepted | 2026-11-01 |
| [003](#adr-003) | Same layout as ticket-triage: uv, Pydantic, one CLI, tests, lint, CI | Accepted | 2026-11-01 |

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
