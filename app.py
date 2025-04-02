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
    return "こえのつぼみLINEボットは正常に動作しています\U0001F331"

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
    try:
        if not os.path.exists(COURSE_FILE):
            return {}
        with open(COURSE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"読み込みエラー: {e}")
        return {}

def save_courses(data):
    try:
        with open(COURSE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"保存エラー: {e}")

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
    text = TextSendMessage(text=(
        "\U0001F331こえのつぼみへようこそ\U0001F331\n\n"
        "ご登録ありがとうございます✨\n\n"
        "あなたが「話してみよう」と\n"
        "一歩踏み出されたこと\n"
        "とても素晴らしいことです\U0001F337\n\n"
        "ここはママの心がふっと軽くなる\n"
        "❛やさしい場❜\n"
        "でありたいと思っています😊\n\n"
        "まずはあなたに合った\n"
        "「お話スタイル」を\n"
        "選んでみてください\uD83C\uDFE0\n\n"
        "あなたの思いを\n"
        "たくさんこぼしてください☕"
    ))

    flex = FlexSendMessage(
        alt_text="お話スタイルを選んでください",
        contents={
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {"type": "text", "text": "お話スタイルを選んでください", "weight": "bold", "size": "md"},
                    {"type": "button", "action": {"type": "postback", "label": "☕そっとこぼす", "data": "course=sotto"}, "style": "primary"},
                    {"type": "button", "action": {"type": "postback", "label": "🤝寄り添い", "data": "course=yorisoi"}, "style": "primary"},
                    {"type": "button", "action": {"type": "postback", "label": "🔥喝とやさしい", "data": "course=katsu"}, "style": "primary"},
                    {"type": "button", "action": {"type": "postback", "label": "🌈本気", "data": "course=honki"}, "style": "primary"}
                ]
            }
        }
    )

    line_bot_api.reply_message(event.reply_token, [text, flex])

@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    if data.startswith("course="):
        selected = data.split("=")[1]
        user_id = event.source.user_id
        courses = load_courses()
        courses[user_id] = selected
        save_courses(courses)

        course_names = {
            "sotto": "☕そっとこぼす",
            "yorisoi": "🤝寄り添い",
            "katsu": "🔥喝とやさしい",
            "honki": "🌈本気"
        }
        selected_label = course_names.get(selected, "コース")

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"{selected_label} コースを選択しました。\n\nいつでも話しかけてくださいね\U0001F424")
        )

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id
    courses = load_courses()
    selected = courses.get(user_id, "sotto")

    prompts = {
        "sotto": "あなたは、話相手にそっと寄り添うママ友です。ママがつぶやいた一言を否定せず、うなずくように共感してください。励ましやアドバイスはせず、『うん、わかるよ』『それだけ頑張ってるってことだよね』のように、相手の気持ちを受け止める返事をしてください。文章は短く、語尾にやわらかい絵文字（🌷☕😊 など）を少しだけ添えてください。",
        "yorisoi": "あなたは、がんばっているママを見守り、行動や想いを褒めるママ友です。相手の努力や気持ちを認めてやさしく返してください。悩みを話しやすいように促してあげましょう。ママがホッとするようなやさしい絵文字（例：🍀🫶🌈💬 など）を使ってください。",
        "katsu": "あなたは、少し元気をなくしているママの背中をやさしく押す応援役です。前向きな一歩を踏み出せるメッセージをやさしく返してください。元気が出るような絵文字（例：🔥🌟💪😊）を添えてください。",
        "honki": "あなたは、人生を変えたいと願うママに寄り添うカウンセラーです。状況を聞き、一緒にやさしく考えていく返答をしてください。安心感を持てるような絵文字（例：🌱📖🕊️💭）を適度に使ってください。",
    }

    system_prompt = prompts.get(selected, prompts["sotto"])
    full_prompt = f"{system_prompt}\nママのつぶやき：『{user_message}』に対して、返事："

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.8,
            max_tokens=100
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

