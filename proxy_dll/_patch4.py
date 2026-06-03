import sys

# Replace the auto-save wait block with: send Ctrl+S + launch uia_save.py + wait for file
OLD = b"""        /* Step 4: Wait for auto-save (saveMethod=1 in set.ini) */
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

NEW = b"""        /* Step 4: Ctrl+S to open QML save dialog, then use UIA to click Save */
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
                const char *prefix = "python E:/__electric/atk-logic/proxy_dll/uia_save.py ";
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

filepath = "E:/__electric/atk-logic/proxy_dll/proxy_main.c"

with open(filepath, "rb") as f:
    content = f.read()

if OLD not in content:
    print("ERROR: old string not found in file")
    # Find partial match
    for m in [b"Step 4", b"waiting for GUI auto-save", b"auto-save file found"]:
        idx = content.find(m)
        if idx >= 0:
            print(f"Found '{m.decode()}' at {idx}: {content[idx:idx+120]!r}")
    sys.exit(1)

new_content = content.replace(OLD, NEW, 1)
print(f"OK. Old={len(OLD)} -> New={len(NEW)} bytes")

with open(filepath, "wb") as f:
    f.write(new_content)
print("Done.")
