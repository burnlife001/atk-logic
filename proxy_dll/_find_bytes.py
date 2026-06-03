import sys

with open("E:/__electric/atk-logic/proxy_dll/proxy_main.c", "rb") as f:
    content = f.read()

# Find the "Step 4" marker
idx = content.find(b"Step 4: Ctrl")
print(f"'Step 4' at byte offset: {idx}")

# Find the InterlockedExchange line
end_idx = content.find(b"InterlockedExchange(&g_capturing, 0)", idx)
print(f"'InterlockedExchange' at byte offset: {end_idx}")

# Show the old block to replace (from Step 4 comment to just before InterlockedExchange)
if idx >= 0 and end_idx > idx:
    old_block = content[idx:end_idx]
    print(f"\nOld block size: {len(old_block)} bytes")
    print(f"First 100 bytes: {repr(old_block[:100])}")
    print(f"Last 100 bytes: {repr(old_block[-100:])}")
    # Check for problematic chars
    for i, b in enumerate(old_block):
        if b < 9 or (b > 13 and b < 32 and b != 10):
            print(f"  Unusual byte at offset {idx + i}: 0x{b:02x}")
