# ATK-Logic 二次开发环境搭建记录

## 当前状态

编译环境完整可用，Debug/Release 均已成功编译。USB 连接、固件升级、逻辑分析功能正常工作。

## 已完成的准备工作

### 1. Qt 开发环境
- Qt 5.15.2 MSVC2019 x64 → `D:\Programs\Qt\5.15.2\msvc2019_64`
- 安装方式：`aqtinstall`

### 2. MSVC 编译器
- Visual Studio 2026 Community → `D:\Programs\MSStudio`
- MSVC 14.51.36231 (C++ x64)

### 3. atk_libsigrokdecode (解码器库)
- **仓库**：`burnlife001/atk_libsigrokdecode` (fork from `alientek-openedv`)
- **构建方式**：GitHub Actions + MSYS2/MinGW
- **产物**：`libsigrokdecode-4.dll` + `sigrokdecode.lib` (MSVC import lib)
- **注意**：`atk_decoder.c` 通过 `--export-all-symbols` 导出符号到 DLL
- **运行时依赖**：`libpython3.14.dll`, `libglib-2.0-0.dll`, MinGW 运行时 DLL
- **Python stdlib**：`lib/python3.14/` (协议解码器需要，从 MSYS2 打包)

### 4. libusb-1.0 (USB 通信)
- 源码 `v1.0.28` 本地 MSBuild 编译
- 静态库：`lib/bin/libusb-1.0.lib`
- **修改**：`msvc/Configuration.Base.props` — 加入 VS 2026 (18.0) toolset 支持
- **修改**：`msvc/Base.props` — 关闭 TreatWarningAsError

### 5. 源码修改 (ATK-Logic.pro 及相关)
- `ATK-Logic.pro`：
  - 添加 `INCLUDEPATH += $$PWD/lib/include`
  - 添加 `LIBS += -L$$PWD/lib/bin -lsigrokdecode -llibusb-1.0`
  - 添加 `qtlockedfile_win.cpp` 到 SOURCES
- `main.cpp`：`QBreakpadHandler.h` include 加条件编译守卫
- `QBreakpadHandler.h`：创建 stub 头文件（项目根目录）
- `pv/static/atk_decoder.c`：已下载但**未**加入编译（依赖 GLib/Python MSVC 头文件，改为通过 DLL 导出符号）

### 6. 构建脚本
- **`build.ps1`**：一键构建 (qmake → nmake → windeployqt)
  ```powershell
  .\build.ps1              # Release
  .\build.ps1 -Build Debug # Debug
  ```

## 项目目录结构

```
E:\__electric\atk-logic\
├── build.ps1              # 一键构建脚本
├── ATK-Logic.pro          # Qt 工程文件
├── QBreakpadHandler.h     # 崩溃处理 stub
├── main.cpp               # 入口 (已修改 include 守卫)
├── lib/
│   ├── bin/               # sigrokdecode.lib, libusb-1.0.lib
│   ├── include/           # atk_decoder.h, libsigrokdecode.h, libusb.h, version.h
│   └── python3.14/        # Python 3.14 标准库 (运行时)
├── debug/                 # Debug 编译输出
│   ├── ATK-Logic.exe
│   └── lib/python3.14/    # 运行时 Python stdlib
└── release/               # Release 编译输出
    ├── ATK-Logic.exe
    └── lib/python3.14/
```

## 已解决问题：软件版本过低

### 现象
首次启动后固件自动更新完成，弹窗：「软件版本过低，请升级软件」。

### 根因
`connect.cpp:137` — 固件升级后通过 USB 返回 `minVersion=1108`，而代码中 `APP_VERSION_NUM=1066` 不满足要求。
完整链路：`CheckDeviceCreanInfo` → 读取 FPGA 数据 → `APP_VERSION_NUM(1066) < minVersion(1108)` → `SendDeviceCreanInfo(state=7)` → QML `showText[7]` = "软件版本过低"

### 修复
- `ATK-Logic.pro`: `VERSION = 1.2.2.0`, `APP_VERSION_NUM=1220` (> 固件要求 1108)
- `log_help.h/cpp`: 新增 `flush()` 方法，确保关键日志及时落盘
- `connect.cpp`: 增加 MCU/FPGA 全链路诊断日志
