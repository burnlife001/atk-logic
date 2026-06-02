"""
ATK-Logic CLI entry point.

Commands:
    info          Show capture file metadata
    export        Export edge events for channel(s)
    list-decoders List available protocol decoders
    decode        Run protocol decoder on capture data
    capture       Start capture from USB device and save as .atkdl

Built-in decoders (native Python, no DLL needed): uart, i2c, spi.
Other decoders require libsigrokdecode-4.dll + Python 3.14.

Usage:
    python atk_cli.py info test.atkdl
    python atk_cli.py export test.atkdl --ch 0 --start 0 --end 1ms
    python atk_cli.py list-decoders --filter uart
    python atk_cli.py decode test.atkdl --decoder uart --rx 0 --option baudrate=115200
    python atk_cli.py capture start --ch 0 --duration 5s --output data/capture.atkdl
"""

from __future__ import annotations

import _bootstrap  # noqa: F401 — must precede other imports for .pyd loading

import argparse
import json
import sys
from pathlib import Path

from atk_reader import CaptureReader, parse_time
from atk_proto import (
    native_decode,
    get_native_decoder_ids,
    list_native_decoders,
)
# DecoderBridge requires Python 3.14 + libsigrokdecode-4.dll
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
    filter_ids = [f.strip() for f in args.filter.split(",")] if args.filter else None

    # Always show built-in native decoders first
    data = list_native_decoders(filter_ids)

    # If DLL is available, also show libsigrokdecode decoders
    if DecoderBridge is not None:
        try:
            bridge = DecoderBridge()
            bridge_decoders = bridge.list_decoders(filter_ids)
            data += [
                {
                    "id": d.id,
                    "name": d.name + " (libsigrokdecode)",
                    "desc": d.desc,
                    "channels": d.channels,
                    "opt_channels": d.opt_channels,
                    "options": d.options,
                }
                for d in bridge_decoders
            ]
        except Exception as e:
            _err(f"DLL decoder list failed: {e}")

    _out(data, args.format)


# ---------------------------------------------------------------------------
# decode
# ---------------------------------------------------------------------------

def cmd_decode(args):
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

    # ── Native decoder path (built-in, no DLL needed) ──
    native_ids = get_native_decoder_ids()
    if args.decoder in native_ids:
        try:
            frames = native_decode(
                decoder_id=args.decoder,
                channel_map=channel_map,
                reader=reader,
                options=decoder_options,
                start_ns=start_ns,
                end_ns=end_ns,
                max_events=args.max_events,
            )
        except Exception as e:
            _out({"error": str(e)}, args.format)
            sys.exit(1)

        _out(
            {
                "decoder": args.decoder,
                "engine": "native",
                "frames": frames,
                "stats": {"total_frames": len(frames)},
            },
            args.format,
        )
        return

    # ── DLL decoder path (libsigrokdecode) ──
    if DecoderBridge is None:
        _out(
            {
                "error": (
                    f"Decoder '{args.decoder}' not built-in. "
                    f"Built-in decoders: {', '.join(native_ids)}. "
                    "For other decoders, run with python3.14.exe launcher and libsigrokdecode-4.dll."
                )
            },
            args.format,
        )
        sys.exit(1)

    # Convert edges to dense sample tuples for DLL decoder
    all_edge_events: list[tuple[int, int]] = []
    if channel_map:
        first_ch = next(iter(channel_map.values()))
        edges = reader.read_edges(first_ch, start_ns, end_ns, args.max_events)
        start_sample = start_ns // multiply_ns
        for e in edges:
            s = e.t_ns // multiply_ns
            all_edge_events.append((s, e.level))
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
            "engine": "libsigrokdecode",
            "frames": [
                {"t_ns": f.t_ns, "type": f.type, "data": f.data, "errors": f.errors}
                for f in frames
            ],
            "stats": {"total_frames": len(frames)},
        },
        args.format,
    )


# ---------------------------------------------------------------------------
# capture
# ---------------------------------------------------------------------------

def cmd_capture(args):
    import json
    import socket
    import time

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)

    try:
        sock.connect(("127.0.0.1", 9876))
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        _err(f"Cannot connect to ATK-Logic GUI at 127.0.0.1:9876 ({e})")
        _err("Please start ATK-Logic.exe first, then retry.")
        sys.exit(1)

    try:
        if args.capture_action == "start":
            duration_str = args.duration
            duration_ns = parse_time(duration_str)
            duration_s = duration_ns / 1_000_000_000

            output = args.output
            if output is None:
                ts = time.strftime("%Y%m%d_%H%M%S")
                output = f"data/capture_{ts}.atkdl"

            output = str(Path(output).resolve())
            Path(output).parent.mkdir(parents=True, exist_ok=True)

            print(f"=== ATK-Logic Capture ===")
            print(f"  Sample rate: {args.sample_rate_hz / 1e6:.0f} MHz")
            print(f"  Duration:    {duration_s:.1f}s")
            print(f"  Channel:     {args.ch}")
            print(f"  Threshold:   {args.threshold} V")
            print(f"  Output:      {output}")
            print(f"  RLE:         {'on' if args.rle else 'off'}")

            req = {
                "cmd": "start",
                "ch": args.ch,
                "duration_s": duration_s,
                "sample_rate_hz": args.sample_rate_hz,
                "threshold_v": args.threshold,
                "output": output,
                "rle": args.rle,
            }
            sock.sendall((json.dumps(req) + "\n").encode())

            # Wait for responses: progress updates then final result
            sock.settimeout(duration_s + 30)
            buf = b""
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        resp = json.loads(line.decode())
                        status = resp.get("status", "")
                        if status == "progress":
                            phase = resp.get("phase", "capture")
                            schedule = resp.get("schedule", 0)
                            print(f"\r  [{phase}] {schedule}%", end="", flush=True)
                        elif status == "ok":
                            print(f"\nCapture complete!")
                            print(f"  File:    {resp.get('file', output)}")
                            print(f"  Rate:    {resp.get('sample_rate_hz', 0) / 1e6:.0f} MHz")
                            print(f"  Duration:{resp.get('duration_s', 0):.1f}s")
                            return
                        elif status == "error":
                            print(f"\nError: {resp.get('msg', 'unknown error')}")
                            sys.exit(1)
                except socket.timeout:
                    print(f"\nError: Capture timed out (no response from GUI)")
                    sys.exit(1)

        elif args.capture_action == "stop":
            req = {"cmd": "stop"}
            sock.sendall((json.dumps(req) + "\n").encode())
            sock.settimeout(5)
            resp_data = sock.recv(4096)
            resp = json.loads(resp_data.decode().strip())
            if resp.get("status") == "ok":
                print("Capture stopped.")
            else:
                _err(f"Error: {resp.get('msg', 'unknown error')}")
                sys.exit(1)
    finally:
        sock.close()


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

    # capture
    p = sub.add_parser("capture", help="Start/stop USB capture from logic analyzer device")
    p.add_argument("capture_action", choices=("start", "stop"), help="Start or stop capture")
    p.add_argument("--ch", type=int, default=0, help="Channel number (default 0)")
    p.add_argument("--duration", default="5s", help="Capture duration (ns/us/ms/s, default 5s)")
    p.add_argument("--sample-rate-hz", dest="sample_rate_hz", type=int, default=100_000_000,
                   help="Sample rate in Hz (default 100000000 = 100MHz, matching GUI)")
    p.add_argument("--threshold", type=float, default=3.3,
                   help="Logic threshold voltage (default 3.3V, matching GUI)")
    p.add_argument("--rle", action="store_true", default=False,
                   help="Enable FPGA RLE compression (default off, matching GUI)")
    p.add_argument("--no-rle", action="store_false", dest="rle",
                   help="Disable FPGA RLE compression")
    p.add_argument("--output", "-o", default=None, help="Output .atkdl file path (default: data/capture_<timestamp>.atkdl)")
    p.set_defaults(func=cmd_capture)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
