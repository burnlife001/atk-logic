import sys

# Fix: use full python.exe path
OLD = b"""            const char *prefix = "python E:/__electric/atk-logic/proxy_dll/uia_save.py ";"""

NEW = b"""            const char *prefix = "\\\"D:/Programs/.pyenv/pyenv-win/versions/3.12.9/python.exe\\\" E:/__electric/atk-logic/proxy_dll/uia_save.py ";"""

filepath = "E:/__electric/atk-logic/proxy_dll/proxy_main.c"

with open(filepath, "rb") as f:
    content = f.read()

if OLD not in content:
    print("ERROR: old string not found")
    idx = content.find(b"python")
    if idx >= 0:
        print(f"Found 'python' at {idx}: {content[idx:idx+150]!r}")
    sys.exit(1)

new_content = content.replace(OLD, NEW, 1)
print(f"OK. Fixed python path.")

with open(filepath, "wb") as f:
    f.write(new_content)
print("Done.")
