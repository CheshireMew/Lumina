# 已归档的后端实现

这些文件在 2026-08-23 的前后端架构治理中退出正式运行路径，内容完整保留，没有删除。

- `python_backend/services/automation/`：未接入产品入口，且仍包含未实现的 YAML 加载与事件发送分支。Lumina 当前不在产品内部提供 Agent 或自动化编排层；外部 Agent 通过现有 CLI、API 和工具使用项目能力。
- `python_backend/services/discovery/`：旧的分布式注册表和负载均衡实现。当前 Windows 桌面运行时统一使用 `python_backend/services/infra/service_discovery.py`，并由应用组合根显式创建和注入。
- `python_backend/core/services/`：旧的服务定位器。当前服务只从 `python_backend/services/container/` 的显式组合根获取，避免隐藏单例和两套依赖解析规则。

归档代码不属于可导入的生产源码。若未来确实需要其中的能力，应先根据当时的产品需求重新设计公开契约和生命周期，不应直接把这些目录移回运行路径。
