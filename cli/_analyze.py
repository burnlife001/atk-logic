"""Analyze decoded UART output from stdin JSON."""
import sys, json
from collections import Counter

data = json.load(sys.stdin)
frames = [f for f in data.get('frames', []) if f['type'] == 'data']
bytes_ = [f['data']['byte'] for f in frames]
unique = sorted(set(bytes_))

# Find repeating pattern
found = False
for period in range(3, 12):
    if len(bytes_) >= period * 3:
        chunks = [tuple(bytes_[i:i+period]) for i in range(0, len(bytes_)-period+1, period)]
        if all(c == chunks[0] for c in chunks[:10]):
            text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunks[0])
            print(f'Total frames: {len(frames)}')
            print(f'Unique bytes ({len(unique)}): {[hex(b) for b in unique]}')
            print(f'Pattern (period={period}): {text!r}')
            print(f'Pattern hex: {[hex(b) for b in chunks[0]]}')
            found = True
            break

if not found:
    print(f'Total frames: {len(frames)}')
    print(f'Unique bytes ({len(unique)}): {[hex(b) for b in unique]}')
    print(f'No repeating pattern found')
    text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in bytes_[:60])
    print(f'First 60 chars: {text!r}')

err_frames = [f for f in data.get('frames', []) if f.get('errors')]
print(f'Error frames: {len(err_frames)}')
print(f'Top byte counts: {Counter(bytes_).most_common(10)}')
