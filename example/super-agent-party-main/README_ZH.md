![image](static/source/cover.png)

<div align="center">
  <a href="./README_ZH.md">
    <img src="https://img.shields.io/badge/简体中文-自述文档-00B4AB?style=for-the-badge&logo=markdown"/>
  </a>
  <a href="./README.md">
    <img src="https://img.shields.io/badge/English-Readme-0057D2?style=for-the-badge&logo=markdown"/>
  </a>
</div>

####

<div align="center">
  <a href="https://space.bilibili.com/26978344"><img src="https://img.shields.io/badge/B站-观看教程-red?style=for-the-badge&logo=bilibili"/></a>
  <a href="https://www.youtube.com/@LLM-party"><img src="https://img.shields.io/badge/YouTube-订阅频道-FF0000?style=for-the-badge&logo=youtube"/></a>
  <a href="https://gcnij7egmcww.feishu.cn/wiki/DPRKwdetCiYBhPkPpXWcugujnRc"><img src="https://img.shields.io/badge/中文使用指南-飞书文档-00CDCD?style=for-the-badge&logo=docsdotrs"/></a>
  <a href="https://temporal-lantern-7e8.notion.site/super-agent-party-211b2b2cb6f180c899d1c27a98c4965d"><img src="https://img.shields.io/badge/English%20Usage%20Guide-Notion-000000?style=for-the-badge&logo=notion"/></a>
  <a href="https://pan.baidu.com/share/init?surl=VBSnq4Ga3fRX_NcyPwsV7Q&pwd=2333"><img src="https://img.shields.io/badge/网盘下载-百度网盘-2E58D4?style=for-the-badge&logo=baidu"/></a>
  <a href="#快速开始"><img src="https://img.shields.io/badge/快速开始-下载-0052CC?style=for-the-badge&logo=github"/></a>
</div>

## 简介

### 🚀 **一款拥有无限可能的AI桌面伴侣！**

- ✅ 全渠道一键部署：支持将智能体配置快速部署至多类终端，已兼容经典聊天界面、桌宠机器人、QQ、飞书、discord、telegram聊天机器人、B站、YouTube、twitch直播机器人等场景，开箱即用。

- ✅ 生态工具互联：可自由接入第三方智能体与工作流作为工具链（已适配Home Assistant/Claude code/Qwen code/Dify/ComfyUI/MCP/A2A等系统），通过agent-party架构实现跨平台能力聚合。

- ✅ 扩展生态丰富：支持自定义扩展开发，通过官网的[扩展市场](https://super-agent-party.github.io/plugins.html)实现社区共享，满足个性化需求。

- ✅ 标准化接口开放：提供OpenAI API兼容接口及MCP协议支持，便于开发者直接对接外部系统，实现智能体能力的快速转接与二次开发。VRM桌宠开放了VMC协议，实现跨应用动作同步。VRM桌宠界面支持了webXR协议，你可以在支持XR的设备中沉浸式体验。

- ✅ 无缝能力增强：无需代码改造即可实现LLM API企业级升级，为现有模型接口无缝集成知识库、实时联网、永久记忆、兼容酒馆(SillyTavern)角色卡、代码执行、多模态能力（视觉/绘图/听觉/语音）、自动化能力（控制智能家居、控制浏览器）、深度思考控制与研究等模块化功能，打造可插拔的LLM增强中台。

- ✅ 全平台兼容适配：覆盖Windows/macOS/Linux原生运行环境，支持Docker容器化部署与Web端云服务，满足多场景技术栈需求。

## 软件截图

### 多服务商支持：本地部署引擎(ollama/dify等等)以及云服务商接口均支持
![image](doc/image/1.jpeg)

### 海量工具：内置各种工具(如知识库、联网、智能家居、浏览器控制)，支持异步调用，不阻塞智能体回复
![image](doc/image/2.jpeg)

### VRM桌宠：支持上传自定义VRM模型，打造专属桌面伴侣
![image](doc/image/3.jpeg)

### 扩展系统：支持安装扩展，和自己创造新的扩展，下图为galgame扩展
![image](doc/image/4.jpeg)

### 酒馆角色卡：支持酒馆角色卡，支持长期记忆
![image](doc/image/5.jpeg)

### 社交平台机器人：支持一键部署到QQ、飞书、telegram、discord
![image](doc/image/6.jpeg)

### 直播机器人：支持一键部署到B站、YouTube、twitch
![image](doc/image/7.jpeg)

### 开发者友好：开放openai API接口、MCP接口，可以将智能体对外转接
![image](doc/image/8.jpeg)

## 快速开始

### 网盘下载

  👉 [点击百度云下载](https://pan.baidu.com/share/init?surl=VBSnq4Ga3fRX_NcyPwsV7Q&pwd=2333)
  
  👉 [点击谷歌云下载](https://drive.google.com/drive/folders/1xu8U1FCIZ5iqWpmf1w3TLX8AqGWft3zg?usp=sharing)

### windows整合包（推荐！免安装源码版本，支持一键同步到仓库最新版本，无需等待桌面版打包）

  👉 [点击下载](https://github.com/heshengtao/super-agent-party/releases/download/v0.3.5/super-agent-party-win-v0.3.5.7z)

⭐注意！你可以双击`一键更新(update).bat`更新软件，也可以双击`一键启动(start).bat`启动软件。操作系统需要是**Windows 10/11、Window Server 2025**或者后续版本！

### windows桌面版安装

  👉 [点击下载](https://github.com/heshengtao/super-agent-party/releases/download/v0.3.5/Super-Agent-Party-Setup-0.3.5.exe)

⭐注意！安装时选择仅为当前用户安装，否则启动时需要管理员权限。操作系统需要是**Windows 10/11、Window Server 2025**或者后续版本！

### MacOS整合包（目前只支持M芯片，适合开发者，同样是免安装源码版本，支持一键同步到仓库最新版本，无需等待桌面版打包）

  👉 [点击下载](https://github.com/heshengtao/super-agent-party/releases/download/v0.3.5/super-agent-party-mac-v0.3.5.7z)

⭐注意！你可以在终端使用`一键更新(update).sh`更新软件，也可以在终端使用`一键启动(start).sh`启动软件。在使用前，记得给文件加权限！

  ```shell
  chmod +x 一键更新(update).sh
  ./一键更新(update).sh
  chmod +x 一键启动(start).sh
  ./一键启动(start).sh
  ```

### MacOS桌面版安装（目前只支持M芯片）

  👉 [点击下载](https://github.com/heshengtao/super-agent-party/releases/download/v0.3.5/Super-Agent-Party-0.3.5-Mac.dmg)

⭐注意！下载后将dmg文件的app文件拖入`/Applications`目录下，然后打开终端，执行以下命令并输入root密码，从而移除从网络下载附加的Quarantine属性：

  ```shell
  sudo xattr -dr com.apple.quarantine  /Applications/Super-Agent-Party.app
  ```

### Linux 桌面版安装

我们提供了两种主流的 Linux 安装包格式，方便你在不同场景下使用。

#### 1. 使用 `.AppImage` 安装

`.AppImage` 是一种无需安装、即开即用的 Linux 应用格式。适用于大多数 Linux 发行版。

  👉 [点击下载](https://github.com/heshengtao/super-agent-party/releases/download/v0.3.5/Super-Agent-Party-0.3.5-Linux.AppImage)

#### 2. 使用 `.deb` 包安装（适用于 Ubuntu / Debian 系统）

  👉 [点击下载](https://github.com/heshengtao/super-agent-party/releases/download/v0.3.5/Super-Agent-Party-0.3.5-Linux.deb)

### docker部署（该版本桌宠只能通过浏览器查看）

- 两行命令安装本项目：
  ```shell
  docker pull ailm32442/super-agent-party:latest
  docker run -d -p 3456:3456 -v ./super-agent-data:/app/data ailm32442/super-agent-party:latest
  ```

- ⭐注意！`./super-agent-data`可以替换为任意本地文件夹，docker启动后，所有数据都将缓存到该本地文件夹，不会上传到任何地方。

- 开箱即用：访问http://localhost:3456/

### docker compose部署（该版本桌宠只能通过浏览器查看，会额外启动一个网关容器，用于登录管理）

- 安装本项目：

  ```shell
  git clone https://github.com/heshengtao/super-agent-party.git
  cd super-agent-party
  docker-compose up -d
  ```

- ⭐注意！初始用户名为`root`，初始密码为`pass`，首次登录后请修改密码。

- 开箱即用：访问http://localhost:3456/

- API key管理： 访问http://localhost:3456/token.html

### 与docker版本配套的轻量版客户端，将你的docker版本变成桌面端

👉 [SAP-lite-Windows-exe](https://github.com/heshengtao/desktop-for-sap/releases/download/v0.1.0/super-agent-party-lite-Setup-0.1.0.exe)

👉 [SAP-lite-MacOS-dmg](https://github.com/heshengtao/desktop-for-sap/releases/download/v0.1.0/super-agent-party-lite-0.1.0-Mac.dmg)


### 源码部署

  ```shell
  git clone https://github.com/heshengtao/super-agent-party.git
  cd super-agent-party
  uv sync
  npm install
  npm run dev
  ```

## 扩展

新增了全新的扩展系统，你可以在这里 [扩展列表](https://super-agent-party.github.io/plugins.html) 查看有哪些插件可用，你也可以直接在party中直接在【开发者】->【扩展】中查看和安装插件。你可以在[super-agent-party.github.io](https://github.com/super-agent-party/super-agent-party.github.io) 将你自己开发的扩展添加到官方扩展列表中！

## 硬件要求

- CPU：2核及以上
- 内存：2GB及以上

**因为所有的模型都是可选的，可以接入本地部署引擎，也可以全部使用云服务商的接口，所以硬件要求几乎没有。在2核2G的云服务器上测试docker版本可以正常运行** 

## 使用方法

- 桌面端：点击桌面端图标即可开箱即用。

- web端或docker端：启动后访问http://localhost:3456/

- API调用：开发者友好，完美兼容openai格式，可以流式输出，完全不影响原有API的反应速度，无需修改调用的代码：

  ```python
  from openai import OpenAI
  client = OpenAI(
    api_key="super-secret-key",
    base_url="http://localhost:3456/v1"
  )
  response = client.chat.completions.create(
    model="super-model",
    messages=[
        {"role": "user", "content": "什么是super agent party？"}
    ]
  )
  print(response.choices[0].message.content)
  ```

- MCP调用：启动后，在配置文件中写入以下内容，即可调用本地的mcp服务：

  ```json
  {
    "mcpServers": {
      "super-agent-party": {
        "url": "http://127.0.0.1:3456/mcp",
      }
    }
  }
  ```

## 功能

主要功能请移步以下文档查看：
  - 👉 [中文文档](https://gcnij7egmcww.feishu.cn/wiki/DPRKwdetCiYBhPkPpXWcugujnRc)
  - 👉 [英文文档](https://temporal-lantern-7e8.notion.site/super-agent-party-211b2b2cb6f180c899d1c27a98c4965d)

| 功能 | 详情 |
| --- | --- |
| 常见模型服务商支持 | 已支持市面上常见的本地部署引擎接口及云服务商接口，如：openai/ollama/dify等 |
| 多模态模型融合 | 支持将角色扮演、推理、视觉、绘图、语音识别、语音合成等多种类型的模型融合在一起使用 |
| VRM桌宠机器人 | 高度自由，支持自定义形象、自定义动作、可语音交互、对话打断等功能，可以透明推流到OBS等录屏软件中，支持双向VMC协议！ |
| 消息平台机器人 | 目前已支持QQ、飞书、discord、telegram，后续会支持更多平台 |
| 直播机器人 | 目前已支持B站、YouTube、twitch，后续会支持更多平台 |
| 播报机器人 | 支持长文播报，多语音播报，数字人口播，超长文本批量转语音（可下载），支持常见电子书epub等格式解析，后续开发分章节转录功能 |
| 对话界面 | 对话界面已支持A2UI、公式、mermaid绘图、HTML代码绘图等前端渲染功能，图像支持下载和复制。支持胶囊模式和小助手模式，方便将对话界面缩小停靠，配合桌面视觉和截图，无缝融入工作娱乐 |
| 角色扮演 | 支持酒馆角色卡上传、编辑及下载，可为不同角色配置不同语音和形象。支持长期记忆，使用角色卡时，支持多语音，非角色文字支持使用旁白音色，支持表情包 |
| 大量原生工具 | 工具调用支持异步，支持联网、知识库、控制智能家居、控制浏览器、在沙盒中执行代码、控制comfyui绘图、Claude code操作文件系统等 |
| 自定义工具接口 | 已支持MCP、A2A、HTTP请求、任意LLM接口作为主智能体的工具使用，让用户以完全自由的方式定制自己的智能体工具链 |
| 对外接口开放 | 开发者友好，对外开放模拟openAI和MCP的API接口，以及桌宠API接口 |
| 扩展系统 | 你可以在这里 [扩展列表](https://super-agent-party.github.io/plugins.html) 查看有哪些插件可用，你也可以直接在party中直接在【开发者】->【扩展】中查看和安装插件。你可以在[super-agent-party.github.io](https://github.com/super-agent-party/super-agent-party.github.io) 将你自己开发的扩展添加到官方扩展列表中！ |
| 存储空间 | 所有的文件资料均存放在用户本地的数据文件夹中，如果使用NAS部署，还可以作为内网的个人图床、文件床使用 |

## 免责声明：
本开源项目及其内容（以下简称“项目”）仅供参考之用，并不意味着任何明示或暗示的保证。项目贡献者不对项目的完整性、准确性、可靠性或适用性承担任何责任。任何依赖项目内容的行为均需自行承担风险。在任何情况下，项目贡献者均不对因使用项目内容而产生的任何间接、特殊或附带的损失或损害承担责任。

## 特别说明
本开源项目的部分功能（如 Edge TTS 语音合成、B 站 WebSocket 弹幕监听等）依赖于第三方服务的公开接口或实验性功能。这些功能可能随时因第三方政策调整而失效，开发者不对其稳定性、合法性或持续性承担责任。

QQ机器人使用的是QQ官方机器人接口，请遵守[AIGC接入QQ机器人须知](https://q.qq.com/#/news/detail?id=1376238e8e2fbbc036676bb09d2f37da)

用户使用这些功能即视为已知晓并同意自行承担相关风险。开发者不建议也不鼓励将这些功能用于商业或大规模部署场景。

## 许可证协议

本项目采用双许可证授权模式：
1. 默认情况下，本项目遵循 **GNU Affero General Public License v3.0 (AGPLv3)** 授权协议
2. 若需将本项目用于闭源的商业用途，必须通过项目管理员获取商业授权许可。商业合作：hst97@qq.com

未经书面授权擅自进行闭源商业使用的，视为违反本协议约定。AGPLv3 完整文本可在项目根目录的 LICENSE 文件或 [gnu.org/licenses](https://www.gnu.org/licenses/agpl-3.0.html) 查阅。

### 第三方许可证声明

本项目可能包含或依赖一些第三方库或组件，这些第三方材料的许可证可能与主项目的许可证不同。为遵守相关许可证要求，您可以在项目根目录下的 [LICENSE-third-party](./LICENSE-third-party) 文件夹中查阅这些第三方组件的许可证信息，或在对应组件的源代码中找到其许可证文件。

我们感谢所有第三方库和组件的贡献者，并承诺尊重其许可证条款。

## 支持：

### 求星标！
⭐你的支持是我们前进的动力！

<div align="center">
  <img src="doc/image/star.gif" width="400" alt="star">
</div>

### 关注我们
<div align="center">
  <a href="https://space.bilibili.com/26978344">
    <img src="doc/image/B.png" width="100" height="100" style="border-radius: 80%; overflow: hidden;" alt="octocat"/>
  </a>
  <a href="https://www.youtube.com/@agentParty">
    <img src="doc/image/YT.png" width="100" height="100" style="border-radius: 80%; overflow: hidden;" alt="octocat"/>
  </a>
</div>

<div align="center">
  <a href="https://www.bilibili.com/video/BV15UuJz9EGH/" target="_blank">
    <img src="https://i0.hdslb.com/bfs/archive/0f4629dcc958a9437cd7f2e6b5b84649b6ac467c.jpg" 
         width="600" 
         alt="B站视频封面"
         style="border-radius: 8px; border: 1px solid #eee;">
  </a>
</div>

### 加入社群
如果项目存在问题或者您有其他的疑问，欢迎加入我们的社群。

1. QQ群：`931057213`

<div style="display: flex; justify-content: center;">
    <img src="doc/image/Q群.jpg" style="width: 48%;" />
</div>

2. 微信群：`we_glm`（添加小助手微信后进群）

3. discord:[discord链接](https://discord.gg/f2dsAKKr2V)

## 星标历史

[![Star History Chart](https://api.star-history.com/svg?repos=heshengtao/super-agent-party&type=Date)](https://www.star-history.com/#heshengtao/super-agent-party&Date)