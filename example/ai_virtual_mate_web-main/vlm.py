import cv2
import numpy as np
from base64 import b64encode
from function import *

img_path = "data/cache/cache.jpg"
photo_path = "data/cache/cache.png"


def function_vlm(msg):  # 多模态大模型功能函数
    vlm_handlers = {
        "GLM-4V-Flash": glm_4v_screen, "本地Ollama VLM": ollama_vlm_screen, "本地LM Studio": lmstudio_vlm_screen,
        "本地QwenVL整合包": qwen_vlm_screen, "本地Janus整合包": janus_screen}
    try:
        handler = vlm_handlers.get(img_menu.get(), custom_vlm_screen)
        return handler(msg).replace("#", "").replace("*", "")
    except Exception as e:
        return f"图像识别引擎配置错误，错误详情：{e}"


def glm_4v_cam(question):  # 多模态摄像头画面聊天
    cap = cv2.VideoCapture(cam_num, cv2.CAP_DSHOW)
    if not cap.isOpened():
        return "无法打开摄像头"
    ret, frame = cap.read()
    cap.release()
    base64_image = encode_image(frame)
    messages = [{"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {
        "url": f"data:image/png;base64,{base64_image}"}}]}]
    vlm_client = ZhipuAI(api_key=glm_key)
    completion = vlm_client.chat.completions.create(model=glm_vlm_model, messages=messages)
    return completion.choices[0].message.content


def glm_4v_screen(question):  # 多模态屏幕画面聊天
    screenshot = pag.screenshot()
    screenshot_np = np.array(screenshot)
    screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
    base64_image = encode_image(screenshot_bgr)
    messages = [{"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {
        "url": f"data:image/png;base64,{base64_image}"}}]}]
    vlm_client = ZhipuAI(api_key=glm_key)
    completion = vlm_client.chat.completions.create(model=glm_vlm_model, messages=messages)
    return completion.choices[0].message.content


def ollama_vlm_cam(question):
    try:
        rq.get(f'http://{local_vlm_ip}:{ollama_port}')
    except:
        Popen(f"ollama pull {ollama_vlm_name}", shell=False)
    cap = cv2.VideoCapture(cam_num, cv2.CAP_DSHOW)
    if not cap.isOpened():
        return "无法打开摄像头"
    ret, frame = cap.read()
    cap.release()
    _, buffer = cv2.imencode('.jpg', frame)  # 将图片转换为字节流
    byte_data = buffer.tobytes()
    client = Client(host=f'{local_vlm_ip}:{ollama_port}')
    response = client.chat(model=ollama_vlm_name,
                           messages=[{'role': 'user', 'content': question, 'images': [byte_data]}])
    return response['message']['content']


def ollama_vlm_screen(question):
    try:
        rq.get(f'http://{local_vlm_ip}:{ollama_port}')
    except:
        Popen(f"ollama pull {ollama_vlm_name}", shell=False)
    screenshot = pag.screenshot()
    screenshot.save(img_path, "JPEG")
    with open(img_path, 'rb') as f:
        image = f.read()
    os.remove(img_path)
    client = Client(host=f'{local_vlm_ip}:{ollama_port}')
    response = client.chat(model=ollama_vlm_name,
                           messages=[{'role': 'user', 'content': question, 'images': [image]}])
    return response['message']['content']


def lmstudio_vlm_cam(question):
    cap = cv2.VideoCapture(cam_num, cv2.CAP_DSHOW)
    if not cap.isOpened():
        return "无法打开摄像头"
    ret, frame = cap.read()
    cap.release()
    base64_image = encode_image(frame)
    messages = [{"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {
        "url": f"data:image/png;base64,{base64_image}"}}]}]
    vlm_client = OpenAI(base_url=f"http://{local_vlm_ip}:{lmstudio_port}/v1", api_key="lm-studio")
    completion = vlm_client.chat.completions.create(model="", messages=messages)
    return completion.choices[0].message.content


def lmstudio_vlm_screen(question):
    screenshot = pag.screenshot()
    screenshot_np = np.array(screenshot)
    screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
    base64_image = encode_image(screenshot_bgr)
    messages = [{"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {
        "url": f"data:image/png;base64,{base64_image}"}}]}]
    vlm_client = OpenAI(base_url=f"http://{local_vlm_ip}:{lmstudio_port}/v1", api_key="lm-studio")
    completion = vlm_client.chat.completions.create(model="", messages=messages)
    return completion.choices[0].message.content


def qwen_vlm_cam(question):
    cap = cv2.VideoCapture(cam_num, cv2.CAP_DSHOW)
    if not cap.isOpened():
        return "无法打开摄像头"
    ret, frame = cap.read()
    cap.release()
    _, buffer = cv2.imencode('.jpg', frame)
    base64_image = b64encode(buffer).decode('utf-8')
    data = {"image": f"data:image/jpeg;base64,{base64_image}", "msg": question}
    response = rq.post(f"http://{local_vlm_ip}:8086/qwen_vl", json=data)
    return response.json()["answer"]


# open_source_project_address:https://github.com/swordswind/ai_virtual_mate_web
def qwen_vlm_screen(question):
    screenshot = pag.screenshot()
    screenshot.save(img_path, "JPEG")
    with open(img_path, "rb") as image_file:
        base64_image = b64encode(image_file.read()).decode('utf-8')
    data = {"image": f"data:image/jpeg;base64,{base64_image}", "msg": question}
    os.remove(img_path)
    response = rq.post(f"http://{local_vlm_ip}:8086/qwen_vl", json=data)
    return response.json()["answer"]


def janus_cam(question):
    cap = cv2.VideoCapture(cam_num, cv2.CAP_DSHOW)
    if not cap.isOpened():
        return "无法打开摄像头"
    ret, frame = cap.read()
    cap.release()
    _, buffer = cv2.imencode('.jpg', frame)
    files = {'file': ('image.jpg', buffer.tobytes(), 'image/jpeg')}
    data = {'question': question, 'seed': 42, 'top_p': 0.95, 'temperature': 0.1}
    response = rq.post(f"http://{local_vlm_ip}:8082/understand_image_and_question/", files=files, data=data)
    return response.json()['response']


def janus_screen(question):
    screenshot = pag.screenshot()
    screenshot.save(img_path, "JPEG")
    with open(img_path, 'rb') as image_file:
        files = {'file': image_file}
        data = {'question': question, 'seed': 42, 'top_p': 0.95, 'temperature': 0.1}
        response = rq.post(f"http://{local_vlm_ip}:8082/understand_image_and_question/", files=files, data=data)
    os.remove(img_path)
    return response.json()['response']


def encode_image(image):
    _, buffer = cv2.imencode('.png', image)
    return b64encode(buffer).decode('utf-8')


def custom_vlm_cam(question):
    cap = cv2.VideoCapture(cam_num, cv2.CAP_DSHOW)
    if not cap.isOpened():
        return "无法打开摄像头"
    ret, frame = cap.read()
    cap.release()
    base64_image = encode_image(frame)
    messages = [{"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {
        "url": f"data:image/png;base64,{base64_image}"}}]}]
    vlm_client = OpenAI(base_url=custom_url, api_key=custom_key)
    completion = vlm_client.chat.completions.create(model=custom_vlm, messages=messages)
    return completion.choices[0].message.content


def custom_vlm_screen(question):
    screenshot = pag.screenshot()
    screenshot_np = np.array(screenshot)
    screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
    base64_image = encode_image(screenshot_bgr)
    messages = [{"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {
        "url": f"data:image/png;base64,{base64_image}"}}]}]
    vlm_client = OpenAI(base_url=custom_url, api_key=custom_key)
    completion = vlm_client.chat.completions.create(model=custom_vlm, messages=messages)
    return completion.choices[0].message.content


def glm_4v_photo(question):  # 多模态大模型图片聊天
    with open(photo_path, "rb") as image_file:
        base64_image = b64encode(image_file.read()).decode('utf-8')
    messages = [{"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {
        "url": f"data:image/png;base64,{base64_image}"}}]}]
    vlm_client = ZhipuAI(api_key=glm_key)
    completion = vlm_client.chat.completions.create(model=glm_vlm_model, messages=messages)
    return completion.choices[0].message.content


def ollama_vlm_photo(question):
    try:
        rq.get(f'http://{local_vlm_ip}:{ollama_port}')
    except:
        Popen(f"ollama pull {ollama_vlm_name}", shell=False)
    with open(photo_path, 'rb') as f:
        image = f.read()
    client = Client(host=f'{local_vlm_ip}:{ollama_port}')
    response = client.chat(model=ollama_vlm_name,
                           messages=[{'role': 'user', 'content': question, 'images': [image]}])
    return response['message']['content']


def lmstudio_vlm_photo(question):
    with open(photo_path, "rb") as image_file:
        base64_image = b64encode(image_file.read()).decode('utf-8')
    messages = [{"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {
        "url": f"data:image/png;base64,{base64_image}"}}]}]
    vlm_client = OpenAI(base_url=f"http://{local_vlm_ip}:{lmstudio_port}/v1", api_key="lm-studio")
    completion = vlm_client.chat.completions.create(model="", messages=messages)
    return completion.choices[0].message.content


def qwen_vlm_photo(question):
    with open(photo_path, "rb") as image_file:
        base64_image = b64encode(image_file.read()).decode('utf-8')
    data = {"image": f"data:image/jpeg;base64,{base64_image}", "msg": question}
    response = rq.post(f"http://{local_vlm_ip}:8086/qwen_vl", json=data)
    return response.json()["answer"]


def janus_photo(question):
    with open(photo_path, 'rb') as image_file:
        files = {'file': image_file}
        data = {'question': question, 'seed': 42, 'top_p': 0.95, 'temperature': 0.1}
        response = rq.post(f"http://{local_vlm_ip}:8082/understand_image_and_question/", files=files, data=data)
    return response.json()['response']


def custom_vlm_photo(question):
    with open(photo_path, "rb") as image_file:
        base64_image = b64encode(image_file.read()).decode('utf-8')
    messages = [{"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {
        "url": f"data:image/png;base64,{base64_image}"}}]}]
    vlm_client = OpenAI(base_url=custom_url, api_key=custom_key)
    completion = vlm_client.chat.completions.create(model=custom_vlm, messages=messages)
    return completion.choices[0].message.content
