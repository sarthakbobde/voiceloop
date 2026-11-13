"""Tests for the shared pieces: config loading, the doctor's parsing and verdicts, CLI parsing."""

import pytest

from voiceloop.cli import build_parser
from voiceloop.config import load_stack
from voiceloop.doctor import VRAM_HEADROOM_MIB, Gpu, parse_nvidia_smi, power_verdict, vram_verdict

# ---- config ----------------------------------------------------------------------------------


def test_models_config_loads_and_fits_a_4gb_card():
    stack = load_stack()
    assert stack.vram_total_mib() < 4096


# ---- doctor --------------------------------------------------------------------------------------


def test_parse_nvidia_smi_reads_name_total_and_free_vram():
    text = "NVIDIA GeForce GTX 1650, 4096, 3296\n"
    assert parse_nvidia_smi(text) == [Gpu("NVIDIA GeForce GTX 1650", 4096, 3296)]


def test_parse_nvidia_smi_handles_commas_in_the_name_and_blank_lines():
    gpus = parse_nvidia_smi("Card, Rev B, 8192, 8000\n\n")
    assert gpus == [Gpu("Card, Rev B", 8192, 8000)]


def test_vram_verdict_ok_when_the_stack_fits():
    assert vram_verdict([Gpu("big", 24000, 24000)], load_stack()).startswith("ok")


def test_vram_verdict_too_tight_when_the_stack_does_not_fit():
    assert vram_verdict([Gpu("small", 1024, 1024)], load_stack()).startswith("too tight")


def test_vram_verdict_uses_free_memory_not_total():
    # ADR-009: the total is plenty, but other apps leave one MiB too little free.
    stack = load_stack()
    needed = stack.vram_total_mib() + VRAM_HEADROOM_MIB
    gpu = Gpu("GTX 1650", vram_mib=4096, free_mib=needed - 1)
    assert vram_verdict([gpu], stack).startswith("too tight")
    assert vram_verdict([Gpu("GTX 1650", vram_mib=4096, free_mib=needed)], stack).startswith("ok")


def test_vram_verdict_ok_when_the_card_is_nearly_empty():
    gpu = Gpu("GTX 1650", vram_mib=4096, free_mib=3935)
    assert vram_verdict([gpu], load_stack()).startswith("ok")


def test_vram_verdict_without_a_gpu_suggests_cpu():
    assert "CPU" in vram_verdict([], load_stack())


def test_power_verdict_ok_when_plugged_in():
    assert power_verdict(True).startswith("ok")


def test_power_verdict_warns_on_battery():
    assert "battery" in power_verdict(False)


def test_power_verdict_says_unknown_when_unreadable():
    assert power_verdict(None).startswith("unknown")


# ---- cli -----------------------------------------------------------------------------------------


def test_cli_requires_a_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_cli_parses_doctor():
    args = build_parser().parse_args(["doctor"])
    assert args.command == "doctor"
