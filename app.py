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
USER_HISTORY_FILE = "user_history.json"

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

# ユーザーの発言履歴管理
def load_history():
    try:
        if not os.path.exists(USER_HISTORY_FILE):
            return {}
        with open(USER_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_history(data):
    with open(USER_HISTORY_FILE, 'w') as f:
        json.dump(data, f)

def update_user_history(user_id):
    history = load_history()
    history[user_id] = history.get(user_id, 0) + 1
    save_history(history)
    return history[user_id]

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

    # ユーザーの発言数を更新＆取得
    message_count = update_user_history(user_id)

    # 各コースのプロンプト切り替え
    if selected == "sotto":
        if message_count == 1:
            prompt = 'あなたは、話相手にそっと寄り添うママ友です。ママがつぶやいた一言に共感し、「よかったら、もう少し聞かせてね☕」などのやさしい促しを文末に添えてください。アドバイスは不要です。短くてやわらかい言葉にしてください。絵文字は🌷☕😊などを少しだけ。'
        else:
            prompt = 'あなたは、ママの話をそっと聞いてくれるママ友です。相手の言葉を否定せずに共感し、「そっか…そんなことがあったんだね☁️」や「自分を責めたりしてない？」など自然な問いかけを含んだ返事を短く返してください。絵文字は🌷☕😊などを少しだけ。'

    elif selected == "yorisoi":
        if message_count == 1:
            prompt = 'あなたは、がんばっているママを見守るママ友です。ママの努力を認め、「よかったらもう少し聞かせてね🍀」などのやさしい促しを添えてください。絵文字は🫶🍀🌷などを少しだけ使ってください。'
        else:
            prompt = 'あなたは、ママの想いに寄り添って話を聞くママ友です。「それだけがんばってたんだね🍀」「今日あったこと、よかったらもう少し聞かせて」など、共感しながら自然な問いかけを短く返してください。絵文字はやさしいものを少しだけ。'

    elif selected == "katsu":
        if message_count == 1:
            prompt = 'あなたは、少し元気をなくしているママの背中をやさしく押すママ友です。「大丈夫」「そのままでいいよ」などの言葉で受け止めつつ、「よかったら少し話してみてね🔥」など前向きな促しを添えてください。絵文字は🔥🌟💪😊などを少しだけ。'
        else:
            prompt = 'あなたは、やさしく背中を押すママ友です。相手のがんばりに共感しながら、「それだけ頑張ってたんだね🌟」「どうしたら少しラクになれそう？」など、前向きな問いかけを交えて返してください。'

    elif selected == "honki":
        if message_count == 1:
            prompt = 'あなたは、人生を変えたいと願うママに寄り添うカウンセラーです。まずは相手の言葉を受け止め、「よかったら、どんな気持ちだったか聞かせてください🕊️」などのやさしい促しを添えてください。'
        else:
            prompt = 'あなたは、ママの深い気持ちに寄り添うカウンセラーです。「その気持ち、大切にしてあげてね📖」「何が一番つらかったかな？」など、ていねいに気持ちを深掘りする問いかけをやさしく返してください。'

    else:
        prompt = 'あなたは、相手に共感してやさしく返事をするママ友です。短く、否定せず、あたたかい返答をしてください。'

    full_prompt = f"{prompt}\nママのつぶやき：『{user_message}』に対して、返事："

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.8,
            max_tokens=120
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




