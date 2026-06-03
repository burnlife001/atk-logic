import sys

NEW_BLOCK = b"""        /* Step 4: Dismiss any leftover dialog, then Ctrl+S = direct save (no dialog) */
        dbg_log("start: dismissing any dialog with Escape...");
        focus_window();
        Sleep(200);
        keybd_event(VK_ESCAPE, 0, 0, 0); Sleep(30);
        keybd_event(VK_ESCAPE, 0, KEYEVENTF_KEYUP, 0);
        Sleep(300);
        dbg_log("start: sending Ctrl+S to save directly...");
        focus_window();
        Sleep(200);
        send_mod_combo(VK_CONTROL, 0, 'S');
        dbg_log("start: Ctrl+S sent, waiting for GUI to save...");
        Sleep(2000);

        /* Send final progress */
        {
            int len = build_response(resp, BUF_SIZE, "progress", "phase", "save", "schedule", "100");
            send(s, resp, len, 0);
        }

        /* Step 5: find saved file and copy to output */
        if (output[0]) {
            int file_saved = 0;
            const char *doc_path = "C:/Users/yg/Documents/";

            /* Extract filename from output path */
            const char *filename = output;
            {
                const char *p = output;
                while (*p) { if (*p == '\\\\' || *p == '/') filename = p + 1; p++; }
            }

            /* Build source path: Documents/<filename> */
            char src_path[520];
            {
                int i = 0;
                const char *dp = doc_path;
                while (*dp && i < 510) src_path[i++] = *dp++;
                const char *fn = filename;
                while (*fn && i < 510) src_path[i++] = *fn++;
                src_path[i] = 0;
            }

            /* Convert to wide */
            {
                int k = 0;
                while (src_path[k] && k < 510) { g_w_src[k] = (WCHAR)(unsigned char)src_path[k]; k++; }
                g_w_src[k] = 0;
            }
            {
                int k = 0;
                while (output[k] && k < 510) { g_w_dst[k] = (WCHAR)(unsigned char)output[k]; k++; }
                g_w_dst[k] = 0;
            }

            dbg_log("start: looking for saved file...");

            /* First try the expected filename at Documents path */
            DWORD attr = GetFileAttributesW(g_w_src);
            if (attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY)) {
                /* Check file size is reasonable (not the old 12KB stub) */
                WIN32_FILE_ATTRIBUTE_DATA fad;
                if (GetFileAttributesExW(g_w_src, GetFileExInfoStandard, &fad)) {
                    ULONGLONG fsize = ((ULONGLONG)fad.nFileSizeHigh << 32) | fad.nFileSizeLow;
                    if (fsize > 100000) { /* must be >100KB for valid 2s capture */
                        dbg_log("start: valid file found in Documents, copying to output...");
                        if (copy_file_w(g_w_src, g_w_dst)) {
                            dbg_log("start: copy SUCCESS");
                            DeleteFileW(g_w_src);
                            int len = build_response(resp, BUF_SIZE, "ok", "file", output, NULL, NULL);
                            send(s, resp, len, 0);
                            file_saved = 1;
                        } else {
                            dbg_log("start: copy FAILED, using Documents path");
                            char utf8_path[512];
                            WideCharToMultiByte(CP_UTF8, 0, g_w_src, -1, utf8_path, 511, NULL, NULL);
                            int len = build_response(resp, BUF_SIZE, "ok", "file", utf8_path, NULL, NULL);
                            send(s, resp, len, 0);
                            file_saved = 1;
                        }
                    } else {
                        dbg_log("start: file too small, ignoring stale file");
                    }
                }
            }

            /* If not found by expected name, search for newest .atkdl in Documents */
            if (!file_saved) {
                WIN32_FIND_DATAW fd;
                WCHAR search_pattern[320];
                {
                    const WCHAR *dp_w = L"C:/Users/yg/Documents/";
                    int j = 0;
                    while (*dp_w && j < 310) search_pattern[j++] = *dp_w++;
                    search_pattern[j++] = '*'; search_pattern[j++] = '.';
                    search_pattern[j++] = 'a'; search_pattern[j++] = 't';
                    search_pattern[j++] = 'k'; search_pattern[j++] = 'd';
                    search_pattern[j++] = 'l'; search_pattern[j] = 0;
                }

                HANDLE hf = FindFirstFileW(search_pattern, &fd);
                if (hf != INVALID_HANDLE_VALUE) {
                    FILETIME best_time = {0};
                    WCHAR best_file[260] = {0};
                    do {
                        if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                            if (CompareFileTime(&fd.ftCreationTime, &best_time) > 0) {
                                best_time = fd.ftCreationTime;
                                int jj = 0;
                                while (fd.cFileName[jj] && jj < 259) { best_file[jj] = fd.cFileName[jj]; jj++; }
                                best_file[jj] = 0;
                            }
                        }
                    } while (FindNextFileW(hf, &fd));
                    FindClose(hf);

                    if (best_file[0]) {
                        WCHAR full_src[520];
                        {
                            const WCHAR *dp_w2 = L"C:/Users/yg/Documents/";
                            int jj = 0;
                            while (*dp_w2 && jj < 510) full_src[jj++] = *dp_w2++;
                            const WCHAR *bf = best_file;
                            while (*bf && jj < 510) full_src[jj++] = *bf++;
                            full_src[jj] = 0;
                        }

                        dbg_log("start: found newest file, copying...");
                        if (copy_file_w(full_src, g_w_dst)) {
                            dbg_log("start: copy SUCCESS");
                            DeleteFileW(full_src);
                            int len = build_response(resp, BUF_SIZE, "ok", "file", output, NULL, NULL);
                            send(s, resp, len, 0);
                            file_saved = 1;
                        } else {
                            dbg_log("start: copy FAILED");
                            char utf8_path[512];
                            WideCharToMultiByte(CP_UTF8, 0, full_src, -1, utf8_path, 511, NULL, NULL);
                            int len = build_response(resp, BUF_SIZE, "ok", "file", utf8_path, NULL, NULL);
                            send(s, resp, len, 0);
                            file_saved = 1;
                        }
                    }
                }
            }

            /* Also check output path directly */
            if (!file_saved) {
                DWORD attr2 = GetFileAttributesW(g_w_dst);
                if (attr2 != INVALID_FILE_ATTRIBUTES && !(attr2 & FILE_ATTRIBUTE_DIRECTORY)) {
                    dbg_log("start: file found at output path directly");
                    int len = build_response(resp, BUF_SIZE, "ok", "file", output, NULL, NULL);
                    send(s, resp, len, 0);
                    file_saved = 1;
                }
            }

            if (!file_saved) {
                dbg_log("start: file NOT FOUND after Ctrl+S save");
                int len = build_response(resp, BUF_SIZE, "error", "msg", "Ctrl+S save did not produce a valid file", NULL, NULL);
                send(s, resp, len, 0);
            }
        } else {
            /* No output path specified */
            int len = build_response(resp, BUF_SIZE, "ok", "msg", "capture complete (no output path)", NULL, NULL);
            send(s, resp, len, 0);
        }

"""

filepath = "E:/__electric/atk-logic/proxy_dll/proxy_main.c"

with open(filepath, "rb") as f:
    content = f.read()

# Find markers
old_start = content.find(b"Step 4: Ctrl")
if old_start < 0:
    print("ERROR: 'Step 4: Ctrl' not found")
    sys.exit(1)

old_end = content.find(b"InterlockedExchange(&g_capturing, 0)", old_start)
if old_end < 0:
    print("ERROR: 'InterlockedExchange' not found")
    sys.exit(1)

print(f"Replacing bytes {old_start} to {old_end} ({old_end - old_start} bytes)")
print(f"With new block ({len(NEW_BLOCK)} bytes)")

new_content = content[:old_start] + NEW_BLOCK + content[old_end:]

with open(filepath, "wb") as f:
    f.write(new_content)

print("Done.")
