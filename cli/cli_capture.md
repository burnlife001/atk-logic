## CLI 采集方案对比

| 维度 | GUI 方案 | 直接 CLI 方案 |
|------|---------|------------|
| **实现方式** | CLI 通过 socket/pipe 向 GUI 发指令，GUI 执行采集并保存 .atkdl | CLI 通过 libusb/pyusb 直接控制 USB 硬件 |
| **可行性** | ✅ 需要修改 GUI C++ 代码，增加 IPC 服务端 | ❌ `libusb-package` 的 `winusbx_open` 被 WinUSB 驱动拒绝 (ERROR_ACCESS_DENIED) |
| **驱动兼容** | ✅ 依赖 GUI 已有的 libusbK/WinUSB 驱动，已验证可用 | ❌ libusb-package 的 libusb-1.0 DLL 与 ATK 设备的 WinUSB 驱动栈不兼容 |
| **代码量** | C++ ~200行 (socket 服务端) + Python ~100行 (客户端) | 已完成 ~400 行 (`atk_capture.py`)，但无法跑通 |
| **维护成本** | 低 — 硬件控制逻辑不变，复用 GUI 的 USB 层 | 高 — 需要持续维护 libusb 兼容性 |
| **多进程共用** | ✅ 可以共存，CLI 和 GUI 同时运行 | ❌ Windows 上 WinUSB 设备只能被一个进程独占 |
| **操作方式** | `capture start` → GUI 采集 → 完成后通知 CLI | `capture start` → 直连设备 → 读取数据 |
| **独立性** | ❌ 依赖 GUI 运行 | ✅ 无 GUI 依赖 |
| **已测试部分** | 无 | CRC32、交织/解交织、协议帧解析 → ✅ 均通过单元测试 |

---

### 结论

**直接 CLI 方案不可行** — `libusb-package` 的 libusb-1.0 DLL 无法打开 ATK 设备的 WinUSB 驱动。这不是代码 bug，是 libusb-package 与 WinUSB 的兼容性限制，且 Windows 上设备同一时间只能被一个进程打开。

**GUI 方案是唯一可行的路径** — 需要在 ATK-Logic.exe 里加一个本地 socket 服务，接收 `START` / `STOP` 指令，CLI 通过 socket 发送命令。硬件控制和驱动兼容性全部由 GUI 已有的 USB 层处理。
