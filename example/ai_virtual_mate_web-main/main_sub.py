from agent import *


def common_chat(msg):  # 通用对话
    output_box.insert("end", f"\n{username}:\n    {msg}\n")
    output_box.see("end")
    notice(f"{mate_name}正在思考中，请稍等...")
    if mode_menu.get() == "多智能体助手":
        user_task = user_intent_recognition(msg)
        notice(f"{mate_name}调用了[{user_task}]智能体")
        task_handlers = {
            "音乐播放": (play_music, (msg,)), "语音输入": (voice_input, (msg,)),
            "打开软件/网页": (open_app_select, (msg,)), "音量减小": (vol_down, ()), "音量增大": (vol_up, ()),
            "文本写作": (auto_input, (msg,)), "翻译屏幕内容": (translate_screen, (msg,)),
            "解释屏幕内容": (explain_screen, (msg,)), "总结屏幕内容": (summary_screen, (msg,)),
            "续写屏幕内容": (continue_write_screen, (msg,)), "灯类智能家居控制": (control_ha, ()),
            "天气查询": (get_weather, (msg,)), "热搜新闻": (get_news, (msg,)),
            "系统状态查询": (get_system_state, (msg,)), "联网搜索": (ol_search, (msg,)),
            "视频生成": (generate_video, (msg,))}
        for task, (handler, args) in task_handlers.items():
            if task in user_task:
                handler(*args)
                break
        else:
            normal_chat(msg)
    else:
        normal_chat(msg)


def normal_chat(msg):  # 普通对话
    bot_response = chat_preprocess(msg)
    bot_response = bot_response.replace("#", "").replace("*", "")
    stream_insert(f"{mate_name}:\n    {bot_response}\n")
    get_tts_play(bot_response)


# open_source_project_address:https://github.com/swordswind/ai_virtual_mate_web
def open_app_select(msg):  # 打开软件
    def find_app_path(app_path):
        possible_paths = [
            f"C:/Program Files (x86)/{app_path}", f"C:/Program Files/{app_path}", f"D:/Program Files (x86)/{app_path}",
            f"D:/Program Files/{app_path}", f"E:/Program Files (x86)/{app_path}", f"E:/Program Files/{app_path}",
            f"F:/Program Files (x86)/{app_path}", f"F:/Program Files/{app_path}",
            os.path.join(os.environ['APPDATA'], app_path)]
        for path2 in possible_paths:
            if os.path.exists(path2):
                return path2
        return None

    def open_app(app_name2, app_path):
        app_full_path = find_app_path(app_path)
        if app_full_path:
            Popen(app_full_path)
            notice(f"{mate_name}打开了{app_name2}")
            get_tts_play(f"好的，已为您打开{app_name2}")
        else:
            stream_insert(f"{mate_name}:\n    未找到{app_name2}安装路径\n")
            notice(f"未找到{app_name2}安装路径")
            get_tts_play(f"未找到{app_name2}安装路径")

    app_mappings = {
        '微信': ('微信', 'Tencent/Weixin/Weixin.exe'), 'QQ': ('QQ', 'Tencent/QQNT/QQ.exe'),
        '文档': ('Word文档', 'Microsoft Office/root/Office16/WINWORD.EXE'),
        '音乐': ('网易云音乐', 'NetEase/CloudMusic/cloudmusic.exe'),
        '崩坏': ('崩坏：星穹铁道', 'miHoYo Launcher/games/Star Rail Game/StarRail.exe'),
        '原神': ('原神', 'miHoYo Launcher/games/Genshin Impact Game/YuanShen.exe'),
        '绝区零': ('绝区零', 'miHoYo Launcher/games/ZenlessZoneZero Game/ZenlessZoneZero.exe'),
        '记事本': ('记事本', None), '便签': ('记事本', None), '备忘录': ('记事本', None), '笔记': ('记事本', None),
        '计算器': ('计算器', None), '文件管理': ('资源管理器', None), '资源管理': ('资源管理器', None),
        '任务管理': ('任务管理器', None), '画图': ('画图工具', None), '绘图': ('画图工具', None), '控制面板': ('控制面板', None)}
    special_commands = {'悟空': ('黑神话：悟空', 'steam://rungameid/2358720', wb.open),
                        '我的世界': ('我的世界', 'fevergames://mygame/?gameId=1', wb.open)}
    builtin_commands = {
        '记事本': ('notepad', Popen), '计算器': ('calc', Popen), '资源管理器': ('explorer', Popen),
        '任务管理器': ('taskmgr', Popen), '画图工具': ('mspaint', Popen), '控制面板': ('control', Popen)}
    for keyword, (app_name, path, func) in special_commands.items():
        if keyword in msg:
            func(path)
            notice(f"{mate_name}打开了{app_name}")
            get_tts_play(f"好的，已为您打开{app_name}")
            return
    for keyword, (app_name, path) in app_mappings.items():
        if keyword in msg:
            if path is None:
                cmd, func = builtin_commands[app_name]
                func(cmd)
                notice(f"{mate_name}打开了{app_name}")
                get_tts_play(f"好的，已为您打开{app_name}")
            else:
                open_app(app_name, path)
            return
    try:
        content = function_llm(
            "请你扮演一个Windows CMD命令转换器。每当我输入自然语言命令时，你必须仅输出对应的CMD命令，不能添加任何其他文字或说明。",
            msg)
        result = os.system(content)
        if result == 0:
            notice(f"{mate_name}接管了电脑")
        else:
            text_to_cmd_error = "抱歉，这个我还不会，可尝试更换对话语言模型"
            stream_insert(f"{mate_name}:\n    {text_to_cmd_error}\n")
            notice(text_to_cmd_error)
            get_tts_play(text_to_cmd_error)
    except:
        text_to_cmd_error = "暂不支持打开该软件"
        stream_insert(f"{mate_name}:\n    {text_to_cmd_error}\n")
        notice(text_to_cmd_error)
        get_tts_play(text_to_cmd_error)
