import random
from llm import *
from tts import *


def ase_chat(msg):  # 主动对话
    stop_tts()
    bot_response = chat_preprocess(msg)
    notice(f"{mate_name}主动感知并发起了聊天")
    stream_insert(f"{mate_name}:\n    {bot_response}\n")
    get_tts_play(bot_response)


def ase_hello():  # 根据时间发起话题
    current_hour = datetime.now().time().hour
    time_area = {(0, 6): "夜深了睡不着，你来发起聊天话题吧。", (6, 9): "早上好呀，你来发起聊天话题吧。",
                 (9, 11): "上午好呀，你来发起聊天话题吧。", (11, 13): "中午好呀，你来发起聊天话题吧。",
                 (13, 17): "下午好呀，你来发起聊天话题吧。", (17, 19): "傍晚好呀，你来发起聊天话题吧。",
                 (19, 24): "晚上好呀，你来发起聊天话题吧。"}
    for (start, end), hello_msg in time_area.items():
        if start <= current_hour < end:
            ase_chat(hello_msg)
            break


# open_source_project_address:https://github.com/swordswind/ai_virtual_mate_web
def run_ase_rp():  # 角色扮演聊天模式的主动对话
    def ase_vlm_screen():
        ase_chat(
            f"你是我的有情感的贴心伙伴，名叫{mate_name}。需要称呼我为{username}，在对话中，你将作为{mate_name}，隐藏自己是程序的事实。注意保持角色一致，不能提及任何关于自己是语言模型或人工智能的话题。回答不要超过50个字，性格为亲切活泼。请你读取屏幕画面，务必结合其中内容和我聊聊天，比如点评屏幕中的内容。")

    def ase_vlm_cam():
        ase_chat(
            f"你是我的有情感的贴心伙伴，名叫{mate_name}。需要称呼我为{username}，在对话中，你将作为{mate_name}，隐藏自己是程序的事实。注意保持角色一致，不能提及任何关于自己是语言模型或人工智能的话题。回答不要超过50个字，性格为亲切活泼。请你读取你看到的摄像头内容，务必根据其中的内容和我聊聊天，比如点评看到的人物行为和场景。")

    def ase_context():
        ase_chat("你是我的有情感的贴心伙伴，请你结合上下文和人设，主动向我发起聊天话题。")

    while True:
        if ase_menu.get() != "不主动" and mode_menu.get() == "角色扮演聊天":
            time_ranges = {"高活跃": (60, 120), "中活跃": (240, 360)}
            time_range = time_ranges.get(ase_menu.get(), (480, 660))
            if cam_permission == "开启":
                ase_function = random.choice([ase_hello, ase_vlm_screen, ase_vlm_cam, ase_context])
            else:
                ase_function = random.choice([ase_hello, ase_vlm_screen, ase_context])
            ase_function()
            time.sleep(random.randint(*time_range))
        time.sleep(0.1)


def run_ase_agent():  # 多智能体助手模式的主动对话
    def ase_vlm_cam():
        ase_chat(
            f"你是我的有情感的贴心伙伴，名叫{mate_name}。需要称呼我为{username}，在对话中，你将作为{mate_name}，隐藏自己是程序的事实。注意保持角色一致，不能提及任何关于自己是语言模型或人工智能的话题。回答不要超过50个字，性格为亲切活泼。请你读取你看到的摄像头内容，务必根据其中的内容和我聊聊天，比如点评看到的人物行为和场景。")

    def ase_news():
        ase_chat("你有什么感兴趣的新闻吗，选择一条你感兴趣的和我聊聊天")

    def ase_weather():
        ase_chat(f"请你结合{weather_city}天气信息，和我发起话题简短聊聊天，例如提出生活或出行建议")

    while True:
        if ase_menu.get() != "不主动" and mode_menu.get() == "多智能体助手":
            time_ranges = {"高活跃": (60, 120), "中活跃": (240, 360)}
            time_range = time_ranges.get(ase_menu.get(), (480, 660))
            if cam_permission == "开启":
                ase_function = random.choice([ase_hello, ase_weather, ase_vlm_cam, ase_news])
            else:
                ase_function = random.choice([ase_hello, ase_weather, ase_news])
            ase_function()
            time.sleep(random.randint(*time_range))
        time.sleep(0.1)
