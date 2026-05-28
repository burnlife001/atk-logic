"""
ATK-Logic CLI entry point.

Commands:
    info          Show capture file metadata
    export        Export edge events for channel(s)
    list-decoders List available protocol decoders
    decode        Run protocol decoder on capture data
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import click

from atk_reader import CaptureReader, parse_time

# Decoder is optional (requires Python 3.14)
try:
    from atk_decoder import DecoderBridge
except Exception as _e:
    DecoderBridge = None  # type: ignore


def _out(data: dict, fmt: str) -> None:
    if fmt == "json":
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        # Simple text fallback
        for k, v in data.items():
            click.echo(f"{k}: {v}")


def _warn(msg: str) -> None:
    click.echo(msg, err=True)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "text"]),
    default="json",
    help="Output format",
)
@click.pass_context
def cli(ctx: click.Context, fmt: str) -> None:
    ctx.ensure_object(dict)
    ctx.obj["format"] = fmt


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def info(ctx: click.Context, file: Path) -> None:
    """Show capture file metadata."""
    reader = CaptureReader(file)
    cap = reader.get_info()
    data = {
        "channels": cap.channels,
        "sample_rate_hz": cap.sample_rate_hz,
        "total_samples": cap.total_samples,
        "duration_ns": cap.duration_ns,
        "capture_time": cap.capture_time,
        "file_format": cap.file_format,
    }
    _out(data, ctx.obj["format"])


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--ch", required=True, help="Comma-separated channel IDs, e.g. 0,2,3")
@click.option("--start", default="0", help="Start time (supports ns/us/ms/s suffix)")
@click.option("--end", default=None, help="End time (supports ns/us/ms/s suffix)")
@click.option("--max-events", default=10_000, type=int, help="Max edge events per channel")
@click.pass_context
def export(
    ctx: click.Context,
    file: Path,
    ch: str,
    start: str,
    end: str | None,
    max_events: int,
) -> None:
    """Export edge events for specified channel(s)."""
    reader = CaptureReader(file)
    start_ns = parse_time(start)
    end_ns = parse_time(end) if end else None

    channel_ids = [int(c.strip()) for c in ch.split(",")]
    result: dict[str, list[dict]] = {}
    for cid in channel_ids:
        edges = reader.read_edges(cid, start_ns, end_ns, max_events)
        result[str(cid)] = [
            {"t_ns": e.t_ns, "level": e.level, "dur_ns": e.dur_ns}
            for e in edges
        ]

    _out({"channels": result}, ctx.obj["format"])


# ---------------------------------------------------------------------------
# list-decoders
# ---------------------------------------------------------------------------

@cli.command("list-decoders")
@click.option("--filter", default=None, help="Comma-separated decoder IDs to filter")
@click.pass_context
def list_decoders(ctx: click.Context, filter: str | None) -> None:
    """List available protocol decoders."""
    if DecoderBridge is None:
        click.echo(
            json.dumps(
                {
                    "error": "Decoder module unavailable. Python 3.14+ required."
                },
                indent=2,
            )
        )
        sys.exit(1)

    filter_ids = [f.strip() for f in filter.split(",")] if filter else None
    bridge = DecoderBridge()
    try:
        decoders = bridge.list_decoders(filter_ids)
    except RuntimeError as e:
        click.echo(json.dumps({"error": str(e)}, indent=2))
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
    _out(data, ctx.obj["format"])


# ---------------------------------------------------------------------------
# decode
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--decoder", required=True, help="Decoder ID, e.g. uart")
@click.option("--start", default="0", help="Start time")
@click.option("--end", default=None, help="End time")
@click.option("--max-events", default=100_000, type=int, help="Max edge events to decode")
@click.option("--rx", default=None, type=int, help="Map RX channel to physical channel N")
@click.option("--tx", default=None, type=int, help="Map TX channel to physical channel N")
@click.option("--scl", default=None, type=int, help="Map SCL channel to physical channel N")
@click.option("--sda", default=None, type=int, help="Map SDA channel to physical channel N")
@click.option("--clk", default=None, type=int, help="Map CLK channel to physical channel N")
@click.option("--mosi", default=None, type=int, help="Map MOSI channel to physical channel N")
@click.option("--miso", default=None, type=int, help="Map MISO channel to physical channel N")
@click.option("--cs", default=None, type=int, help="Map CS channel to physical channel N")
@click.option("--option", "options", multiple=True, help="Decoder option as key=value")
@click.pass_context
def decode(
    ctx: click.Context,
    file: Path,
    decoder: str,
    start: str,
    end: str | None,
    max_events: int,
    rx: int | None,
    tx: int | None,
    scl: int | None,
    sda: int | None,
    clk: int | None,
    mosi: int | None,
    miso: int | None,
    cs: int | None,
    options: tuple[str, ...],
) -> None:
    """Decode waveform with a protocol decoder."""
    if DecoderBridge is None:
        click.echo(
            json.dumps(
                {
                    "error": "Decoder module unavailable. Python 3.14+ required."
                },
                indent=2,
            )
        )
        sys.exit(1)

    channel_map: dict[str, int] = {}
    for key, val in [
        ("rx", rx), ("tx", tx), ("scl", scl), ("sda", sda),
        ("clk", clk), ("mosi", mosi), ("miso", miso), ("cs", cs),
    ]:
        if val is not None:
            channel_map[key] = val

    decoder_options: dict[str, str] = {}
    for opt in options:
        if "=" in opt:
            k, v = opt.split("=", 1)
            decoder_options[k] = v

    reader = CaptureReader(file)
    info = reader.get_info()
    start_ns = parse_time(start)
    end_ns = parse_time(end) if end else None

    # Gather edge events for all mapped channels
    all_edges: dict[int, list] = {}
    for ch_id in channel_map.values():
        if ch_id not in all_edges:
            all_edges[ch_id] = reader.read_edges(ch_id, start_ns, end_ns, max_events)

    # Convert to dense sample tuples for decoder
    # For now, we export frames from the first channel's edges
    # (decoder needs dense sample buffer - this is a simplified approach)
    _warn("decode: dense sample reconstruction not yet fully implemented")

    bridge = DecoderBridge()
    try:
        frames = bridge.decode(
            decoder_id=decoder,
            channel_map=channel_map,
            options=decoder_options,
            edge_events=[],  # TODO: dense reconstruction
            sample_rate_hz=info.sample_rate_hz,
        )
    except RuntimeError as e:
        click.echo(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)

    data = {
        "decoder": decoder,
        "frames": [
            {"t_ns": f.t_ns, "type": f.type, "data": f.data, "errors": f.errors}
            for f in frames
        ],
        "stats": {"total_frames": len(frames), "error_frames": 0},
    }
    _out(data, ctx.obj["format"])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
