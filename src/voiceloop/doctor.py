"""`voiceloop doctor`: checks this machine can run the Phase 1 stack.

The parsing and verdict functions take plain values, so they are tested without a GPU.
"""

import platform
import shutil
import subprocess
from dataclasses import dataclass

from voiceloop.config import Stack, load_stack

# Leave room for the CUDA context and the desktop, which also live in VRAM.
VRAM_HEADROOM_MIB = 500


@dataclass
class Gpu:
    name: str
    vram_mib: int


def parse_nvidia_smi(csv_text: str) -> list[Gpu]:
    """Parse `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits`."""
    gpus = []
    for line in csv_text.strip().splitlines():
        if not line.strip():
            continue
        name, vram = line.rsplit(",", 1)
        gpus.append(Gpu(name=name.strip(), vram_mib=int(vram.strip())))
    return gpus


def find_gpus() -> list[Gpu]:
    if shutil.which("nvidia-smi") is None:
        return []
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return parse_nvidia_smi(result.stdout)


def vram_verdict(gpus: list[Gpu], stack: Stack) -> str:
    needed = stack.vram_total_mib() + VRAM_HEADROOM_MIB
    if not gpus:
        return f"no NVIDIA GPU found: run every stage on CPU (the stack wants ~{needed} MiB of VRAM)"
    best = max(gpus, key=lambda gpu: gpu.vram_mib)
    if best.vram_mib >= needed:
        return f"ok: {best.name} has {best.vram_mib} MiB, the stack needs ~{needed} MiB"
    return f"too tight: {best.name} has {best.vram_mib} MiB, needs ~{needed} MiB; move a stage to CPU"


def run_doctor() -> list[tuple[str, str]]:
    """Return (check, result) rows for the CLI to print."""
    rows = [("python", platform.python_version())]
    gpus = find_gpus()
    for gpu in gpus:
        rows.append(("gpu", f"{gpu.name}, {gpu.vram_mib} MiB"))
    rows.append(("vram", vram_verdict(gpus, load_stack())))
    for tool in ["ffmpeg", "uv", "git"]:
        rows.append((tool, "found" if shutil.which(tool) else "missing"))
    try:
        import sounddevice

        inputs = [d["name"] for d in sounddevice.query_devices() if d["max_input_channels"] > 0]
        rows.append(("microphones", ", ".join(inputs) if inputs else "none found"))
    except ImportError:
        rows.append(("microphones", "unknown: install the realtime extra (uv sync --extra realtime)"))
    return rows
