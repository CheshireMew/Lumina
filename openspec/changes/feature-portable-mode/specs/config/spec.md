# Spec: Config Path Resolution

## 新增需求

### 需求:Data Path Resolution

#### 场景:检测便携数据目录

- **Given** 应用程序启动(Frozen 或 Dev 模式)。
- **When** 在 `Base Directory` (可执行文件所在目录) 下发现名为 `Lumina_Data` 的子目录。
- **Then** `CONFIG_ROOT` 和所有数据存储路径 **必须 (MUST)** 指向 `Lumina_Data`。

#### 场景:回退到标准 AppData

- **Given** `Base Directory` 下**不**存在 `Lumina_Data` 目录。
- **And** 没有设置 `LUMINA_DATA_PATH` 环境变量。
- **Then** `CONFIG_ROOT` **必须 (MUST)** 指向操作系统的标准用户数据目录(Windows 下为 `%APPDATA%/Lumina`)。
- **Note**: 这改变了当前"默认写入安装目录"的行为,提高了安全性和规范性(Program Files 通常不可写)。但为了向后兼容,如果当前工作目录已有配置文件,可能需要一个迁移或兼容检查。
