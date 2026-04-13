# Lumina MVP Definition (Minimum Viable Product)

> Focus: Reliable, Low-Latency Conversation with Live2D Avatar.

## 1. Core User Loop (The "Must Haves")

- **Voice Interaction**:
  - [ ] **STT**: User speaks -> Accurate text transcription (SenseVoice).
  - [ ] **LLM**: Context-aware response (< 3s latency).
  - [ ] **TTS**: Natural voice output (GPT-SoVITS) synced with audio.
- **Visual Feedback**:
  - [ ] **Live2D**: Character renders, idles, and performs lip-sync to TTS.
  - [ ] **UI**: User sees chat bubble history.
- **Persistence**:
  - [ ] **Memory**: Conversation context persists across restarts (SurrealDB).

## 2. Critical Architecture (Enablers)

- **Backend Service**: `main.py` starts without error.
- **Frontend App**: Electron app launches and connects to `GET /network`.
- **Config**: Settings (API keys, paths) load correctly.

## 3. Excluded from MVP (Post-MVP)

- _Complex Plugins_ (Web Search, Home Assistant).
- _Long-term Memory Dreaming_ (The Gardener).
- _Multi-Character Switching_ (UI is there, but stability is lower priority).
- _Remote Process Isolation_ (Optimization, not functional req).

## 4. MVP Verification Plan

1.  **Startup Check**: One-click launch verify.
2.  **Ping Test**: Frontend <-> Backend connectivity.
3.  **Echo Test**: Speak -> STT logs text -> LLM replies -> TTS plays.


Lumina 全面架构审查报告
Critical（立即影响功能或安全）
#	领域	问题	文件
1	安全	/ws/worker-control 无任何认证，任何能访问 8010 端口的客户端可注册为 Worker	main.py:180, worker_control_hub.py:67
2	配置	Electron 首次运行无 ports.json 时，stt_port 回退到 8010（与主服务冲突）	python_stt_service.ts:363,494
High（严重但不致命，需尽快修复）
#	领域	问题	文件
3	安全	PluginGuardMiddleware 异常时 fail-open（应该 fail-closed）	plugin_guard.py:86-89
4	安全	无效 Token 被静默放行而非 401 拒绝	scope_guard.py:35-41
5	安全	所有 Router 的 HTTPException(500, str(e)) 泄露内部错误到生产环境（绕过全局 is_dev 保护）	30+ 处
6	安全	JWT Secret 写到相对路径、无文件权限设置	security/tokens.py:18-34
7	安全	Worker CORS allow_methods=["*"] + allow_credentials=True	generic_worker.py:99-100
8	安全	Admin 原始查询未阻止 SurrealDB 的 REMOVE/DEFINE/UPSERT	routers/admin.py:101-130
9	安全	Config freeze 对嵌套 Pydantic 模型无效（app_settings.stt.provider = x 绕过冻结）	app_config.py:343, stt/routes.py:169
10	并发	switch_model_background 写共享状态不持锁	capabilities/stt/manager.py:60,80-84
11	并发	transcribe() 在 threading.Lock 内执行 ML 推理（数百毫秒阻塞）	capabilities/stt/manager.py:244-247
12	资源	STT message_queue 无界，持续语音输入会 OOM	capabilities/stt/globals.py:15
13	资源	generic_worker.py shutdown 未取消 ConfigWatcher 和 PluginStateSync 任务	generic_worker.py:253,241
14	资源	SurrealLifecycleBus 单 WebSocket 连接无重连逻辑，断连后写入静默丢失	surreal_lifecycle_bus.py:50-51
15	asyncio	asyncio.get_event_loop().create_task() 在 Python 3.12 已废弃	generic_worker.py:240-241
16	asyncio	Postgres NOTIFY 回调中并发修改 subscribers 列表	postgres_lifecycle_bus.py:261-268
17	进程	stop_worker() fire-and-forget async stop，worker 被删除时 stop 还没完成	process_manager.py:309-323
18	前端	isTTSEnabled 永不持久化，每次重启恢复为 true	useSettings.ts
19	前端	POST /soul/switch_character 永远返回 501，角色切换静默失败	routers/soul.py:86-96
20	前端	POST /soul/mutate 端点不存在，情感突变和主动聊天清除始终 404	soul.py
21	前端	GET /soul 响应缺少 system_prompt 字段，LLM 可能无角色人格	soul.py:47-64
22	构建	electron-builder 引用 dist_backend/ 但构建脚本不包含 PyInstaller 步骤	package.json:93-120
23	API	PluginStatus 前端接口要求 active_in_group/config_schema/permissions，后端从未返回	usePluginManager.ts vs 后端
24	LLM	Electron 向 /llm-mgmt/providers/custom_provider POST 同步配置，需确认端点存在	main.ts:145
Medium
#	领域	问题
25	安全	electron://altair CORS origin 疑似遗留
26	安全	PluginConfigRequest.value 接受任意类型/大小，无限制
27	安全	ChatCompletionRequest.model 无白名单校验
28	安全	System role 注入检测存在但被 pass 跳过
29	并发	activate() 两个并发调用可以同时执行 driver.load()
30	资源	PluginStateAggregator._cache 无自动 prune
31	资源	MemoryJobQueue 无界 PriorityQueue
32	资源	Hub 清理过期 Worker 时未 emit worker.offline 事件
33	asyncio	emit_sync() 在非事件循环线程调用 create_task() 不安全
34	asyncio	run_coroutine_threadsafe 返回值被丢弃，异常静默吞掉
35	前端	COGNITIVE_STATE 后端发送但前端无 handler
36	前端	前端 "chat" 消息缺少 user_id，model 字段被后端忽略
37	前端	ChatCompletionRequest 缺少 top_p/presence_penalty/frequency_penalty
38	前端	GET /soul/{character_id} 永远返回 {}
39	构建	SurrealDB exe 仍在打包，但已迁移到 Postgres
40	死代码	VoiceInput 导入未使用，3 个 hooks 在 App.tsx 冗余导入
41	死代码	Gateway 中遗留 print("DEBUG: ...") 语句