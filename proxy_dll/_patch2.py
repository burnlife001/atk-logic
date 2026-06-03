import sys

# Add paste + Enter after Ctrl+S to interact with the QML save dialog
OLD = b"""        dbg_log("start: sending Ctrl+S to save directly...");
        focus_window();
        Sleep(200);
        send_mod_combo(VK_CONTROL, 0, 'S');
        dbg_log("start: Ctrl+S sent, waiting for GUI to save...");
        Sleep(2000);"""

NEW = b"""        dbg_log("start: sending Ctrl+S to open save dialog...");
        focus_window();
        Sleep(200);
        send_mod_combo(VK_CONTROL, 0, 'S');
        dbg_log("start: Ctrl+S sent, waiting for QML save dialog...");
        Sleep(800);
        /* QML dialog opened - paste filename and press Enter to save */
        if (output[0]) {
            const char *fn = output;
            {
                const char *p = output;
                while (*p) { if (*p == '\\\\' || *p == '/') fn = p + 1; p++; }
            }
            dbg_log("start: pasting filename into dialog...");
            paste_text(fn);
            Sleep(400);
        }
        dbg_log("start: pressing Enter to click Save button...");
        press_enter();
        dbg_log("start: Enter pressed, waiting for save to complete...");
        Sleep(1500);

        /* Handle possible overwrite confirm dialog */
        {
            HWND confirm = FindWindowA("#32770", NULL);
            if (confirm) {
                DWORD pid;
                GetWindowThreadProcessId(confirm, &pid);
                if (pid == GetCurrentProcessId()) {
                    dbg_log("start: overwrite confirm dialog found, pressing Enter");
                    press_enter();
                    Sleep(1000);
                }
            }
        }"""

filepath = "E:/__electric/atk-logic/proxy_dll/proxy_main.c"

with open(filepath, "rb") as f:
    content = f.read()

if OLD not in content:
    print("ERROR: old string not found")
    idx = content.find(b"Ctrl+S sent")
    if idx >= 0:
        print(f"Found 'Ctrl+S sent' at {idx}: {content[idx:idx+200]!r}")
    sys.exit(1)

new_content = content.replace(OLD, NEW, 1)
print(f"Replaced. Old len={len(OLD)}, New len={len(NEW)}")

with open(filepath, "wb") as f:
    f.write(new_content)
print("Done.")
