with open("E:/__electric/atk-logic/proxy_dll/proxy_main.c", "rb") as f:
    content = f.read()

marker = b"InterlockedExchange(&g_capturing, 0);\n        return;"
idx = content.find(marker)
if idx < 0:
    print("ERROR: return marker not found")
    import sys; sys.exit(1)

# Find next InterlockedExchange after the dead code
next_exchange = content.find(b"\n        InterlockedExchange(&g_capturing, 0);\n\n    }", idx + len(marker))
if next_exchange < 0:
    print("ERROR: dead code end marker not found")
    # Show what comes after
    tail = content[idx + len(marker):idx + len(marker) + 200]
    print(f"Tail: {tail!r}")
    import sys; sys.exit(1)

dead_start = idx + len(marker)
dead_end = next_exchange + 1  # Keep the newline before } else if
print(f"Removing dead code: bytes {dead_start} to {dead_end} ({dead_end - dead_start} bytes)")

new_content = content[:dead_start] + b"\n" + content[dead_end:]

with open("E:/__electric/atk-logic/proxy_dll/proxy_main.c", "wb") as f:
    f.write(new_content)
print(f"Done. {len(content)} -> {len(new_content)} bytes")
