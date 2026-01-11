# GPT-SoVITS 模型下载指南

GPT-SoVITS 拥有强大的社区资源，你完全不需要自己训练模型。网络上有大量现成的**角色模型 (Fine-tuned Models)** 和 **底模 (Base Models)** 可供直接使用。

## 1. 核心底模 (必须下载)

GPT-SoVITS 运行的基础，必须下载放入 `GPT_SoVITS/pretrained_models`。

*   **Hugging Face 官方仓库**: [lj1995/GPT-SoVITS](https://huggingface.co/lj1995/GPT-SoVITS)
    *   下载 `s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt` (底模)
    *   下载 `s2D488k.pth` (底模)
    *   下载 `s2G488k.pth` (底模)
    *   下载 `chinese-roberta-wwm-ext-large` (文本编码器)
    *   下载 `chinese-hubert-base` (语音编码器)

## 2. 现成角色模型 (推荐)

社区已经训练好了大量动漫/游戏角色模型，你只需要下载 `.pth` (模型) 和 `.ckpt` (GPT权重) 两个文件即可使用。

### 推荐下载源
1.  **Hugging Face 模型库**: 搜索 `GPT-SoVITS`
    *   例如：[WhiteCastle/GPT-SoVITS-Models](https://huggingface.co/WhiteCastle/GPT-SoVITS-Models) (包含大量二次元角色)
    *   [X-T-E-R/GPT-SoVITS-Models](https://huggingface.co/X-T-E-R/GPT-SoVITS-Models)
2.  **ModelScope 魔搭社区**: 国内下载速度更快
    *   搜索 `GPT-SoVITS`
3.  **Bilibili / YouTube 视频简介**:
    *   很多 UP 主分享模型链接（通常是阿里云盘/夸克网盘），搜索 "GPT-SoVITS 模型分享" + 你想要的角色名（如 "流萤 GPT-SoVITS"）。

### 如何使用下载的角色模型？
下载后得到两个文件（例如 `liuying-e10.ckpt` 和 `liuying_e10_s200.pth`）：

1.  **参考音频**: 这个最重要！模型作者通常会附带一段 `ref.wav` 和对应的文本。如果没有，你需要自己从该角色的语音素材中截取一段 5-10 秒的干净语音。
2.  **加载模型**: 在 GPT-SoVITS 的 WebUI 中勾选这两个模型文件。

## 3. "零样本" (Zero-Shot) 能力

**其实你甚至不需要下载特定角色模型！**

GPT-SoVITS 最强的地方在于 **Zero-Shot (零样本克隆)**。
只要你有官方底模（第1步下载的），然后：
1.  找一段 5-10 秒的任意角色语音（如雷电将军的一句话）。
2.  把这段语音作为“参考音频”喂给系统。
3.  GPT-SoVITS 就能用这个声音说话了！

**结论**:
*   想省事？直接用底模 + 参考音频 (效果已经有 90% 像)。
*   想极致完美？去下载对应角色的微调模型。

---

**建议下一步**:
先只下载 **官方底模**，然后找一段你喜欢的角色的音频文件（mp3/wav）测试。如果效果不满意，再去找微调模型。
