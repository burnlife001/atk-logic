"""
ATK-Logic CLI entry point.

Commands:
    info          Show capture file metadata
    export        Export edge events for channel(s)
    list-decoders List available protocol decoders
    decode        Run protocol decoder on capture data

Usage:
    python3.14.exe atk_cli.py info test.atkdl
    python3.14.exe atk_cli.py export test.atkdl --ch 0 --start 0 --end 1ms
    python3.14.exe atk_cli.py list-decoders --filter uart
    python3.14.exe atk_cli.py decode test.atkdl --decoder uart --rx 0 --option baudrate=115200
"""

from __future__ import annotations

import _bootstrap  # noqa: F401 — must precede other imports for .pyd loading

import argparse
import json
import sys
from pathlib import Path

from atk_reader import CaptureReader, EdgeEvent, parse_time

# Decoder requires Python 3.14
try:
    from atk_decoder import DecoderBridge
except RuntimeError:
    DecoderBridge = None  # type: ignore


def _out(data, fmt):
    if fmt == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        for k, v in data.items():
            print(f"{k}: {v}")


def _err(msg):
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------

def cmd_info(args):
    reader = CaptureReader(args.file)
    info = reader.get_info()
    _out(
        {
            "channels": info.channels,
            "sample_rate_hz": info.sample_rate_hz,
            "total_samples": info.total_samples,
            "duration_ns": info.duration_ns,
            "capture_time": info.capture_time,
            "file_format": info.file_format,
        },
        args.format,
    )


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

def cmd_export(args):
    reader = CaptureReader(args.file)
    start_ns = parse_time(args.start)
    end_ns = parse_time(args.end) if args.end else None
    channel_ids = [int(c.strip()) for c in args.ch.split(",")]
    result = {}
    for cid in channel_ids:
        edges = reader.read_edges(cid, start_ns, end_ns, args.max_events)
        result[str(cid)] = [
            {"t_ns": e.t_ns, "level": e.level, "dur_ns": e.dur_ns} for e in edges
        ]
    _out({"channels": result}, args.format)


# ---------------------------------------------------------------------------
# list-decoders
# ---------------------------------------------------------------------------

def cmd_list_decoders(args):
    if DecoderBridge is None:
        _out({"error": "Decoder module requires Python 3.14+. Use python3.14.exe launcher."}, args.format)
        sys.exit(1)

    filter_ids = [f.strip() for f in args.filter.split(",")] if args.filter else None
    bridge = DecoderBridge()
    try:
        decoders = bridge.list_decoders(filter_ids)
    except Exception as e:
        _out({"error": str(e)}, args.format)
        sys.exit(1)

    data = [
        {
            "id": d.id,
            "name": d.name,
            "desc": d.desc,
            "channels": d.channels,
            "opt_channels": d.opt_channels,
            "options": d.options,
        }
        for d in decoders
    ]
    _out(data, args.format)


# ---------------------------------------------------------------------------
# decode
# ---------------------------------------------------------------------------

def _edges_to_dense(edges: list[EdgeEvent], start_sample: int, count: int) -> list[tuple[int, int]]:
    """Convert RLE edge events to dense (sample_num, level) tuples.

    Returns a list of (transition_sample, new_level) covering count samples from start_sample.
    """
    result: list[tuple[int, int]] = []
    if not edges:
        return result

    # Find the first edge that covers start_sample
    pos = start_sample
    for e in edges:
        e_start_sample = e.t_ns // 50  # will be recalculated below
        # Actually we need to work in sample space consistently
        pass

    # Use edges directly: each edge is (t_ns, level, dur_ns)
    # Convert to sample-space transitions
    prev_level = edges[0].level
    result.append((start_sample, prev_level))
    # We need sample rate info; for now this is handled in the caller
    return result


def cmd_decode(args):
    if DecoderBridge is None:
        _out({"error": "Decoder module requires Python 3.14+. Use python3.14.exe launcher."}, args.format)
        sys.exit(1)

    reader = CaptureReader(args.file)
    info = reader.get_info()
    multiply_ns = 1_000_000_000 // info.sample_rate_hz if info.sample_rate_hz else 50

    start_ns = parse_time(args.start)
    end_ns = parse_time(args.end) if args.end else None

    # Build channel map from --rx, --tx, --scl, etc.
    channel_map: dict[str, int] = {}
    for key in ("rx", "tx", "scl", "sda", "clk", "mosi", "miso", "cs"):
        val = getattr(args, key, None)
        if val is not None:
            channel_map[key] = val

    decoder_options: dict[str, str] = {}
    if args.option:
        for opt in args.option:
            if "=" in opt:
                k, v = opt.split("=", 1)
                decoder_options[k] = v

    # Read edge events for mapped channels and convert to dense sample data
    all_edge_events: list[tuple[int, int]] = []
    if channel_map:
        first_ch = next(iter(channel_map.values()))
        edges = reader.read_edges(first_ch, start_ns, end_ns, args.max_events)
        # Convert edges to dense sample tuples
        start_sample = start_ns // multiply_ns
        for e in edges:
            s = e.t_ns // multiply_ns
            all_edge_events.append((s, e.level))
        # Add final sample
        if edges:
            last = edges[-1]
            final_s = (last.t_ns + last.dur_ns) // multiply_ns
            all_edge_events.append((final_s, last.level))

    bridge = DecoderBridge()
    try:
        bridge.init()
        frames = bridge.decode(
            decoder_id=args.decoder,
            channel_map=channel_map,
            options=decoder_options,
            edge_events=all_edge_events,
            sample_rate_hz=info.sample_rate_hz,
        )
    except Exception as e:
        _out({"error": str(e)}, args.format)
        sys.exit(1)

    _out(
        {
            "decoder": args.decoder,
            "frames": [
                {"t_ns": f.t_ns, "type": f.type, "data": f.data, "errors": f.errors}
                for f in frames
            ],
            "stats": {"total_frames": len(frames)},
        },
        args.format,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    # Force UTF-8 stdout on Windows (avoid GBK codec errors with e.g. I²C)
    import io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )

    parser = argparse.ArgumentParser(
        description="ATK-Logic CLI — logic analyzer data reader and decoder"
    )
    parser.add_argument(
        "--format", choices=("json", "text"), default="json", help="Output format"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # info
    p = sub.add_parser("info", help="Show capture file metadata")
    p.add_argument("file", type=Path, help="Path to .atkdl or .bin file")
    p.set_defaults(func=cmd_info)

    # export
    p = sub.add_parser("export", help="Export edge events for channel(s)")
    p.add_argument("file", type=Path)
    p.add_argument("--ch", required=True, help="Comma-separated channel IDs, e.g. 0,2,3")
    p.add_argument("--start", default="0", help="Start time (ns/us/ms/s)")
    p.add_argument("--end", default=None, help="End time (ns/us/ms/s)")
    p.add_argument("--max-events", type=int, default=10000)
    p.set_defaults(func=cmd_export)

    # list-decoders
    p = sub.add_parser("list-decoders", help="List available protocol decoders")
    p.add_argument("--filter", default=None, help="Comma-separated decoder IDs")
    p.set_defaults(func=cmd_list_decoders)

    # decode
    p = sub.add_parser("decode", help="Decode waveform with a protocol decoder")
    p.add_argument("file", type=Path)
    p.add_argument("--decoder", required=True, help="Decoder ID, e.g. uart")
    p.add_argument("--start", default="0", help="Start time")
    p.add_argument("--end", default=None, help="End time")
    p.add_argument("--max-events", type=int, default=100000, help="Max edge events")
    p.add_argument("--rx", type=int, help="Map RX to channel N")
    p.add_argument("--tx", type=int, help="Map TX to channel N")
    p.add_argument("--scl", type=int, help="Map SCL to channel N")
    p.add_argument("--sda", type=int, help="Map SDA to channel N")
    p.add_argument("--clk", type=int, help="Map CLK to channel N")
    p.add_argument("--mosi", type=int, help="Map MOSI to channel N")
    p.add_argument("--miso", type=int, help="Map MISO to channel N")
    p.add_argument("--cs", type=int, help="Map CS to channel N")
    p.add_argument("--option", action="append", help="Decoder option as key=value")
    p.set_defaults(func=cmd_decode)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
