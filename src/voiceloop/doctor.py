"""`voiceloop doctor`: checks this machine can run the Phase 1 stack.

The parsing and verdict functions take plain values, so they are tested without a GPU or a battery.
"""

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass

from voiceloop.config import Stack, load_stack

# Leave room for the CUDA context, which also lives in VRAM.
VRAM_HEADROOM_MIB = 500


@dataclass
class Gpu:
    name: str
    vram_mib: int  # total
    free_mib: int  # free right now: Windows and other apps already use some (ADR-009)


def parse_nvidia_smi(csv_text: str) -> list[Gpu]:
    """Parse `nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits`."""
    gpus = []
    for line in csv_text.strip().splitlines():
        if not line.strip():
            continue
        name, total, free = line.rsplit(",", 2)
        gpus.append(Gpu(name=name.strip(), vram_mib=int(total.strip()), free_mib=int(free.strip())))
    return gpus


def find_gpus() -> list[Gpu]:
    if shutil.which("nvidia-smi") is None:
        return []
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
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
    best = max(gpus, key=lambda gpu: gpu.free_mib)
    have = f"{best.name} has {best.free_mib} MiB free of {best.vram_mib}"
    if best.free_mib >= needed:
        return f"ok: {have}, the stack needs ~{needed} MiB"
    return f"too tight: {have}, needs ~{needed} MiB; close GPU apps or move a stage to CPU"


def find_on_ac_power() -> bool | None:
    """True on mains power, False on battery, None if it cannot be read (not Windows, or no answer)."""
    if sys.platform != "win32":
        return None
    import ctypes

    class PowerStatus(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_ubyte),  # 0 battery, 1 mains, 255 unknown
            ("BatteryFlag", ctypes.c_ubyte),
            ("BatteryLifePercent", ctypes.c_ubyte),
            ("SystemStatusFlag", ctypes.c_ubyte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    status = PowerStatus()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return None
    return {0: False, 1: True}.get(status.ACLineStatus)


def power_verdict(on_ac: bool | None) -> str:
    if on_ac is None:
        return "unknown: could not read the power state"
    if on_ac:
        return "ok: plugged in"
    return "on battery: the GPU is throttled, so plug in before benchmarking (ADR-008)"


def run_doctor() -> list[tuple[str, str]]:
    """Return (check, result) rows for the CLI to print."""
    rows = [("python", platform.python_version())]
    gpus = find_gpus()
    for gpu in gpus:
        rows.append(("gpu", f"{gpu.name}, {gpu.vram_mib} MiB"))
    rows.append(("vram", vram_verdict(gpus, load_stack())))
    rows.append(("power", power_verdict(find_on_ac_power())))
    for tool in ["ffmpeg", "uv", "git"]:
        rows.append((tool, "found" if shutil.which(tool) else "missing"))
    try:
        import sounddevice

        inputs = [d["name"] for d in sounddevice.query_devices() if d["max_input_channels"] > 0]
        rows.append(("microphones", ", ".join(inputs) if inputs else "none found"))
    except ImportError:
        rows.append(("microphones", "unknown: install the realtime extra (uv sync --extra realtime)"))
    return rows
