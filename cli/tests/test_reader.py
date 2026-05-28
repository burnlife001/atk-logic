"""Tests for atk_reader."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from atk_reader import parse_time, CaptureReader


def test_parse_time():
    assert parse_time("100ns") == 100
    assert parse_time("100") == 100
    assert parse_time("1.5us") == 1500
    assert parse_time("2ms") == 2_000_000
    assert parse_time("1s") == 1_000_000_000


def test_atkdl_info():
    test_file = Path(__file__).parent.parent.parent / "data" / "uart_123456.atkdl"
    if not test_file.exists():
        return
    reader = CaptureReader(test_file)
    info = reader.get_info()
    assert info.sample_rate_hz == 20_000_000
    assert info.total_samples == 1_200_000_000
    assert info.file_format == "source"
    assert len(info.channels) == 16


def test_atkdl_edges():
    test_file = Path(__file__).parent.parent.parent / "data" / "uart_123456.atkdl"
    if not test_file.exists():
        return
    reader = CaptureReader(test_file)
    edges = reader.read_edges(0, start_ns=0, end_ns=parse_time("1ms"), max_events=100)
    assert len(edges) > 0
    assert edges[0].level in (0, 1)
    assert edges[0].dur_ns > 0


if __name__ == "__main__":
    test_parse_time()
    test_atkdl_info()
    test_atkdl_edges()
    print("All tests passed.")
