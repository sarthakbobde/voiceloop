"""Loads configs/models.yaml: which model runs each stage, where, and its VRAM estimate."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from voiceloop import paths


class StageModel(BaseModel):
    model: str
    device: Literal["cuda", "cpu"]
    vram_mib: int  # rough estimate, checked against the real number in Step 01


class Stack(BaseModel):
    vad: StageModel
    asr: StageModel
    llm: StageModel
    tts: StageModel

    def vram_total_mib(self) -> int:
        stages = [self.vad, self.asr, self.llm, self.tts]
        return sum(stage.vram_mib for stage in stages if stage.device == "cuda")


def load_stack(path: Path = paths.MODELS_CONFIG) -> Stack:
    with open(path, encoding="utf-8") as f:
        return Stack.model_validate(yaml.safe_load(f)["stack"])
