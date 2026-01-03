import ctypes
import json
import socket
import shutil
from subprocess import Popen
from tkinter import filedialog as fd, messagebox

with open('data/db/init.db', 'r', encoding='utf-8') as file:
    lines = file.readlines()
init = int(lines[0].strip())
if init == 0:
    user_response = messagebox.askyesno("欢迎使用枫云AI虚拟伙伴Web版",
                                   "您是否阅读了软件使用文档并同意GPL-3.0开源协议？\n(首次运行加载较长,请耐心等待)\n注意事项:\n1.如果需要使用云端免费模型,首次使用请前往软件设置→云端AI Key设置\n2.本软件公益开源免费,严禁商用、套壳和倒卖,请遵守开源协议使用")
    if user_response:
        with open('data/db/init.db', 'w', encoding="utf-8") as file:
            file.write("1")
    else:
        exit()
try:
    with open('data/db/config.json', 'r', encoding='utf-8') as file:
        config = json.load(file)
    mate_name = config["虚拟伙伴名称"]
    prompt = config["虚拟伙伴人设"]
    username = config["用户名"]
    vits_model_name = config["VITS-ONNX模型名"]
    paddle_rate = config["PaddleTTS语速"]
    paddle_lang = config["PaddleTTS语言"]
    chatweb_port = config["对话网页端口"]
    live2d_port = config["L2D角色网页端口"]
    mmd_port = config["MMD角色网页端口"]
    vrm_port = config["VRM角色网页端口"]
    local_llm_ip = config["本地LLM服务器IP"]
    anything_llm_ws = config["AnythingLLM工作区"]
    cam_permission = config["摄像头权限"]
    anything_llm_key = config["AnythingLLM密钥"]
    ollama_model_name = config["Ollama大语言模型"]
    stream_tts_switch = config["流式语音合成开关"]
    custom_url = config["自定义API-base_url"]
    custom_key = config["自定义API-api_key"]
    custom_model = config["自定义API-model"]
    voice_key = config["实时语音开关键"]
    chat_web_switch = config["对话网页开关"]
    pet_top_switch = config["桌面宠物置顶"]
    ollama_vlm_name = config["Ollama多模态VLM"]
    wake_word = config["自定义语音唤醒词"]
    pet_x = int(config["桌宠位置x"])
    pet_y = int(config["桌宠位置y"])
    voice_break = config["实时语音打断"]
    asr_sensitivity = config["语音识别灵敏度"]
    weather_city = config["默认天气城市"]
    dify_ip = config["Dify知识库IP"]
    dify_key = config["Dify知识库密钥"]
    edge_speaker = config["edge-tts音色"]
    edge_rate = config["edge-tts语速"]
    edge_pitch = config["edge-tts音高"]
    custom_vlm = config["自定义API-VLM"]
    prefer_draw = config["图像生成引擎"]
    voiceprint_switch = config["声纹识别"]
    try:
        with open('data/db/preference.json', 'r', encoding='utf-8') as file:
            preference = json.load(file)
        voice_switch = preference["语音识别模式"]
        prefer_llm = preference["对话语言模型"]
        prefer_tts = preference["语音合成引擎"]
        prefer_img = preference["图像识别引擎"]
        ase_switch = preference["主动感知对话"]
        prefer_mode = preference["运行模式切换"]
    except:
        voice_switch = "关闭语音识别"
        prefer_llm = "GLM-4-Flash"
        prefer_tts = "云端edge-tts"
        prefer_img = "GLM-4V-Flash"
        ase_switch = "不主动"
        prefer_mode = "角色扮演聊天"
    with open('data/db/history.db', 'r', encoding='utf-8') as file:
        history = file.read()
    with open('data/set/custom_tts_set.txt', 'r', encoding='utf-8') as file:
        lines = file.readlines()
    custom_tts_url = lines[1].strip()
    custom_tts_model = lines[4].strip()
    custom_tts_voice = lines[7].strip()
    custom_tts_key = lines[10].strip()
    with open('data/db/vrm_model_name.db', 'r', encoding='utf-8') as file:
        vrm_model_name = file.read()
    with open('dist/assets/live2d_core/live2d_js_part1', 'r', encoding='utf-8') as file:
        live2d_js_part1 = file.read()
    with open('dist/assets/live2d_core/live2d_js_part2', 'r', encoding='utf-8') as file:
        live2d_js_part2 = file.read()
    with open('dist/assets/live2d_core/live2d_js_part3', 'r', encoding='utf-8') as file:
        live2d_js_part3 = file.read()
    with open('dist/assets/live2d_core/live2d_js_part4', 'r', encoding='utf-8') as file:
        live2d_js_part4 = file.read()
    with open('dist/assets/live2d_core/live2d_js_part5', 'r', encoding='utf-8') as file:
        live2d_js_part5 = file.read()
    try:
        with open('data/set/more_set.json', 'r', encoding='utf-8') as file:
            more_set = json.load(file)
        cam_num = int(more_set["摄像头编号"])
        mic_num = int(more_set["麦克风编号"])
        ollama_port = more_set["Ollama端口"]
        lmstudio_port = more_set["LM Studio端口"]
        sd_port = more_set["本地SD AI绘画端口"]
        tf_port = more_set["Transformers端口"]
        tf_model = more_set["Transformers模型"]
        vmd_music_switch = more_set["MMD 3D动作音乐开关(可选项:on/off)"]
        vmd_music_name = more_set["MMD 3D动作音乐名称(位于data/music_vmd文件夹)"]
        gsv_prompt = more_set["GPT-SoVITS参考音频文本"]
        gsv_ref_audio_path = more_set["GPT-SoVITS参考音频路径(位于GSV整合包内)"]
        gsv_prompt_lang = more_set["GPT-SoVITS参考音频语言"]
        gsv_lang = more_set["GPT-SoVITS合成输出语言"]
        gsv_port = more_set["GPT-SoVITS端口"]
        pet_subtitle_switch = more_set["桌宠悬浮字幕开关(可选项:on/off)"]
        think_filter_switch = more_set["思维链think过滤(可选项:on/off)"]
        local_vlm_ip = more_set["本地VLM服务器IP"]
        local_tts_ip = more_set["本地TTS服务器IP"]
        local_draw_ip = more_set["本地AI绘画服务器IP"]
    except:
        messagebox.showinfo("提示", "更多设置修改失误，导致软件部分功能异常\n请重新设置，保存重启软件生效")
        Popen("notepad data/set/more_set.json")
    try:
        with open('data/set/cloud_ai_key_set.json', 'r', encoding='utf-8') as file:
            cloud_key_set = json.load(file)
        glm_key = cloud_key_set["GLM智谱BigModel开放平台key(bigmodel.cn)"]
        sf_key = cloud_key_set["SiliconCloud硅基流动平台key(siliconflow.cn)"]
        bd_key = cloud_key_set["文心百度智能云平台(console.bce.baidu.com/qianfan)"]
        hy_key = cloud_key_set["腾讯混元大模型平台key(console.cloud.tencent.com/hunyuan)"]
        xf_key = cloud_key_set["讯飞星火开放平台key(xinghuo.xfyun.cn/sparkapi)"]
    except:
        messagebox.showinfo("提示", "云端AI Key设置修改失误，导致云端AI功能异常\n请重新设置，保存重启软件生效")
        Popen("notepad data/set/cloud_ai_key_set.json")
    with open('data/set/home_assistant_set.txt', 'r', encoding='utf-8') as file:
        lines = file.readlines()
    ha_api = lines[1].strip()
    entity_id = lines[4].strip()
    ha_key = lines[7].strip()
    with open('dist/assets/mmd_core/mmd_js_part1', 'r', encoding='utf-8') as file:
        mmd_js_part1 = file.read()
    with open('dist/assets/mmd_core/mmd_js_part2', 'r', encoding='utf-8') as file:
        mmd_js_part2 = file.read()
    with open('dist/assets/mmd_core/mmd_js_part3', 'r', encoding='utf-8') as file:
        mmd_js_part3 = file.read()
    with open('dist/assets/mmd_core/mmd_js_part4', 'r', encoding='utf-8') as file:
        mmd_js_part4 = file.read()
    with open('dist/assets/mmd_core/mmd_vmd_js_part1', 'r', encoding='utf-8') as file:
        mmd_vmd_js_part1 = file.read()
    with open('dist/assets/mmd_core/mmd_vmd_js_part2', 'r', encoding='utf-8') as file:
        mmd_vmd_js_part2 = file.read()
    with open('dist/assets/mmd_core/mmd_vmd_js_part3', 'r', encoding='utf-8') as file:
        mmd_vmd_js_part3 = file.read()
except Exception as e1:
    mate_name = "小月"
    chatweb_port = "5260"
    live2d_port = "5261"
    mmd_port = "5262"
    vrm_port = "5263"
    messagebox.showerror("启动失败", f"由于误操作设置，导致软件数据损坏\n请参考错误信息来解决:\n{e1}")


# open_source_project_address:https://github.com/swordswind/ai_virtual_mate_web
def get_local_ip():  # 获取本机在局域网的IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('119.29.29.29', 1))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    return ip


def upload_image():  # 更换网页背景
    file_path = fd.askopenfilename(title="选择一张JPG图片", filetypes=[("JPG文件", "*.jpg")])
    if file_path:
        target_path = "dist/assets/image/bg.jpg"
        shutil.copy(file_path, target_path)
        messagebox.showinfo("提示", "更换网页背景成功,请刷新网页")


def get_dpi():  # 获取DPI
    try:  # Windows系统下获取DPI
        hDC = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hDC, 88)
        ctypes.windll.user32.ReleaseDC(0, hDC)
        return dpi
    except:  # 如果获取DPI失败，默认返回96
        return 96


server_ip = get_local_ip()
edge_speaker_list = ["晓艺-年轻女声", "晓晓-成稳女声", "云健-大型纪录片男声", "云希-短视频热门男声", "云夏-年轻男声",
                     "云扬-成稳男声", "晓北-辽宁话女声", "晓妮-陕西话女声", "晓佳-粤语成稳女声", "晓满-粤语年轻女声",
                     "云龙-粤语男声", "晓辰-台湾话年轻女声", "晓宇-台湾话成稳女声", "云哲-台湾话男声", "佳太-日语男声",
                     "七海-日语女声"]
mzw_model_url = "https://www.aplaybox.com/model/model"
default_config = {
    "虚拟伙伴名称": "小月",
    "虚拟伙伴人设": "请你扮演《枫云之境》中的小月。你是晨光型情感伴生型少女，来自枫云市。有着樱粉色双丸髻、碧蓝眼睛，身着绀碧暗金相间的新中式裙装。你性格开朗温暖，善于观察他人情绪。你用甜美语气交流，称对方为开拓者，并且绝不提及自己是AI或程序。你的回复尽量简洁，不要包含emoji，不要超过100字",
    "用户名": "开拓者", "VITS-ONNX模型名": "sherpa-onnx-vits-zh-ll", "PaddleTTS语速": "5", "PaddleTTS语言": "中文",
    "对话网页端口": "5260", "L2D角色网页端口": "5261", "MMD角色网页端口": "5262", "VRM角色网页端口": "5263",
    "本地LLM服务器IP": "127.0.0.1", "AnythingLLM工作区": "aivm", "摄像头权限": "开启",
    "AnythingLLM密钥": "在AnythingLLM获取", "Ollama大语言模型": "qwen3:1.7b", "流式语音合成开关": "关闭",
    "自定义API-base_url": "填入服务提供方地址，例如 https://api.siliconflow.cn/v1",
    "自定义API-api_key": "填入从服务提供方控制台获取的密钥，例如 sk-xxxxxxxxxx",
    "自定义API-model": "填入服务提供方支持的LLM名称，例如 Qwen/Qwen3-8B", "实时语音开关键": "x", "对话网页开关": "开启",
    "桌面宠物置顶": "开启", "Ollama多模态VLM": "qwen3-vl:2b-instruct", "自定义语音唤醒词": "你好", "桌宠位置x": "150",
    "桌宠位置y": "70", "实时语音打断": "关闭", "语音识别灵敏度": "中", "默认天气城市": "杭州",
    "Dify知识库IP": "127.0.0.1", "Dify知识库密钥": "app-xxxxxxxxxx", "edge-tts音色": "晓艺-年轻女声", "edge-tts语速": "+0",
    "edge-tts音高": "+10", "自定义API-VLM": "填入服务提供方支持的VLM名称，例如 Qwen/Qwen3-VL-8B-Instruct",
    "图像生成引擎": "云端CogView-3", "声纹识别": "关闭"}
default_more_set = {
    "摄像头编号": "0", "麦克风编号": "0", "声纹识别阈值": "0.6", "Ollama端口": "11434", "LM Studio端口": "1234",
    "本地SD AI绘画端口": "7860", "Transformers端口": "8000", "Transformers模型": "model/Qwen3-0.6B",
    "MMD 3D动作音乐开关(可选项:on/off)": "on", "MMD 3D动作音乐名称(位于data/music_vmd文件夹)": "测试音乐.mp3",
    "GPT-SoVITS端口": "9880", "GPT-SoVITS参考音频文本": "你好，我是小月，很高兴遇见你。有什么我可以帮助你的吗",
    "GPT-SoVITS参考音频路径(位于GSV整合包内)": "example.wav", "GPT-SoVITS参考音频语言": "zh",
    "GPT-SoVITS合成输出语言": "zh", "桌宠悬浮字幕开关(可选项:on/off)": "on", "思维链think过滤(可选项:on/off)": "on",
    "本地VLM服务器IP": "127.0.0.1", "本地TTS服务器IP": "127.0.0.1", "本地AI绘画服务器IP": "127.0.0.1"}
default_cloud_ai_key_set = {
    "GLM智谱BigModel开放平台key(bigmodel.cn)": "xxxxx.xxxxx",
    "SiliconCloud硅基流动平台key(siliconflow.cn)": "sk-xxxxxxxxxx",
    "文心百度智能云平台(console.bce.baidu.com/qianfan)": "bce-v3/xxxxx-xxxxx/xxxxx",
    "腾讯混元大模型平台key(console.cloud.tencent.com/hunyuan)": "sk-xxxxxxxxxx",
    "讯飞星火开放平台key(xinghuo.xfyun.cn/sparkapi)": "xxxxx:xxxxx"}
mode_options = ["角色扮演聊天", "多智能体助手"]
voice_options = ["实时语音识别", "自定义唤醒词", "关闭语音识别"]
llm_options = ["GLM-4-Flash", "通义千问3-8B", "DeepSeek-R1-8B", "文心一言Speed", "腾讯混元Lite", "讯飞星火Lite", "本地Ollama LLM",
               "本地LM Studio", "本地Transformers", "Dify聊天助手", "AnythingLLM", "自定义API-LLM"]
tts_options = ["云端edge-tts", "云端Paddle-TTS", "内置低延迟VITS", "本地GPT-SoVITS", "本地CosyVoice", "本地Index-TTS",
               "本地VoxCPM", "系统自带TTS", "自定义API-TTS", "关闭语音合成"]
img_options = ["GLM-4V-Flash", "本地Ollama VLM", "本地LM Studio", "本地QwenVL整合包", "本地Janus整合包", "自定义API-VLM",
               "关闭图像识别"]
all_task = "音乐播放、语音输入、打开软件/网页、音量减小、音量增大、文本写作、翻译屏幕内容、解释屏幕内容、总结屏幕内容、续写屏幕内容、屏幕内容问答、摄像头场景问答、灯类智能家居控制、天气查询、热搜新闻、系统状态查询、联网搜索、视频生成、绘画图像生成、日常闲聊"
glm_llm_model = "glm-4-flash-250414"
glm_vlm_model = "glm-4v-flash"
sf_url = "https://api.siliconflow.cn/v1"
bd_url = "https://qianfan.baidubce.com/v2"
bd_model = "ernie-speed-128k"
hy_url = "https://api.hunyuan.cloud.tencent.com/v1"
hy_model = "hunyuan-lite"
xf_url = "https://spark-api-open.xf-yun.com/v1"
xf_model = "lite"
vits_target_dir = "data/model/TTS"
