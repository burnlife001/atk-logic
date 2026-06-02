# CLI 采集数据 UART 帧错误率高 (50%+) 问题 — 已解决

## 现象

CLI (`atk_cli.py capture`) 采集的 `.atkdl` 文件，用 UART 解码器解码时错误率 ~50-55%。
GUI 直采的同信号文件错误率 <1%。

| 文件 | 采集方式 | UART 帧错误率 | 边缘密度 |
|------|---------|---------------|---------|
| `uart_1111.atkdl` | GUI 直采 | 0.0% | 173 edges/ms |
| `uart_333.atkdl` | GUI 直采 | 0.1% | 173 edges/ms |
| `uart_2222.atkdl` | GUI 直采 | 0.8% | 173 edges/ms |
| CLI 采集 (修复前) | TCP→GUI | **50-55%** | **~2830 edges/ms** |
| **CLI 采集 (修复后)** | TCP→GUI | **0.0%** | **162 edges/ms** |

## 根因 #1: `selectHzIndex = 0` → FPGA PLL 配置错误

CLI 代码 (`thread_cmd.cpp`) 硬编码 `selectHzIndex = 0`，传给 FPGA 寄存器 `setArray[2] = 1`，
对应 1 MHz 时钟。但 `setHz` 设为 20000000 (20 MHz)。FPGA PLL 与元数据相差 20 倍，
导致亚稳态采样和大量毛刺 — raw bytes 中出现 `0x80`, `0xFE`, `0xF8` 等混合值。

**修复**: 添加 `mapSampleRateToHzIndex()` 函数，动态映射采样率到 FPGA 支持的最接近频率。

## 根因 #2: SessionController 创建策略

CLI 需要设备 SessionController 才能采集。QML 不保证自动创建设备会话（需用户交互）。

**修复**: CmdServer 优先复用 QML SessionController（避免 USB 端口竞争），
若不存在则自行创建 CLi-owned SessionController。

## 已排查并排除的假设

| 假设 | 结论 |
|------|------|
| RLE 未开启 | 排除 — 边缘密度不降不是 RLE 的问题 |
| Buffer vs Stream 模式 | 排除 |
| 通道使能配置 | 排除 |
| 即时触发 vs 等待触发 | 排除 |
| 保存阶段 `set.ini` 缺失 | 已修复 — 添加空文件创建逻辑 |

## 最终修改文件

`pv/thread/thread_cmd.cpp`:
- 新增 `mapSampleRateToHzIndex()` — 采样率 → FPGA 频率索引映射
- `handleStart()` 调用映射函数，`selectHzIndex` 和 `setHz` 保持一致
- QML SessionController 复用 + 自建 fallback

`pv/thread/thread_cmd.h`:
- 新增 `m_ownController` 成员

## 测试结果 (2026-06-02)

```
$ python atk_cli.py capture start --ch 0 --duration 3s --output data/cli_test_002.atkdl
Capture complete!
  File: E:\__electric\atk-logic\data\cli_test_002.atkdl
  Rate: 20 MHz / Duration: 3.0s

Edge density: 161.9 edges/ms (GUI: 173 edges/ms)
Glitches (<40ns pulse): 0 / 485,836 = 0.00%
UART decode: 6,484 frames, 0 errors
```
