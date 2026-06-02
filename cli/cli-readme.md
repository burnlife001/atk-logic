# ATK-Logic CLI

Logic analyzer 命令行工具，用于读取 `.atkdl` / `.bin` 采集文件、查看元数据、导出波形边缘事件、以及运行协议解码器。

## 环境要求

- **Windows** (x86-64)
- **Python 3.10+**（内置解码器 **uart / i2c / spi** 无需特定版本）
- **Python 3.14** + **libsigrokdecode-4.dll**（仅非内置解码器需要，如 `ac97`）
- 零外部 Python 依赖（纯标准库）

> 内置解码器（`atk_proto.py`）基于 RLE 边缘事件直接解码，无需展开稠密采样数组，比 DLL 路径更快更省内存。

## 架构

```
cli/
  python3.14.exe       Go 编写的启动器，加载 Python 3.14 DLL 并执行脚本
  _bootstrap.py        DLL 搜索路径初始化（将 lib/bin/ 加入 os.add_dll_directory）
  atk_cli.py           命令行入口（argparse，5 个子命令）
  atk_reader.py        采集文件读取器（atkdl / bin 格式，RLE 边缘事件）
  atk_proto.py         内置原生协议解码器（UART / I2C / SPI，纯 Python，无依赖）
  atk_decoder.py       协议解码桥接（ctypes 封装 libsigrokdecode-4.dll，仅非内置解码器）
  pylauncher/          python3.14.exe 的 Go 源码
  tests/               测试文件
```

运行流程：
- **内置解码器**：`python` → `atk_cli.py` → `atk_proto.py`（RLE 边缘事件直接解码，无需 DLL）
- **DLL 解码器**：`python3.14.exe` → `_bootstrap.py` → `atk_cli.py` → `atk_decoder.py` → `libsigrokdecode-4.dll`

## 支持的文件格式

| 格式 | 后缀 | 说明 |
|------|------|------|
| ATKDL | `.atkdl` | ZIP 压缩，内含 channel.ini 元数据 + 各通道二进制数据块 |
| 原始二进制 | `.bin` | 64 字节头 + 通道交织/独立原始位数据 |

## 子命令

### info — 查看文件元数据

```bash
python3.14.exe atk_cli.py --format json info <文件路径>
```

输出字段：`channels`（通道 ID/名称）、`sample_rate_hz`（采样率）、`total_samples`（总采样数）、`duration_ns`（持续时间 ns）、`capture_time`、`file_format`.

`--format` 可选 `json`（默认）或 `text`.

### capture — 控制硬件采集（需要 GUI 运行）

```bash
# 开始采集（需要 ATK-Logic.exe 已启动）
python atk_cli.py capture start --ch 0 --duration 5s --output data/cap.atkdl

# 停止当前采集
python atk_cli.py capture stop
```

采集命令通过 TCP socket（127.0.0.1:9876）向运行中的 ATK-Logic GUI 发送指令，
GUI 负责 USB 硬件控制和 .atkdl 文件保存。CLI 不直接操作 USB 设备。

参数：

| 参数 | 说明 |
|------|------|
| `--ch` | 通道编号，默认 0 |
| `--duration` | 采集时长，带单位（如 `5s`、`100ms`），默认 `5s` |
| `--sample-rate-hz` | 采样率 Hz，默认 20000000（20 MHz） |
| `--threshold` | 逻辑电平阈值（V），默认 1.5 |
| `--rle` | 启用 FPGA RLE 压缩 |
| `--output` / `-o` | 输出 .atkdl 路径，默认 `data/capture_<timestamp>.atkdl` |

### export — 导出通道边缘事件

```bash
python3.14.exe atk_cli.py export <文件> --ch 0,1,2 [--start 0] [--end 1ms] [--max-events 10000]
```

参数：

| 参数 | 说明 |
|------|------|
| `--ch` | 通道 ID，逗号分隔（如 `0,2,3`） |
| `--start` | 起始时间，支持 `ns`/`us`/`ms`/`s` 单位，默认 `0` |
| `--end` | 结束时间，同上 |
| `--max-events` | 最大输出事件数，默认 10000 |

输出每个通道的边缘事件列表：`t_ns`（发生时间）、`level`（电平 0/1）、`dur_ns`（持续时长）。

### list-decoders — 列出可用协议解码器

```bash
python atk_cli.py list-decoders [--filter uart,i2c]
```

- `--filter`：按解码器 ID 过滤，逗号分隔
- **内置解码器始终可用**（无需 DLL），DLL 解码器仅在 Python 3.14 下追加显示
- 内置解码器标记 `(native)`，DLL 解码器标记 `(libsigrokdecode)`

每个解码器输出：`id`、`name`、`desc`、`channels`（必需通道）、`opt_channels`（可选通道）、`options`（可配置参数）。

### decode — 运行协议解码

```bash
# 内置解码器（任何 Python 3.10+）
python atk_cli.py decode <文件> \
  --decoder uart \
  --rx 0 \
  --option baudrate=115200

# 非内置解码器（需要 python3.14.exe + DLL）
python3.14.exe atk_cli.py decode <文件> \
  --decoder ac97 \
  --sync 0 --clk 1
```

参数：

| 参数 | 说明 |
|------|------|
| `--decoder` | 解码器 ID（必填），如 `uart`、`i2c`、`spi` |
| `--rx` / `--tx` | 通道映射（UART） |
| `--scl` / `--sda` | 通道映射（I²C） |
| `--clk` / `--mosi` / `--miso` / `--cs` | 通道映射（SPI） |
| `--option` | 解码器选项，`key=value` 格式，可多次指定 |
| `--start` / `--end` | 时间范围 |
| `--max-events` | 最大边缘事件数，默认 100000 |

**解码路径选择**：内置解码器（uart/i2c/spi）走原生路径，输出 `"engine": "native"`；
其他解码器走 DLL 路径，输出 `"engine": "libsigrokdecode"`。

输出包含解码帧列表：`t_ns`（帧起始时间）、`type`（帧类型）、`data`（解码数据）、`errors`。

### capture — 控制硬件采集（需要 GUI 运行）

```bash
# 开始采集（需要 ATK-Logic.exe 已启动）
python atk_cli.py capture start --ch 0 --duration 5s --output data/cap.atkdl

# 停止当前采集
python atk_cli.py capture stop
```

采集命令通过 TCP socket（127.0.0.1:9876）向运行中的 ATK-Logic GUI 发送指令，
GUI 负责 USB 硬件控制和 .atkdl 文件保存。CLI 不直接操作 USB 设备。

参数：

| 参数 | 说明 |
|------|------|
| `--ch` | 通道编号，默认 0 |
| `--duration` | 采集时长，带单位（如 `5s`、`100ms`），默认 `5s` |
| `--sample-rate-hz` | 采样率 Hz，默认 20000000（20 MHz） |
| `--threshold` | 逻辑电平阈值（V），默认 1.5 |
| `--rle` | 启用 FPGA RLE 压缩 |
| `--output` / `-o` | 输出 .atkdl 路径，默认 `data/capture_<timestamp>.atkdl` |

## 时间格式

所有 `--start`/`--end` 参数支持带单位的时间字符串：

| 单位 | 示例 |
|------|------|
| 纳秒 (ns) | `100ns`、`100`（默认 ns） |
| 微秒 (us) | `1.5us` |
| 毫秒 (ms) | `2ms` |
| 秒 (s) | `1s` |

## 协议解码器

### 内置解码器（native，纯 Python）

无需 Python 3.14，无需 DLL，直接基于 RLE 边缘事件解码。

| ID | 名称 | 必需通道 | 可选通道 | 选项 |
|----|------|----------|----------|------|
| `uart` | UART (native) | — | `rx`, `tx` | `baudrate`, `data_bits`, `parity`, `stop_bits`, `bit_order`, `polarity`, `drop_errors` |
| `i2c` | I²C (native) | `scl`, `sda` | — | `addressing` |
| `spi` | SPI (native) | `clk` | `mosi`, `miso`, `cs` | `wordsize`, `bitorder`, `cpol`, `cpha`, `cs_polarity` |

**UART 选项说明**：

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `baudrate` | 115200 | 波特率 |
| `data_bits` | 8 | 数据位 5-9 |
| `parity` | none | 校验：none / even / odd / mark / space |
| `stop_bits` | 1 | 停止位：1 / 1.5 / 2 |
| `bit_order` | lsb_first | 位序：lsb_first / msb_first |
| `polarity` | 0 | 空闲电平：0=idle high（标准 TTL），1=idle low（RS-232 反转） |
| `drop_errors` | true | 丢弃有 stop bit 错误的帧（噪声导致的虚假起始位） |

别名：`rs232` / `serial` → `uart`，`twi` → `i2c`。

### DLL 解码器（libsigrokdecode）

需要 Python 3.14 + `libsigrokdecode-4.dll`，位于 `runtime/decoders/`。

| ID | 名称 | 必需通道 | 可选通道 | 典型选项 |
|----|------|----------|----------|----------|
| `uart` | UART | — | `rx`, `tx` | `baudrate`, `parity`, `data_bits`, `stop_bits` |
| `i2c` | I²C | `scl`, `sda` | — | `addressing` |
| `spi` | SPI | `clk` | `mosi`, `miso`, `cs` | `wordsize`, `bitorder` |
| `ac97` | AC '97 | `sync`, `clk` | `out`, `in`, `rst` | — |

> 注意：内置解码器与 DLL 解码器 ID 相同（uart/i2c/spi）。CLI 优先使用内置路径，输出 `"engine": "native"`。

完整列表通过 `list-decoders` 命令查看。

## 使用示例

```bash
# 查看采集文件基本信息（任何 Python 版本）
# 通过 GUI 进行硬件采集（需要 ATK-Logic.exe 已启动）
python atk_cli.py capture start --ch 0 --duration 5s --output data/cap.atkdl

python atk_cli.py --format text info capture.atkdl

# 导出通道 0 前 1ms 的边缘事件
python atk_cli.py export capture.atkdl --ch 0 --start 0 --end 1ms

# 查看可用解码器（内置 + DLL）
python atk_cli.py list-decoders --filter uart

# 内置 UART 解码：RX 接通道 0，115200/8N1
python atk_cli.py decode capture.atkdl --decoder uart --rx 0 --option baudrate=115200

# UART 反转信号（idle low / RS-232 电平）
python atk_cli.py decode capture.atkdl --decoder uart --rx 0 --option baudrate=115200 --option polarity=1

# 保留所有帧（含 stop bit 错误），用于信号质量排查
python atk_cli.py decode capture.atkdl --decoder uart --rx 0 --option drop_errors=false

# 内置 I²C 解码：SCL 通道 0, SDA 通道 1
python atk_cli.py decode capture.atkdl --decoder i2c --scl 0 --sda 1

# 内置 SPI 解码：CLK 通道 0, MOSI 通道 1, CS 通道 2
python atk_cli.py decode capture.atkdl --decoder spi --clk 0 --mosi 1 --cs 2

# 非内置解码器（需 python3.14.exe）
python3.14.exe atk_cli.py decode capture.atkdl --decoder ac97 --sync 0 --clk 1
```

## 输出格式

全局 `--format` 参数控制输出格式：

- `json`（默认）：机器可读的 JSON
- `text`：人类可读的 key: value 格式
