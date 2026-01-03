import logging
from flask import Flask, request, render_template_string, jsonify, send_from_directory
from llm import *
from tts import *

app = Flask(__name__)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
web_chat_history = []


@app.route('/data/image/<path:filename>')
def serve_image(filename):
    return send_from_directory("data/image", filename)


@app.route('/dist/assets/image/<path:filename>')
def serve_bg_image(filename):
    return send_from_directory("dist/assets/image", filename)


@app.route("/", methods=["GET", "POST"])
def index():
    global web_chat_history
    if request.method == "POST":
        data = request.get_json()
        action = data.get("action")
        if action == "poll":
            return jsonify(web_chat_history)
        elif action == "send":
            user_text = data.get("text", "").strip()
            if not user_text:
                return jsonify({"error": "请输入内容"})
            web_chat_history.append((username, user_text))  # 立即显示用户消息
            Thread(target=handle_bot_reply, args=(user_text,), daemon=True).start()  # 异步处理虚拟伙伴的回复
            return jsonify(web_chat_history)
        elif action == "clear":
            web_chat_history = []
            return jsonify({"status": "success"})
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>对话 - 枫云AI虚拟伙伴Web版</title>
        <link rel="icon" href="/data/image/logo.png" type="image/png">
        <style>
        body{font-family:'Arial',sans-serif;margin:0;padding:0;background-color:#f5f7fa;color:#333;
            background-image: url('/dist/assets/image/bg.jpg');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            background-repeat: no-repeat;
            position: relative;
        }
        body::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(245, 247, 250, 0.25);
            z-index: -1;
        }
        .header{background-color:rgba(88, 126, 244, 0.25);color:white;padding:15px 20px;box-shadow:0 2px 5px rgba(0,0,0,0.1);position:relative;}
        .header h1{margin:0;font-size:24px;font-weight:600;display:inline-flex;align-items:center;}
        .header-logo{width:32px;height:32px;margin-right:10px;vertical-align:middle;}
        .header-info{margin-top:10px;font-size:14px;}
        .header-info a{color:#fff;text-decoration:none;margin-right:10px;background-color:rgba(255,255,255,0.15);padding:5px 10px;border-radius:4px;transition:background-color 0.3s;}
        .header-info a:hover{background-color:rgba(255,255,255,0.25);}
        .header-info button{background-color:rgba(255,255,255,0.25);border:none;color:white;padding:5px 10px;border-radius:4px;cursor:pointer;font-size:12px;margin-right:10px;transition:background-color 0.3s;}
        .header-info button:hover{background-color:rgba(255,255,255,0.3);}
        .chat-container{height:calc(100vh - 180px);overflow-y:auto;padding:15px;background-color:rgba(255, 255, 255, 0.25);margin:10px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);}
        .message{margin-bottom:15px;padding:10px 15px;border-radius:18px;max-width:80%;word-wrap:break-word;line-height:1.4;display:flex;align-items:flex-start;}
        .user-message{background-color:rgba(88, 126, 244, 0.25);color:white;margin-left:auto;border-bottom-right-radius:4px;max-width:33%;}
        .bot-message{background-color:rgba(240, 242, 245, 0.25);margin-right:auto;border-bottom-left-radius:4px;max-width:33%;}
        .message-avatar{width:36px;height:36px;border-radius:50%;margin-right:10px;flex-shrink:0;}
        .user-message .message-avatar{margin-left:10px;margin-right:0;order:2;}
        .message-content{flex-grow:1;}
        .message-sender{font-weight:bold;margin-bottom:5px;font-size:14px;}
        .input-area{position:fixed;bottom:0;left:0;right:0;background-color:rgba(255, 255, 255, 0.25);padding:15px;box-shadow:0 -2px 5px rgba(0,0,0,0.1);display:flex;align-items:center;}
        #msgInput{flex:1;padding:12px 15px;border:1px solid rgba(221, 221, 221, 0.5);border-radius:24px;outline:none;font-size:16px;margin-right:10px;background-color:rgba(255, 255, 255, 0.5);}
        #msgInput:focus{border-color:#587EF4;}
        .send-btn{background-color:rgba(88, 126, 244, 0.25);color:white;border:none;padding:12px 20px;border-radius:24px;cursor:pointer;font-weight:bold;transition:background-color 0.3s;}
        .send-btn:hover{background-color:rgba(71, 104, 201, 0.3);}
        .new-chat-btn{background-color:rgba(88, 126, 244, 0.25);color:white;border:none;padding:12px 15px;border-radius:50%;cursor:pointer;font-weight:bold;transition:background-color 0.3s;margin-right:10px;width:45px;height:45px;display:flex;align-items:center;justify-content:center;font-size:20px;}
        .new-chat-btn:hover{background-color:rgba(71, 104, 201, 0.3);}
        .mate-avatar{width:40px;height:40px;border-radius:50%;margin-right:10px;vertical-align:middle;}
        .header-content{display:flex;align-items:center;}
        .ai-disclaimer {
            position: fixed;
            bottom: 70px;
            left: 15px;
            font-size: 12px;
            color: #666;
            z-index: 10;
        }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <img class="mate-avatar" src="/data/image/ch/{{ mate_name }}.png" alt="{{ mate_name }}的头像">
                <div>
                    <h1>{{ mate_name }}</h1>
                    <div class="header-info">
                        <a href="http://{{server_ip}}:{{live2d_port}}" target="_blank">Live2D角色</a>
                        <a href="http://{{server_ip}}:{{mmd_port}}" target="_blank">MMD 3D角色</a>
                        <a href="http://{{server_ip}}:{{mmd_port}}/vmd" target="_blank">MMD 3D动作</a>
                        <a href="http://{{server_ip}}:{{vrm_port}}" target="_blank">VRM 3D角色</a>
                    </div>
                </div>
            </div>
        </div>
        <div class="chat-container" id="chat"></div>
        <div class="input-area">
            <button class="new-chat-btn" onclick="clearChat()" title="开启新对话">+</button>
            <input id="msgInput" placeholder="和{{ mate_name }}聊天...">
            <button class="send-btn" onclick="sendMsg()">发送</button>
        </div>
        <div class="ai-disclaimer">内容由AI生成,请仔细甄别</div>
        <script>
            let userName = "{{ username }}";
            let mateName = "{{ mate_name }}";
            setInterval(() => {
                fetch("/", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({action: "poll"})
                })
                .then(r => r.json())
                .then(data => {
                    if(Array.isArray(data)) {
                        const chat = document.getElementById("chat");
                        chat.innerHTML = "";
                        data.forEach(([who, text]) => {
                            const messageDiv = document.createElement("div");
                            messageDiv.className = who === userName ? "message user-message" : "message bot-message";
                            const avatarImg = document.createElement("img");
                            avatarImg.className = "message-avatar";
                            avatarImg.alt = who + "的头像";
                            avatarImg.src = who === userName 
                                ? "/data/image/ch/" + userName + ".png" 
                                : "/data/image/ch/" + mateName + ".png";
                            const contentDiv = document.createElement("div");
                            contentDiv.className = "message-content";
                            const senderDiv = document.createElement("div");
                            senderDiv.className = "message-sender";
                            senderDiv.textContent = who;
                            const textDiv = document.createElement("div");
                            textDiv.innerHTML = text.replace(/\\n/g, "<br>");
                            contentDiv.appendChild(senderDiv);
                            contentDiv.appendChild(textDiv);
                            messageDiv.appendChild(avatarImg);
                            messageDiv.appendChild(contentDiv);
                            chat.appendChild(messageDiv);
                        });
                        chat.scrollTop = chat.scrollHeight;
                    }
                });
            }, 1000);
            function sendMsg() {
                const text = document.getElementById("msgInput").value.trim();
                if(!text) { 
                    alert("请输入内容"); 
                    return; 
                }
                fetch("/", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({action: "send", user: userName, text: text})
                })
                .then(r => r.json())
                .then(() => {
                    document.getElementById("msgInput").value = "";
                });
            }
            function clearChat() {
                if (confirm("确定要清空网页聊天记录吗？")) {
                    fetch("/", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({action: "clear"})
                    })
                    .then(r => r.json())
                    .then(data => {
                        if (data.status === "success") {
                            const chat = document.getElementById("chat");
                            chat.innerHTML = "";
                        }
                    });
                }
            }
            document.getElementById("msgInput").addEventListener("keydown", e => {
                if(e.key === "Enter" && !e.shiftKey) { 
                    e.preventDefault(); 
                    sendMsg(); 
                }
            });
        </script>
    </body>
    </html>'''
    return render_template_string(html, server_ip=server_ip, live2d_port=live2d_port, mmd_port=mmd_port,
                                  vrm_port=vrm_port, username=username, mate_name=mate_name)


# open_source_project_address:https://github.com/swordswind/ai_virtual_mate_web
def handle_bot_reply(user_text):
    global web_chat_history
    bot_reply = chat_llm(user_text)
    bot_reply = bot_reply.replace("#", "").replace("*", "")
    web_chat_history.append((mate_name, bot_reply))
    get_tts_play(bot_reply)


def run_chatweb():
    app.run(host="0.0.0.0", port=chatweb_port)


app_pet = Flask(__name__)


@app_pet.get('/pet_chat')
def pet_chat():
    if asr_menu.get() == "实时语音识别" and tts_menu.get() != "关闭语音合成":
        return jsonify({"error": "请关闭实时语音识别或关闭语音合成后\n再打字发送"}), 500
    msg = request.args.get('msg')
    key = request.args.get('key')
    if not msg:
        return jsonify({"error": "缺少msg参数"}), 400
    if not key or key != 'desktoppetchat':
        return jsonify({"error": "无效的key参数"}), 401
    try:
        answer = chat_preprocess(msg)
        get_tts_play(answer)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": f"处理请求时出错: {e}"}), 500


def run_pet_chat():
    app_pet.run(host='127.0.0.1', port=5249)


Thread(target=run_pet_chat).start()
