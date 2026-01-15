# Proposal: Portable Mode (feature-portable-mode)

## 为什么

允许用户在移动硬盘或非系统盘运行 Lumina,所有数据(配置、记忆、日志)跟随主程序存储,而不写入系统 `AppData`。这对于保护隐私(即插即用)和跨设备携带非常重要。

## 当前行为

- `app_config.py` 目前将 `CONFIG_ROOT` 设置为 `sys.executable` 的父目录(打包后)或源码目录(开发时)。
- 这意味着如果在 Program Files 运行,可能因权限问题无法写入。
- 或者是直接写在安装目录下,这本身就是一种"半便携"状态,但缺乏明确的"数据分离"逻辑(即程序升级时覆盖安装目录会丢失数据)。

## 变更内容

引入明确的 **数据目录发现逻辑**:

1. **优先级 1 (便携模式)**: 检查可执行文件同级目录下是否存在 `Lumina_Data` 文件夹。
   - 如果存在 -> 将所有 User Data 指向此目录。
   - 适用于:便携版解压即用。
2. **优先级 2 (环境设置)**: 检查 `LUMINA_DATA_PATH` 环境变量。

3. **优先级 3 (安装模式)**: 默认回退到 `%APPDATA%/Lumina` (Windows) 或 `~/.config/lumina` (Linux/Mac)。
   - 适用于:标准安装程序(安装到 Program Files)。

## 影响范围

- `python_backend/app_config.py`: 修改 `CONFIG_ROOT` 和数据路径的解析逻辑。
- `Launcher` (PowerShell/Electron): 启动时传递或设置路径。
- `SurrealDB`: 需要将数据库文件存储在解析出的数据目录下。

## 验证

- 在 USB 驱动器上创建一个 `Lumina_Data` 文件夹,启动程序,验证数据是否写入其中。
- 删除该文件夹,启动程序,验证数据是否写入 AppData(或保持当前默认行为,视设计而定)。
