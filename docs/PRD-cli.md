# ATK-Logic CLI — PRD

## 1. 目标

为 ATK-Logic 逻辑分析仪构建一个 **纯 Python CLI**，让 AI（LLM Agent）可以通过 shell 直接读取、分析、解码逻辑分析仪数据。

## 2. 用户场景

1. **AI 辅助调试**：开发者把 `.atk` session 文件丢给 AI，AI 调 CLI 看波形、跑解码、定位异常帧
2. **批量分析**：脚本批量处理多个 session，提取关键时序数据
3. **远程诊断**：CLI 部署在实验室机器上，通过 SSH 远程调用

## 3. 架构

```
┌──────────────────────────────────┐
│  AI Agent                        │
│    调 shell: atk-cli info ...    │
├──────────────────────────────────┤
│  atk-cli (Python CLI)            │
│    ├── atk_reader.py             │
│    ├── atk_decoder.py  (ctypes)  │
│    └── atk_condition.py          │
├──────────────────────────────────┤
│  atk_decoder.dll (C, 132 PDs)    │
└──────────────────────────────────┘
```

## 4. CLI 命令定义

每个命令一个动词，JSON 输出到 stdout，日志/进度到 stderr。

### 4.1 `info`
**一句话**：这个文件里录了什么？

```bash
atk-cli info capture.atk
# → {
#     channels: [{id: 0, name: "UART TX"}, {id: 1, name: "UART RX"}, ...],
#     sample_rate_hz: 100000000,
#     total_samples: 50000000,
#     duration_ns: 500000000,
#     capture_time: "2026-05-29T10:00:00",
#     file_format: "source"
#   }
```

### 4.2 `export`
**一句话**：拉指定通道在时间段内的电平变化序列。

```bash
atk-cli export capture.atk --ch 0,2 --start 100us --end 500us --max-events 10000
# → {
#     channels: {
#       "0": [
#         {t_ns: 0, level: 1, dur_ns: 10400},
#         {t_ns: 10400, level: 0, dur_ns: 86800},
#         ...
#       ],
#       "2": [...]
#     }
#   }
```

输出的是**边沿变化**序列（RLE 压缩），不是逐采样点的原始数据。每个事件记录 "从 t_ns 开始，电平变为 level，持续了 dur_ns"。

### 4.3 `list-decoders`
**一句话**：有哪些协议解码器可用？

```bash
atk-cli list-decoders --filter uart,i2c,spi
# → [
#     {id: "uart", name: "UART", desc: "...", channels: [...], options: [...]},
#     {id: "i2c", name: "I2C", ...},
#   ]
```

### 4.4 `decode`
**一句话**：把波形翻译成协议帧。

```bash
atk-cli decode capture.atk --decoder uart --rx 0 --tx 1 --baudrate 115200 --start 100us --end 10ms
# → {
#     decoder: "uart",
#     frames: [
#       {t_ns: 10400, type: "rx-data", data: {value: 0x48, text: "H"}, errors: []},
#       {t_ns: 96150, type: "rx-data", data: {value: 0x65, text: "e"}, errors: []},
#       ...
#     ],
#     stats: {total_frames: 500, error_frames: 2}
#   }
```

`--rx 0` 意思是把 decoder 定义的 `rx` 通道映射到物理通道 0。支持的 channel 名和 options 名由 `list-decoders` 返回。

### 4.5 `search`
**一句话**：按时序条件搜索信号片段。

```bash
atk-cli search capture.atk --condition "rising(CH0) && CH1==1" --start 0 --end 10ms --limit 100
# → {
#     condition: "rising(CH0) && CH1==1",
#     matches: [
#       {t_ns: 10400, channels: {CH0: 1, CH1: 1}},
#     ]
#   }
```

条件语法（参考 waveform-mcp）：
| 表达式 | 含义 |
|--------|------|
| `rising(CH0)` | CH0 上升沿 |
| `falling(CH0)` | CH0 下降沿 |
| `CH0 == 1` | CH0 高电平 |
| `CH0 == 0` | CH0 低电平 |
| `rising(CH0) && CH1 == 1` | CH0 上升沿 且 CH1 为高 |
| `CH0` | CH0 当前值 |

### 4.6 `measure`
**一句话**：自动测量频率、占空比、脉冲宽度。

```bash
atk-cli measure capture.atk --ch 0 --start 0 --end 10ms
# → {
#     frequency_hz: 1000000,
#     duty_cycle_pct: 50.2,
#     pulse_width_ns: 500,
#     period_ns: 1000,
#     rise_count: 500,
#     fall_count: 500
#   }
```

## 5. 全局参数

所有命令通用：
- `--format json|text` 输出格式，默认 `json`
- 时间参数支持后缀：`ns`, `us`, `ms`, `s`（如 `100us`, `10ms`）
- 日志/进度输出到 stderr，JSON 结果输出到 stdout

## 6. 实现计划

### Phase 0: 文件读取 (`atk_reader.py`) — P0

读 ATK-Logic 的文件格式，统一返回边沿事件流。

```python
class CaptureReader:
    def get_info(self) -> CaptureInfo
    def read_edges(self, channel: int, start_ns: int, end_ns: int, max_events: int = 10000) -> list[Event]
```

支持格式：
- **Source 文件** (.atk zip)：内部是 JSON 元数据 + Bin 数据，直接读 Segment 序列化
- **Bin 文件** (ns/sample 两种)：头 64 bytes 是元数据，后面是位数据
- **CSV 文件**：简单文本解析

优先实现 Source 格式（GUI 默认保存格式）。

### Phase 1: 解码器桥接 (`atk_decoder.py`) — P0

ctypes 封装 `atk_decoder.dll`：

```python
class DecoderBridge:
    def init(self, decoders_path)           # atk_decoder_init
    def list_decoders(self) -> list[DecoderInfo]
    def decode(self, decoder_id, channels, options,
               edge_events, sample_rate) -> list[Frame]
    def close()                            # atk_decoder_exit
```

关键 API（ctypes → `atk_decoder.h`）：
- `atk_decoder_init(path)` — 设置 decoder/python/runtime 路径
- `atk_decoder_session_new()` → `atk_session*`
- `atk_decoder_get_by_id(id)` → `atk_decoder*`（含 channels/options 元数据）
- `atk_decoder_inst_new(sess, id, options)`
- `atk_decoder_inst_channel_set_all(di, channels)`
- `atk_decoder_pd_output_callback_add(sess, ANN, cb, py_obj)` — 注册回调收集帧
- `atk_decoder_session_metadata_set_samplerate(sess, sr)`
- `atk_decoder_session_send(sess, start, end, inbuf)` — 喂样本数据
- `atk_decoder_session_send_eof(sess)` — 通知结束
- `atk_decoder_session_destroy(sess)` — 清理

> **注意**：`atk_decoder.dll` 内嵌 Python C API，运行时需要 `python3.dll` + `decoders/` 目录。确保 Python 版本与 DLL 编译时一致。

### Phase 2: CLI 入口 (`atk_cli.py`) — P1

click 命令骨架 + 6 个子命令，直接调用 Phase 0-1 的模块。

### Phase 3: 高阶功能 — P2

- **`search` 条件解析器**：参考 waveform-mcp 的 LALRPOP 语法，实现时序表达式
- **堆叠解码**：`--stack uart:rx=0:tx=1 --stack modbus` → 物理层 + 协议层
- **多 session 对比**：`atk-cli diff session1.atk session2.atk --ch 0`

## 7. 技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.12+ | AI 生态、ctypes 直调 DLL |
| CLI 框架 | `click` | 成熟稳定，声明式参数 |
| 时间单位 | ns (内部统一) | 与 C++ 代码一致，整数无精度问题 |
| 输出格式 | JSON (default), Text (`--format text`) | JSON 给 AI/脚本, Text 给人 |
| 无状态 | 每次调用独立，自带 path | 简单、AI 友好、无资源泄漏 |

## 8. 目录结构

```
atk-logic/
├── cli/                        # 新增 Python CLI
│   ├── pyproject.toml
│   ├── atk_reader.py           # 文件格式读取
│   ├── atk_decoder.py          # ctypes 解码器桥接
│   ├── atk_condition.py        # 条件表达式解析 (P2)
│   ├── atk_cli.py              # CLI 入口 (click)
│   └── tests/
│       ├── test_reader.py
│       └── test_decoder.py
├── pv/                         # 现有 C++ GUI
├── lib/                        # 现有 DLL / Python 库
├── runtime/decoders/           # 现有 132 解码器 PD
└── docs/
    └── PRD-cli.md              # 本文件
```

## 9. 风险

| 风险 | 缓解 |
|------|------|
| `atk_decoder.dll` 依赖嵌入式 Python，ctypes 调用时 Python 版本冲突 | 锁定 GUI 同版本 Python (3.12)，使用独立 venv |
| 132 解码器质量参差不齐 | 先支持高频协议 (UART/I2C/SPI/CAN)，其余按需验证 |
| Segment 的位压缩格式 (.atk zip 内部) 是私有格式 | 看 C++ `ThreadWork::SaveSourceFileThreadPara` 逆向读写逻辑 |
| Win 路径/编码问题 | 全部用 `pathlib.Path`，UTF-8 强制 |
