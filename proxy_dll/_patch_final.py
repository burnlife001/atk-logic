import sys

# 1. Fix main window class name
OLD1 = b'#define GUI_CLASS    L"Qt5152QWindowOwnDCIcon"'
NEW1 = b'#define GUI_CLASS    L"FramelessWindow_QML_51"'

# 2. Replace entire Step 4 (Ctrl+S + uia) with native #32770 dialog interaction
OLD2 = b"""        /* Step 4: Ctrl+S to open QML save dialog, then use UIA to click Save */
        dbg_log("start: sending Ctrl+S to open save dialog...");
        focus_window();
        Sleep(300);
        send_mod_combo(VK_CONTROL, 0, 'S');
        dbg_log("start: Ctrl+S sent, waiting for QML dialog...");
        Sleep(500);

        /* Launch Python UIA companion to click the Save button */
        if (output[0]) {
            char cmd[600];
            {
                /* Build: python uia_save.py <filename> */
                const char *prefix = "\\\"D:/Programs/.pyenv/pyenv-win/versions/3.12.9/python.exe\\\" E:/__electric/atk-logic/proxy_dll/uia_save.py ";
                int pos = 0;
                const char *ps = prefix;
                while (*ps && pos < 590) cmd[pos++] = *ps++;
                /* Get just the filename */
                {
                    const char *p = output;
                    const char *fn = output;
                    while (*p) { if (*p == '\\\\' || *p == '/') fn = p + 1; p++; }
                    while (*fn && pos < 590) cmd[pos++] = *fn++;
                }
                cmd[pos] = 0;
            }
            dbg_log("start: launching uia_save.py...");
            {
                STARTUPINFOA si;
                PROCESS_INFORMATION pi;
                int i;
                for (i = 0; i < (int)sizeof(si); i++) ((char*)&si)[i] = 0;
                si.cb = sizeof(si);
                for (i = 0; i < (int)sizeof(pi); i++) ((char*)&pi)[i] = 0;
                if (CreateProcessA(NULL, cmd, NULL, NULL, FALSE,
                                  CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
                    dbg_log("start: uia_save.py started, waiting...");
                    WaitForSingleObject(pi.hProcess, 15000); /* wait up to 15s */
                    CloseHandle(pi.hProcess);
                    CloseHandle(pi.hThread);
                    dbg_log("start: uia_save.py finished");
                } else {
                    dbg_log("start: failed to launch uia_save.py");
                }
            }
        }"""

NEW2 = (
    b"        /* Step 4: Ctrl+S to open native #32770 save dialog */\n"
    b'        dbg_log("start: sending Ctrl+S to open save dialog...");\n'
    b"        focus_window();\n"
    b"        Sleep(300);\n"
    b"        send_mod_combo(VK_CONTROL, 0, 'S');\n"
    b'        dbg_log("start: Ctrl+S sent, waiting for native save dialog...");\n'
    b"        Sleep(800);\n"
    b"\n"
    b"        /* Find the native #32770 save dialog - no PID check (runs in COM surrogate) */\n"
    b"        {\n"
    b"            int dialog_found = 0;\n"
    b"            for (int i = 0; i < 20; i++) {\n"
    b"                HWND w = GetTopWindow(NULL);\n"
    b"                while (w) {\n"
    b"                    char cls[32];\n"
    b"                    if (GetClassNameA(w, cls, 31) > 0) {\n"
    b"                        int is32770 = 0;\n"
    b"                        for (int j = 0; cls[j]; j++) {\n"
    b"                            if (cls[j] == '#' && cls[j+1] == '3' && cls[j+2] == '2'\n"
    b"                                && cls[j+3] == '7' && cls[j+4] == '7' && cls[j+5] == '0') {\n"
    b"                                is32770 = 1; break;\n"
    b"                            }\n"
    b"                        }\n"
    b"                        if (is32770) {\n"
    b"                            dbg_log(\"start: #32770 dialog found, focusing...\");\n"
    b"                            SetForegroundWindow(w);\n"
    b"                            Sleep(200);\n"
    b"                            dialog_found = 1;\n"
    b"                            break;\n"
    b"                        }\n"
    b"                    }\n"
    b"                    w = GetWindow(w, GW_HWNDNEXT);\n"
    b"                }\n"
    b"                if (dialog_found) break;\n"
    b"                Sleep(250);\n"
    b"            }\n"
    b"\n"
    b"            if (dialog_found && output[0]) {\n"
    b"                const char *filename = output;\n"
    b"                {\n"
    b"                    const char *p = output;\n"
    b"                    while (*p) { if (*p == '\\\\' || *p == '/') filename = p + 1; p++; }\n"
    b"                }\n"
    b'                dbg_log("start: pasting filename into dialog...");\n'
    b"                paste_text(filename);\n"
    b"                Sleep(400);\n"
    b'                dbg_log("start: pressing Enter to save...");\n'
    b"                press_enter();\n"
    b"                Sleep(1000);\n"
    b"\n"
    b"                /* Handle overwrite confirm dialog */\n"
    b"                {\n"
    b'                    HWND confirm = FindWindowA("#32770", NULL);\n'
    b"                    if (confirm) {\n"
    b'                        dbg_log("start: confirm/overwrite dialog found, pressing Enter");\n'
    b"                        press_enter();\n"
    b"                        Sleep(800);\n"
    b"                    }\n"
    b"                }\n"
    b"            }\n"
    b'            dbg_log(dialog_found ? "start: save dialog handled" : "start: save dialog NOT FOUND");\n'
    b"        }\n"
)

filepath = "E:/__electric/atk-logic/proxy_dll/proxy_main.c"

with open(filepath, "rb") as f:
    content = f.read()

# Apply fix 1
if OLD1 not in content:
    print("ERROR: OLD1 not found")
    sys.exit(1)
content = content.replace(OLD1, NEW1, 1)
print("Fix 1: window class updated")

# Apply fix 2
if OLD2 not in content:
    print("ERROR: OLD2 not found")
    idx = content.find(b"Step 4: Ctrl+S to open")
    if idx >= 0:
        print(f"Found 'Step 4' at {idx}: {content[idx:idx+200]!r}")
    sys.exit(1)
content = content.replace(OLD2, NEW2, 1)
print("Fix 2: save dialog logic replaced")

with open(filepath, "wb") as f:
    f.write(content)
print("Done.")
