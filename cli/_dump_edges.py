import sys
sys.path.insert(0, 'cli')
from atk_reader import CaptureReader

reader = CaptureReader(sys.argv[1])
info = reader.get_info()
print(f"sample_rate_hz={info.sample_rate_hz}, total_samples={info.total_samples}")

edges = reader.read_edges(0, 0, 2_000_000, 1000)
for i, e in enumerate(edges[:30]):
    print(f"{i:3d}: t={e.t_ns:10d} level={e.level} dur_ns={e.dur_ns}")
