"""Detailed CH1 analysis."""
import sys
sys.path.insert(0, "E:/__electric/atk-logic/cli")
from atk_reader import CaptureReader

r = CaptureReader("E:/__electric/atk-logic/data/uart_123456.atkdl")
info = r.get_info()
print(f"SampleRate: {info.sample_rate_hz/1e6:.1f}MHz")

edges = r.read_edges(1, 0, None, 500)
long_pulses = [(e.t_ns, e.level, e.dur_ns) for e in edges if e.dur_ns > 1000]
short_pulses = [(e.t_ns, e.level, e.dur_ns) for e in edges if e.dur_ns <= 1000]
glitch_pairs = [(e.t_ns, e.level, e.dur_ns) for e in edges if e.dur_ns < 500]

print(f"\nCH1: {len(edges)} edges")
print(f"  Long pulses (>1us): {len(long_pulses)}")
print(f"  Short pulses (<1us): {len(short_pulses)}")
print(f"  Glitch pulses (<500ns): {len(glitch_pairs)}")

print(f"\n=== Long pulses (>1us) ===")
for t, lvl, dur in long_pulses:
    print(f"  t={t/1e6:12.3f}ms  lvl={lvl}  dur={dur/1e6:10.3f}ms")

print(f"\n=== Glitch pulses at transitions (<500ns) ===")
# Group into pairs at each transition
i = 0
while i < len(glitch_pairs):
    t1, lvl1, d1 = glitch_pairs[i]
    if i + 1 < len(glitch_pairs):
        t2, lvl2, d2 = glitch_pairs[i + 1]
        # Check if they're close together (same transition)
        if t2 - t1 - d1 < 1000:
            print(f"  pair: {d1:4.0f}ns{'H' if lvl1 else 'L'} + {d2:4.0f}ns{'H' if lvl2 else 'L'}  (gap={t2-t1-d1}ns)")
            i += 2
            continue
    print(f"  solo: {d1:4.0f}ns{'H' if lvl1 else 'L'} at t={t1/1e6:.3f}ms")
    i += 1

print(f"\n=== First 3 Long pulses detail ===")
for t, lvl, dur in long_pulses[:6]:
    surrounding = [e for e in edges if abs(e.t_ns - t) < 2000 or abs(e.t_ns - t - dur) < 2000]
    print(f"  LONG: t={t/1e6:.3f}ms lvl={lvl} dur={dur/1e6:.3f}ms")
    for se in surrounding:
        if se.dur_ns < 500:
            print(f"    near: t={se.t_ns/1e6:.3f}ms lvl={se.level} dur={se.dur_ns}ns")
