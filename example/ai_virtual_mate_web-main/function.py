import re
import sys
import time
import warnings
import keyboard as kb
from datetime import datetime
from comtypes import CLSCTX_ALL
from ollama import Client
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from PySide6.QtWidgets import QApplication
from zhipuai import ZhipuAI
from gui import *

warnings.filterwarnings("ignore", category=UserWarning)
import pygame as pg

devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = interface.QueryInterface(IAudioEndpointVolume)


def current_time():  # 获取当前时间
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def on_closing():  # 退出
    if messagebox.askokcancel("确认退出", "您确定要退出枫云AI虚拟伙伴Web版吗？"):
        root.destroy()


def open_pet():  # 打开桌宠
    def open_pet_th():
        try:
            app = QApplication(sys.argv)
            pet_window = Live2dPet()
            pet_window.show()
            sys.exit(app.exec())
        except Exception:
            messagebox.showinfo("提示", "由于桌宠模块自身原因\n请重启软件再打开桌宠")

    Thread(target=open_pet_th).start()


def stream_insert(text):  # 流式输出
    def show_in_pet():
        for window in QApplication.topLevelWidgets():
            if isinstance(window, Live2dPet):
                text2 = text.replace("\n", "").replace(f"{mate_name}:", "").strip()
                window.show_chat_response(text2)
                wait_time = len(text2) / 4
                if wait_time > 30:
                    wait_time = 30
                time.sleep(wait_time)
                break

    def insert_char(char):
        output_box.insert("end", char)
        output_box.see("end")

    def threaded_insert():
        if pet_subtitle_switch == "on":
            Thread(target=show_in_pet).start()
        for char in text:
            insert_char(char)
            time.sleep(0.01)

    Thread(target=threaded_insert).start()


def export_chat():  # 导出对话
    chat_records = output_box.get("1.0", "end")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_path = fd.asksaveasfilename(defaultextension='.txt', filetypes=[('Text Files', '*.txt')],
                                     initialfile=f'枫云AI虚拟伙伴{mate_name}对话记录{timestamp}')
    if file_path:
        with open(file_path, 'w', encoding='utf-8') as chat_file:
            chat_file.write(chat_records)
            notice(f"{mate_name}对话记录导出成功")


def up_photo():  # 上传图片
    file_path = fd.askopenfilename(title="选择一张PNG图片提问AI", filetypes=[("PNG文件", "*.png")])
    if file_path:
        target_path = "data/cache/cache.png"
        shutil.copy(file_path, target_path)
        notice(f"图片上传成功，请发送包含“图片”二字的消息提问AI")
        messagebox.showinfo("提示", "图片上传成功\n请发送包含“图片”二字的消息提问AI")


def open_chatweb():  # 打开对话网页
    if chat_web_switch == "关闭":
        messagebox.showinfo("提示", "请前往软件设置打开对话网页开关")
        return
    wb.open(f"http://127.0.0.1:{chatweb_port}")


def cloud_function_llm(function_prompt, msg):  # 大语言模型云功能函数
    client = ZhipuAI(api_key=glm_key)
    messages = [{"role": "user", "content": msg}, {"role": "system", "content": function_prompt}]
    completion = client.chat.completions.create(model=glm_llm_model, messages=messages)
    return completion.choices[0].message.content.replace("#", "").replace("*", "").strip()


# open_source_project_address:https://github.com/swordswind/ai_virtual_mate_web
def function_llm(function_prompt, msg):  # 大语言模型功能函数
    function_prompt = function_prompt + "/no_think"
    messages = [{"role": "system", "content": function_prompt}, {"role": "user", "content": msg}]
    try:
        if llm_menu.get() == "GLM-4-Flash":
            client = ZhipuAI(api_key=glm_key)
            completion = client.chat.completions.create(model=glm_llm_model, messages=messages)
        elif llm_menu.get() == "通义千问3-8B":
            client = OpenAI(base_url=sf_url, api_key=sf_key)
            completion = client.chat.completions.create(model="Qwen/Qwen3-8B", messages=messages)
        elif llm_menu.get() == "文心一言Speed":
            client = OpenAI(base_url=bd_url, api_key=bd_key)
            completion = client.chat.completions.create(model=bd_model, messages=messages)
        elif llm_menu.get() == "腾讯混元Lite":
            client = OpenAI(base_url=hy_url, api_key=hy_key)
            completion = client.chat.completions.create(model=hy_model, messages=messages)
        elif llm_menu.get() == "讯飞星火Lite":
            client = OpenAI(base_url=xf_url, api_key=xf_key)
            completion = client.chat.completions.create(model=xf_model, messages=messages)
        elif llm_menu.get() == "本地LM Studio":
            client = OpenAI(base_url=f"http://{local_llm_ip}:{lmstudio_port}/v1", api_key="lm-studio")
            completion = client.chat.completions.create(model="", messages=messages)
        elif llm_menu.get() == "本地Transformers":
            client = OpenAI(base_url=f"http://{local_llm_ip}:{tf_port}/v1", api_key="transformers")
            completion = client.chat.completions.create(model=tf_model, messages=messages)
            chunks = re.findall(r'^data:\s*(.+)$', completion, flags=re.MULTILINE)
            result_content = []
            for chunk in chunks:
                try:
                    data = json.loads(chunk)
                    content = data.get("choices", [{}])[0].get("delta", {}).get("content")
                    if content is not None:
                        result_content.append(content)
                except json.JSONDecodeError:
                    continue
            res = "".join(result_content).replace("\n", "")
            if think_filter_switch == "on":
                res = res.split("</think>")[-1].strip()
            return res.replace("#", "").replace("*", "")
        elif llm_menu.get() == "本地Ollama LLM":
            client = Client(host=f'http://{local_llm_ip}:{ollama_port}')
            response = client.chat(model=ollama_model_name, messages=messages)
            res = response['message']['content']
            if think_filter_switch == "on":
                res = res.split("</think>")[-1].strip()
            return res.replace("#", "").replace("*", "")
        elif llm_menu.get() == "自定义API-LLM":
            client = OpenAI(base_url=custom_url, api_key=custom_key)
            completion = client.chat.completions.create(model=custom_model, messages=messages)
        else:
            return f"[{llm_menu.get()}未适配{mode_menu.get()}，可选择其他对话模型]"
        res = completion.choices[0].message.content
        if think_filter_switch == "on":
            res = res.split("</think>")[-1].strip()
        return res.replace("#", "").replace("*", "").strip()
    except Exception as e:
        return f"[{llm_menu.get()}服务未正确设置，错误详情：{e}]"


def voice_input(text):  # 语音输入
    content = text.replace("语音输入", "")
    for char in content:
        kb.write(char)
        time.sleep(0.01)


def vol_up():  # 调高音量
    try:
        current_volume = volume.GetMasterVolumeLevelScalar()
        volume.SetMasterVolumeLevelScalar(current_volume + 0.15, None)
        current_volume += 0.15
        notice(f"{mate_name}已把[音量]调大至{int(current_volume * 100)}%")
    except:
        notice(f"{mate_name}已把[音量]调至最大")


def vol_down():  # 调低音量
    try:
        current_volume = volume.GetMasterVolumeLevelScalar()
        volume.SetMasterVolumeLevelScalar(current_volume - 0.15, None)
        current_volume -= 0.15
        notice(f"{mate_name}已把[音量]调小至{int(current_volume * 100)}%")
    except:
        notice(f"{mate_name}已把[音量]调至最小")


def open_vmd_music():  # 打开MMD 3D动作音乐
    wb.open(f"http://127.0.0.1:{mmd_port}/vmd")
    if vmd_music_switch == "on":
        pg.mixer.init()
        try:
            vmd_music = pg.mixer.Sound(f'data/music_vmd/{vmd_music_name}')
            vmd_music.play()
        except:
            messagebox.showinfo("MMD 3D音乐名称配置错误", "请前往软件设置→更多设置正确配置MMD 3D动作音乐")


def open_web_tips():  # 打开手机访问网页提示
    text1 = "使用手机访问AI虚拟伙伴，无需下载APP\n\n保持手机和本电脑处于同一WiFi/局域网\n\n根据需求，在手机浏览器输入下列网址即可便捷访问"
    if chat_web_switch == "开启":
        text2 = f"对话网址: http://{server_ip}:{chatweb_port}\nLive2D角色网址: http://{server_ip}:{live2d_port}\nMMD 3D角色网址: http://{server_ip}:{mmd_port}\nVRM 3D角色网址: http://{server_ip}:{vrm_port}\nMMD 3D动作网址: http://{server_ip}:{mmd_port}/vmd"
    else:
        text2 = f"对话网址: 未开启\nLive2D角色网址: http://{server_ip}:{live2d_port}\nMMD 3D角色网址: http://{server_ip}:{mmd_port}\nVRM 3D角色网址: http://{server_ip}:{vrm_port}\nMMD 3D动作网址: http://{server_ip}:{mmd_port}/vmd"
    text3 = "不仅手机能访问，\n同一WiFi或局域网下的电脑/平板/电视/手表/车机如果内置浏览器，\n也可通过输入上述网址访问AI虚拟伙伴\n\n网页端在非本电脑的其他设备上默认情况下仅支持打字聊天和显示角色，不支持语音识别、语音输出和摄像头识别。如需串流其他设备，推荐使用AudioReplay和iVCam软件"
    text = text1 + "\n\n" + text2 + "\n\n" + text3
    msg_box("手机网页访问 - 枫云AI虚拟伙伴Web版", text)
