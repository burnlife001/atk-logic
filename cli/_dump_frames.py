import sys, json
data = json.load(sys.stdin)
frames = data.get('frames', [])
for f in frames[:40]:
    t = f['t_ns']
    typ = f['type']
    err = ' ERR' if f.get('errors') else ''
    if typ == 'data':
        print(f'{t:12d} {typ:6s} {f["data"]["hex"]} {f["data"]["text"]!r}{err}')
    elif typ == 'start':
        print(f'{t:12d} {typ:6s} ---')
    elif typ == 'bit':
        print(f'{t:12d} {typ:6s} bit={f["data"]["bit"]} val={f["data"]["value"]}')
