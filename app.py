from flask import Flask, request, abort
import os
import openai
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FollowEvent, FlexSendMessage
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
    # 登録お礼メッセージ
    text = (
        "🌱こえのつぼみへようこそ🌱\n\n"
        "ご登録ありがとうございます✨\n\n"
        "あなたが「話してみよう」と\n"
        "一歩踏み出されたこと\n"
        "とても素晴らしいことです🌷\n\n"
        "ここは、ママの心が\n"
        "ふっと軽くなるような\n"
        "やさしい場所\n"
        "でありたいと思っています😊\n\n"
        "まずは、あなたに合った\n"
        "「お話スタイル」を選んでみてください🍀\n\n"
        "あなたの思いはこぼしていいんです"\n
    )

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=text)
    )

    # Flexメッセージ送信（コース選択ボタン）
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
                    {
                        "type": "button",
                        "action": { "type": "postback", "label": "☕そっとこぼすコース", "data": "course=sotto" },
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "action": { "type": "postback", "label": "🤝寄り添いコース", "data": "course=yorisoi" },
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "action": { "type": "postback", "label": "🔥喝とやさしいコース", "data": "course=katsu" },
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "action": { "type": "postback", "label": "🌈本気コース", "data": "course=honki" },
                        "style": "primary"
                    }
                ]
            }
        }
    )

    line_bot_api.push_message(event.source.user_id, course_flex)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    # ChatGPTに問い合わせ
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは優しいカウンセラーです。短く、共感的に返答してください。"},
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
