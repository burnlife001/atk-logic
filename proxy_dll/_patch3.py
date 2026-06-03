import sys

# Replace the Esc+Ctrl+S+dialog interaction block with a simple wait-for-autosave
OLD = b"""        /*         /* Step 4: Dismiss any leftover dialog, then Ctrl+S = direct save (no dialog) */
        dbg_log("start: dismissing any dialog with Escape...");
        focus_window();
        Sleep(200);
        keybd_event(VK_ESCAPE, 0, 0, 0); Sleep(30);
        keybd_event(VK_ESCAPE, 0, KEYEVENTF_KEYUP, 0);
        Sleep(300);
        dbg_log("start: sending Ctrl+S to open save dialog...");
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

NEW = b"""        /* Step 4: Wait for auto-save (saveMethod=1 in set.ini) */
        dbg_log("start: waiting for GUI auto-save after F2 stop...");
        /* GUI auto-saves .atkdl to savePath after capture stops.
         * Wait up to 10 seconds for the file to appear. */
        {
            int waited = 0;
            while (waited < 10000) {
                /* Check if a new .atkdl file appeared in Documents */
                WIN32_FIND_DATAW fd;
                WCHAR sp[320];
                {
                    const WCHAR *dp_w = L"C:/Users/yg/Documents/";
                    int j = 0;
                    while (*dp_w && j < 310) sp[j++] = *dp_w++;
                    sp[j++] = '*'; sp[j++] = '.'; sp[j++] = 'a';
                    sp[j++] = 't'; sp[j++] = 'k'; sp[j++] = 'd';
                    sp[j++] = 'l'; sp[j] = 0;
                }
                HANDLE hf = FindFirstFileW(sp, &fd);
                if (hf != INVALID_HANDLE_VALUE) {
                    ULARGE_INTEGER newest_time;
                    newest_time.QuadPart = 0;
                    WCHAR newest_file[260] = {0};
                    do {
                        if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                            ULARGE_INTEGER ft;
                            ft.LowPart = fd.ftCreationTime.dwLowDateTime;
                            ft.HighPart = fd.ftCreationTime.dwHighDateTime;
                            if (ft.QuadPart > newest_time.QuadPart) {
                                newest_time = ft;
                                int jj = 0;
                                while (fd.cFileName[jj] && jj < 259) { newest_file[jj] = fd.cFileName[jj]; jj++; }
                                newest_file[jj] = 0;
                            }
                        }
                    } while (FindNextFileW(hf, &fd));
                    FindClose(hf);

                    /* Check now for comparison */
                    FILETIME ft_now;
                    GetSystemTimeAsFileTime(&ft_now);
                    ULARGE_INTEGER now;
                    now.LowPart = ft_now.dwLowDateTime;
                    now.HighPart = ft_now.dwHighDateTime;

                    if (newest_time.QuadPart > 0 &&
                        (now.QuadPart - newest_time.QuadPart) < 120000000LL) { /* file created within last 12 seconds */
                        dbg_log("start: auto-save file found!");
                        break;
                    }
                }
                Sleep(500);
                waited += 500;
            }
        }"""

filepath = "E:/__electric/atk-logic/proxy_dll/proxy_main.c"

with open(filepath, "rb") as f:
    content = f.read()

if OLD not in content:
    print("ERROR: old string not found")
    # Find partial match
    for marker in [b"Step 4", b"dismissing any dialog", b"Ctrl+S sent"]:
        idx = content.find(marker)
        if idx >= 0:
            print(f"'{marker}' at {idx}: {content[idx:idx+120]!r}")
    sys.exit(1)

new_content = content.replace(OLD, NEW, 1)
print(f"OK. Old={len(OLD)} -> New={len(NEW)}")

with open(filepath, "wb") as f:
    f.write(new_content)
print("Done.")
