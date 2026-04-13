# Database Management Guide

## Overview

Lumina 当前使用 **PostgreSQL + pgvector** 作为统一记忆存储。
主配置入口是 `config.yaml` 中的 `memory.postgres` 段，或对应环境变量：

- `LUMINA_PG_HOST`
- `LUMINA_PG_PORT`
- `LUMINA_PG_USER`
- `LUMINA_PG_PASSWORD`
- `LUMINA_PG_DATABASE`

## Local Startup

推荐直接使用根目录的 [`start_lumina.ps1`](/E:/Work/Code/Lumina/start_lumina.ps1)，脚本会：

1. 读取 `Lumina_Data/config.yaml` 中的 PostgreSQL 配置。
2. 检查目标端口是否可达。
3. 本地没有数据库时尝试用 Docker 拉起 `db` 服务。
4. 数据库就绪后再启动 Electron + Vite。

## Manual Inspection

可以使用任意 PostgreSQL 客户端查看数据，例如 `psql`、DBeaver、TablePlus。

常用表：

- `conversation_log`
- `episodic_memory`
- `plugin_state`
- `worker_heartbeats`
- `security_audit`

## Troubleshooting

**Q: 启动时提示 memory backend unavailable？**  
A: 先确认 PostgreSQL 进程是否存活，以及 `memory.postgres` 的主机、端口、用户名和数据库名是否匹配。

**Q: 主进程能启动，但记忆功能返回 503？**  
A: 这表示后端已经降级启动，UI 仍可用，但数据库连接没有建立成功。优先检查 PostgreSQL 日志和 `LUMINA_PG_PASSWORD`。
