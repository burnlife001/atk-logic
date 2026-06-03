"""Extract exports from official Qt5Network.dll and generate proxy .def + .c files."""
from __future__ import annotations
import pefile
from pathlib import Path

DLL_PATH = Path("D:/Programs/ATK-Logic/Qt5Network.dll")
REAL_DLL_NAME = "Qt5Network_real.dll"
OUT_DIR = Path(__file__).resolve().parent

pe = pefile.PE(str(DLL_PATH))
symbols = pe.DIRECTORY_ENTRY_EXPORT.symbols

exports = []
for exp in symbols:
    if exp.name:
        name = exp.name.decode()
    else:
        name = None
    ordinal = exp.ordinal
    forwarder = exp.forwarder.decode() if exp.forwarder else None
    exports.append((ordinal, name, forwarder, exp.address))

print(f"Total exports: {len(exports)}")
named = [e for e in exports if e[1]]
unnamed = [e for e in exports if not e[1]]
forwarded = [e for e in exports if e[2]]
print(f"  Named: {len(named)}, Unnamed (ordinal only): {len(unnamed)}, Forwarded: {len(forwarded)}")

# Generate .def file for MSVC linker
# For forwarded exports, we use the original forwarder or proxy to our real DLL
def_lines = ["EXPORTS"]
for ordinal, name, forwarder, addr in exports:
    if name:
        def_lines.append(f"    {name}={REAL_DLL_NAME}.{name} @{ordinal}")
    else:
        # Unnamed exports must use NONAME
        def_lines.append(f"    proxy_ord_{ordinal}={REAL_DLL_NAME}.#{ordinal} @{ordinal} NONAME")

def_path = OUT_DIR / "Qt5Network_proxy.def"
def_path.write_text("\n".join(def_lines) + "\n", encoding="utf-8")
print(f"Generated: {def_path} ({len(def_lines)-1} exports)")

# Show first 20 named exports as sample
print("\nFirst 20 named exports:")
for ordinal, name, fwd, addr in exports:
    if name:
        print(f"  @{ordinal}: {name}")
        if len([e for e in exports if e[1] and exports.index(e) < 20]) >= 20:
            break

# List all forwarded exports
if forwarded:
    print(f"\nForwarded exports ({len(forwarded)}):")
    for ordinal, name, fwd, addr in forwarded:
        print(f"  @{ordinal}: {name or '(unnamed)'} -> {fwd}")
