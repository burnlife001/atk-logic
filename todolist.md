# DLL Proxy Injection for Official ATK-Logic

## Goal (COMPLETED 2026-06-03)

Inject TCP CLI server (port 9876) into the official closed-source ATK-Logic.exe
via DLL proxying.

## Tasks

- [x] 1. Generate Qt5Network.dll proxy export list (.def file)
- [x] 2. Implement proxy DLL with WinSock TCP server + JSON protocol
- [x] 3. Build proxy DLL with MSVC (x64)
- [x] 4. Deploy to official ATK-Logic directory and test capture

## Architecture

```
ATK-Logic.exe
  └── Qt5Network.dll (proxy, 218KB)
        ├── DllMain → WinSock TCP server on :9876
        ├── 1506 exports → Qt5Network_real.dll
        ├── JSON: {"cmd":"start"/"stop"/"status"/"file"}
        ├── F1=start, F2=stop, Ctrl+Shift+S=save
        └── dialog detection + paste path + Enter
```

## Status

| Component | Status |
|-----------|--------|
| DLL build & deploy | Done |
| TCP server (port 9876) | Working |
| JSON protocol (status/stop) | Working |
| F1/F2 capture trigger | Working (confirmed via temp/memory) |
| Ctrl+Shift+S save dialog | Not reliably detected |
| End-to-end CLI capture | Partial (capture triggers but save fails) |

## Known Issues
- Save dialog (Ctrl+Shift+S) not reliably detected — need `AttachThreadInput` refinement
- Both official and repo builds have FPGA capture stuck at 1% issue

## Portable Tool Assets

Created `~/.claude/atk-logic-tools/` for waveform analysis from any directory:
- `atk_wave.py` — universal waveform analyzer
- `atk_decode.py` — protocol decoder wrapper
- `atk_reader.py` + `atk_proto.py` — core libraries (zero deps)
