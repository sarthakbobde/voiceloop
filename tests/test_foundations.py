"""Tests for the shared pieces: config loading, the doctor's parsing and verdicts, CLI parsing."""

import pytest

from voiceloop.cli import build_parser
from voiceloop.config import load_stack
from voiceloop.doctor import Gpu, parse_nvidia_smi, vram_verdict

# ---- config ----------------------------------------------------------------------------------


def test_models_config_loads_and_fits_a_4gb_card():
    stack = load_stack()
    assert stack.vram_total_mib() < 4096


# ---- doctor --------------------------------------------------------------------------------------


def test_parse_nvidia_smi_reads_name_and_vram():
    assert parse_nvidia_smi("NVIDIA GeForce GTX 1650, 4096\n") == [Gpu("NVIDIA GeForce GTX 1650", 4096)]


def test_parse_nvidia_smi_handles_commas_in_the_name_and_blank_lines():
    gpus = parse_nvidia_smi("Card, Rev B, 8192\n\n")
    assert gpus == [Gpu("Card, Rev B", 8192)]


def test_vram_verdict_ok_when_the_stack_fits():
    assert vram_verdict([Gpu("big", 24000)], load_stack()).startswith("ok")


def test_vram_verdict_too_tight_when_the_stack_does_not_fit():
    assert vram_verdict([Gpu("small", 1024)], load_stack()).startswith("too tight")


def test_vram_verdict_without_a_gpu_suggests_cpu():
    assert "CPU" in vram_verdict([], load_stack())


# ---- cli -----------------------------------------------------------------------------------------


def test_cli_requires_a_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_cli_parses_doctor():
    args = build_parser().parse_args(["doctor"])
    assert args.command == "doctor"
