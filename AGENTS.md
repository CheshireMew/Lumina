# Repository Guidelines

## 项目结构与模块组织
`app/` 为 Electron + React 前端，`python_backend/` 为 FastAPI 核心服务，`public/` 与 `assets/` 存放静态资源与模型文件，`docs/` 记录架构说明，`scripts/` 提供构建与校验脚本。构建产物集中在 `dist/`、`dist-electron/`、`dist_backend/`，请避免手改。

## 构建、测试与开发命令
- `npm install`：安装前端依赖。
- `npm run dev`：启动前端开发服务（Vite）。
- `.\start_lumina.ps1`：一键启动数据库、后端与桌面端（Windows）。
- `npm run build`：校验构建、编译 TypeScript、打包 Electron。
- `npm run lint`：运行 ESLint。
- `npm run verify-build`：执行 `scripts/verify_build.py` 进行构建前检查。
- `npm run gen-types`：运行 `scripts/generate_api_client.ps1` 生成类型。

## 编码风格与命名约定
遵循 `.editorconfig`：默认 4 空格缩进，`*.json`/`*.yml`/`*.md` 使用 2 空格，换行符为 LF。前端组件使用 PascalCase，变量与函数使用 camelCase；Python 模块与函数使用 snake_case。新增配置项放在 `config/`，避免散落。

## 测试指南
当前测试以手工与脚本验证为主。`test/emotion_test.ts` 用于在浏览器控制台验证 Live2D 情感触发，请按文件内说明操作。提交前至少运行 `npm run lint`，若改动后端逻辑，请启动本地服务进行回归验证。

## 提交与合并请求规范
Git 历史使用 Conventional Commits 风格：`feat`/`fix`/`refactor`/`chore`/`docs`，可带 scope，例如 `feat(stt): ...`。PR 需包含变更说明、测试步骤、关联 Issue；涉及 UI/交互请附截图或录屏。

## 安全与配置提示
`.env` 用于本地 API Key，不要提交到仓库。数据库文件属于本地状态，变更前请备份。运行脚本需确保已安装 Node.js、Python 与 PostgreSQL。
