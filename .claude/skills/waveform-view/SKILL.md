---
name: waveform-view
description: Observe and measure generic waveforms — LED blink patterns, PWM duty/frequency, signal timing, digital pulse trains — from ATK-Logic .atkdl capture files.
---

# 通用波形观察

对 `.atkdl` 采集文件中的数字信号进行通用观察：边沿统计、频率/周期测量、占空比分析。适用于 LED 闪烁、PWM、方波、脉冲等非协议信号。

## 采集命令

```bash
# 从 USB 设备采集波形（默认 20MHz/5s/CH0/1.5V）
python cli/atk_cli.py capture start --duration 5s --output data/test.atkdl

# 采集带自定义参数
python cli/atk_cli.py capture start --ch 0 --duration 10s --threshold 2.0 -o data/led.atkdl

# 停止采集
python cli/atk_cli.py capture stop
```

采集参数：
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--ch` | 0 | 通道号 |
| `--duration` | 5s | 采集时长 |
| `--sample-rate-hz` | 20000000 | 采样率（Hz） |
| `--threshold` | 1.5 | 逻辑阈值电压 (V) |
| `--output / -o` | data/capture_<时间戳>.atkdl | 输出文件路径 |

## 基本命令

```bash
# 查看采集文件元信息
python cli/atk_cli.py info <文件路径>

# 导出通道边缘事件（raw edges）
python cli/atk_cli.py export <文件> --ch 0 --start 0 --end 100ms

# 扫描所有通道，确定信号所在通道
python cli/_check_ch.py <文件路径>
```

## 分析流程

### 1. 确定信号通道

```bash
python cli/_check_ch.py <文件路径>
```
输出每个通道的边缘事件数量，边缘最多的通道即信号通道。

### 2. 导出边缘事件

```bash
python cli/atk_cli.py export <文件> --ch <N> --end 100ms
```

输出每条边缘：`t_ns`（发生时间 ns）、`level`（电平 0/1）、`dur_ns`（持续时长 ns）。

### 3. 计算波形参数

从边缘事件中提取：

- **频率**：`f = 1e9 / (相邻同向边缘时间差)` 即 `1e9 / period_ns`
- **周期**：两个相邻上升沿（或下降沿）的时间差
- **占空比**：`高电平时长 / 周期 × 100%`
- **脉宽**：单次高/低电平的 `dur_ns`

对于周期性信号，取多个周期的平均值以获得准确结果。

### 4. 常见场景

| 场景 | 关注指标 | 典型参数 |
|------|---------|---------|
| LED 闪烁 | 闪烁频率、亮灭时间比 | 1-10 Hz，占空比 50% |
| PWM 调光 | 频率、占空比 | 100 Hz - 10 kHz |
| 舵机 PWM | 脉宽（高电平时间） | 500-2500 us，50 Hz |
| 方波/时钟 | 频率、抖动（周期标准差） | 1 kHz - 100 MHz |
| 按键/GPIO | 按下/释放时间、抖动脉冲 | ms 级别，可能有毛刺 |

### 5. 信号质量检查

- **毛刺检测**：< 100ns 的极窄脉冲通常是噪声
- **抖动**：周期标准差 / 平均周期 = 抖动率，< 1% 为正常
- **缺失脉冲**：比较相邻周期，差异 > 20% 标记为异常

## Python 内联分析示例

在 bash 中直接用 Python 分析导出数据：

```bash
# 统计电平持续时长
python cli/atk_cli.py export <文件> --ch 0 --end 50ms | python -c "
import sys, json
edges = json.load(sys.stdin)['channels']['0']
for e in edges[:20]:
    print(f't={e[\"t_ns\"]:10d} ns  level={e[\"level\"]}  dur={e[\"dur_ns\"]} ns')
"

# 计算 PWM 频率和占空比
python cli/atk_cli.py export <文件> --ch 0 --end 50ms | python -c "
import sys, json
edges = json.load(sys.stdin)['channels']['0']
periods = []
duties = []
for i in range(1, len(edges)-1):
    if edges[i]['level'] == 0 and edges[i+1]['level'] == 1:
        # rising edge at i+1
        high = edges[i]['dur_ns']
        total = edges[i-1]['dur_ns'] + high if i > 0 else high + edges[i+1]['dur_ns']
        period = edges[i+1]['t_ns'] - edges[i-1]['t_ns']
        if period > 0:
            freq = 1e9 / period
            duty = edges[i]['t_ns'] - edges[i-1]['t_ns']  # high time
            periods.append(period)
            duties.append(duty / period * 100)
if periods:
    print(f'Frequency: {1e9 / (sum(periods)/len(periods)):.1f} Hz')
    print(f'Duty cycle: {sum(duties)/len(duties):.1f}%')
"
```

## 采集参数参考

所有 `.atkdl` 文件统一参数：
- **采样率**：20 MHz（20,000,000 samples/s）
- **时间精度**：50 ns（1 个采样周期）
- **采集时长**：通常 60 秒
- **通道数**：16（CH0-CH15）
