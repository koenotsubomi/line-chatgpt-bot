from flask import Flask, request, abort
import os
import openai
import json
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FollowEvent, FlexSendMessage, PostbackEvent
)

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "こえのつぼみLINEボットは正常に動作しています🌱"

# 環境変数からAPIキー等を取得
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

COURSE_FILE = "user_courses.json"

# ユーザーコースの読み書き関数
def load_courses():
    if not os.path.exists(COURSE_FILE):
        return {}
    with open(COURSE_FILE, 'r') as f:
        return json.load(f)

def save_courses(data):
    with open(COURSE_FILE, 'w') as f:
        json.dump(data, f)

@app.route("/webhook", methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(FollowEvent)
def handle_follow(event):
    text = (
        "🌱こえのつぼみへようこそ🌱\n\n"
        "ご登録ありがとうございます✨\n\n"
        "あなたが「話してみよう」と\n"
        "一歩踏み出されたこと\n"
        "とても素晴らしいことです🌷\n\n"
        "ここはママの心が\n"
        "ふっと軽くなるような\n"
        "やさしい場所\n"
        "でありたいと思っています😊\n\n"
        "まずは、あなたに合った\n"
        "「お話スタイル」を選んでみてください🍀\n\n"
        "あなたの思いはこぼしていいんです"\n"
    )
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    course_flex = FlexSendMessage(
        alt_text="お話スタイルを選んでください",
        contents={
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    { "type": "text", "text": "お話スタイルを選んでください", "weight": "bold", "size": "md" },
                    { "type": "button", "action": { "type": "postback", "label": "☕そっとこぼす", "data": "course=sotto" }, "style": "primary" },
                    { "type": "button", "action": { "type": "postback", "label": "🤝寄り添い", "data": "course=yorisoi" }, "style": "primary" },
                    { "type": "button", "action": { "type": "postback", "label": "🔥喝とやさしい", "data": "course=katsu" }, "style": "primary" },
                    { "type": "button", "action": { "type": "postback", "label": "🌈本気", "data": "course=honki" }, "style": "primary" }
                ]
            }
        }
    )
    line_bot_api.push_message(event.source.user_id, course_flex)

@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    if data.startswith("course="):
        selected = data.split("=")[1]
        user_id = event.source.user_id
        courses = load_courses()
        courses[user_id] = selected
        save_courses(courses)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"「{selected}」コースを選択しました。いつでも話しかけてくださいね🌷")
        )

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id
    courses = load_courses()
    selected = courses.get(user_id, "sotto")

    # コース別 system プロンプト
    prompts = {
        "sotto": "あなたは、子育てに疲れたママの声をそっと受け止めるやさしい聞き役です。否定せず、共感の言葉を短く返してください。",
        "yorisoi": "あなたは、がんばっているママを見守り、行動や想いを褒めるカウンセラーです。相手の努力や気持ちを認めて返してください。",
        "katsu": "あなたは、少し元気をなくしているママの背中をやさしく押す応援役です。前向きな一歩を踏み出せるメッセージを返してください。",
        "honki": "あなたは、人生を変えたいと願うママに寄り添うカウンセラーです。状況を聞き、一緒に考えていく返答をしてください。"
    }
    system_prompt = prompts.get(selected, prompts["sotto"])

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        reply_text = response.choices[0].message['content'].strip()
    except Exception as e:
        print(f"ChatGPT API error: {e}")
        reply_text = "ごめんなさい、少し時間をおいて再度お試しください。"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
