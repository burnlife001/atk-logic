"""Quick check: which channels have edges in a capture file."""
import sys
sys.path.insert(0, 'cli')
from atk_reader import CaptureReader

reader = CaptureReader(sys.argv[1])
info = reader.get_info()
for ch in range(len(info.channels)):
    edges = reader.read_edges(ch, 0, 100_000_000, 10)
    if edges:
        levels = [e.level for e in edges[:5]]
        times = [e.t_ns for e in edges[:5]]
        print(f'  CH{ch}: {len(edges)} edges, first levels={levels}, first times={times}')
    else:
        print(f'  CH{ch}: no edges')
