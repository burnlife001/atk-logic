import sys
sys.path.insert(0, "E:/__electric/atk-logic/cli")
sys.path.insert(0, "C:/Users/yg/.claude/skills/atk-logic-capture/scripts")
from atk_reader import CaptureReader
from atk_wave import _first_edge_anomaly, _pulse_stability, _detect_bounce_pairs

r = CaptureReader("E:/__electric/atk-logic/data/uart_123456.atkdl")
info = r.get_info()
edges = list(r.read_edges(1, 0, None, 500))
real = [e for e in edges if e.dur_ns >= 1000]

fa = _first_edge_anomaly(real)
print("first_anomaly:", fa)

bounce = _detect_bounce_pairs(edges, info.sample_rate_hz)
print("bounce:", bounce)

d_high = [e.dur_ns for e in real if e.level == 1]
d_low = [e.dur_ns for e in real if e.level == 0]
print(f"high durs: {d_high[:3]}... ({len(d_high)} total)")
print(f"low durs:  {d_low[:3]}... ({len(d_low)} total)")

if fa and real:
    if real[0].level == 1:
        sh = d_high[1:]
        sl = d_low
    else:
        sh = d_high
        sl = d_low[1:]
else:
    sh = d_high
    sl = d_low

print(f"\nstable_high: {len(sh)} entries, first 3: {sh[:3]}")
print(f"stable_low:  {len(sl)} entries, first 3: {sl[:3]}")

sh_stab = _pulse_stability(sh)
sl_stab = _pulse_stability(sl)
print(f"\nhigh stability: {sh_stab}")
print(f"low stability:  {sl_stab}")

if sh_stab and sl_stab:
    is_ultra = sh_stab["cv_pct"] < 0.5 and sl_stab["cv_pct"] < 0.5
    print(f"\nis_ultra_stable={is_ultra}")
    print(f"has_bounce={bounce is not None}")
    print(f"would_be_clock={is_ultra and bounce is not None}")
