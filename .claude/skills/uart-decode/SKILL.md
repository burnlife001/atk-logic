---
name: uart-decode
description: Decode UART/RS232 serial data from ATK-Logic .atkdl capture files. Use when user asks to analyze UART, serial port, RS232, or raw capture data.
---

# UART 协议解码

对 `.atkdl` 采集文件中的 UART / RS-232 信号进行解码和分析。

## 已知约定

- 波特率固定：**115200**（8N1，idle-high，LSB-first）
- 信号默认在 **CH0**
- 文件名通常暗示数据内容（如 `uart_333.atkdl` → 发送 `"333\n"`）

## 基本命令

```bash
# 查看采集文件元信息
python cli/atk_cli.py info <文件路径>

# UART 解码（信号默认在 CH0）
python cli/atk_cli.py decode <文件路径> --decoder uart --rx 0 --option baudrate=115200

# 限制时间范围（避免数据量过大）
python cli/atk_cli.py decode <文件> --decoder uart --rx 0 --option baudrate=115200 --end 100ms

# 保留所有帧（含错误帧），用于信号质量排查
python cli/atk_cli.py decode <文件> --decoder uart --rx 0 --option baudrate=115200 --option drop_errors=false
```

## 分析流程

1. **运行解码**，输出 JSON，通过 `cli/_analyze.py` 分析：
   ```bash
   python cli/atk_cli.py decode <文件> --decoder uart --rx 0 --option baudrate=115200 2>/dev/null | python cli/_analyze.py
   ```

2. **分析输出**关注：
   - `Total frames`：总解码帧数
   - `Unique bytes`：唯一字节值（判断数据类型）
   - `Pattern`：重复模式（确认数据内容）
   - `Error frames`：错误帧数（0 = 信号质量好）
   - `Top byte counts`：字节分布（寻找噪音/异常值）

3. **信号质量排查**（错误帧 > 0）：
   - 先加 `--option drop_errors=false` 查看错误帧详情
   - 检查 `_dump_edges.py` 查看原始边缘事件
   - 确认是否波特率不对、信号有毛刺、或采集起始截断

## 辅助脚本

- `cli/_analyze.py` — 解析 decode JSON 输出，统计帧数/唯一字节/重复模式/错误
- `cli/_dump_frames.py` — 逐帧打印解码结果（start/bit/data/stop）
- `cli/_dump_edges.py` — 导出原始边缘事件，检查信号电平时序
- `cli/_check_ch.py` — 快速扫描所有通道，确定哪个通道有信号

## UART 选项参考

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `baudrate` | 115200 | 波特率 |
| `data_bits` | 8 | 数据位 5-9 |
| `parity` | none | 校验：none/even/odd/mark/space |
| `stop_bits` | 1 | 停止位：1/1.5/2 |
| `bit_order` | lsb_first | 位序 |
| `polarity` | 0 | 0=idle high（标准TTL），1=idle low（RS-232） |
| `drop_errors` | true | 丢弃 stop bit 错误帧 |
