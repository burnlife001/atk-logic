# ATK-Logic 二次开发环境搭建记录

## 当前状态

编译环境完整可用，Debug/Release 均已成功编译并启动界面。首次启动后固件自动更新完成，但随即弹窗提示「软件版本过低，请升级软件」，USB 未连接时界面无法操作。

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

## 已知问题：软件版本过低

### 现象
1. 程序界面正常显示
2. 启动后自动更新固件（进度条完成）
3. 弹窗：「软件版本过低，请升级软件」
4. USB 未连接时界面无法操作

### 排查方向

#### 可能性1：APP_VERSION 版本号检查
- `.pro` 中 `VERSION = 1.0.6.6`，`APP_VERSION_NUM=1066`
- `DEFINES += FPGA_MIN_VERSION_NUM=115`
- 固件可能要求更高的版本号。检查 `main.cpp:203` 的 `atk_decoder_init` 和 `atk_decoder_load_all` 返回值。
- 在已安装的 `D:\Programs\ATK-Logic\` 版本中对比版本号或其它参数差异。

#### 可能性2：atk_decoder 初始化失败
- `main.cpp` 中 `atk_decoder_init()` 返回非 `ATK_OK` 时设置 `ret=1`
- `atk_decoder_load_all()` 失败时设置 `ret=2`
- 这些值传递给 QML 层 (`decode_init_code` 属性)，界面可能据此提示版本过低。
- **排查**：在 `main.cpp` 的 decoder 初始化处加日志，确认 `ret` 值。

#### 可能性3：runtime DLL 版本不匹配
- `libsigrokdecode-4.dll` 依赖 `libpython3.14.dll`
- 原始 ATK-Logic 使用 `python37.dll` (Python 3.7)
- Python 3.14 → 3.7 API 差异可能导致解码器模块加载行为异常。
- **排查**：如果 `atk_decoder_load_all()` 内部依赖协议解码器 Python 脚本，Python 版本差异可能导致某些解码器无法加载。

#### 可能性4：Decoders 目录未复制
- `atk_decoder_init()` 接收路径参数，在该路径下查找 `decoders/` 目录
- 原始安装版 `D:\Programs\ATK-Logic\decoders/` 包含大量协议解码器
- **排查**：确认 `decoders/` 是否在 exe 同级目录，或在 init 参数指定的路径下。

#### 可能性5：固件版本检查
- `FPGA_MIN_VERSION_NUM=115` 可能是固件最低版本要求
- 固件更新后，软件侧检查 FPGA 版本是否满足最低要求
- **排查**：查看 `data_service` 或 USB 通信层是否有 FPGA 版本比对逻辑。

### 建议排查步骤
1. 先检查 `decode_init_code` 传给 QML 的值（main.cpp:218 → `0` 表示成功，`1`/`2` 表示失败）
2. 确认 `decoders/` 目录存在于 exe 运行目录
3. 对比 `D:\Programs\ATK-Logic\` 中原始安装版的目录结构，补全缺失文件
4. 如果以上都正常，检查 FPGA 版本号相关逻辑（搜索 `FPGA_MIN_VERSION` 使用位置）
