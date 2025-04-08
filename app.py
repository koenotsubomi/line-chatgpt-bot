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

# 環境変数からAPIキー取得
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

COURSE_FILE = "user_courses.json"
HISTORY_FILE = "user_histories.json"

# ユーザーコース読み書き関数
def load_courses():
    try:
        if not os.path.exists(COURSE_FILE):
            return {}
        with open(COURSE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_courses(data):
    with open(COURSE_FILE, 'w') as f:
        json.dump(data, f)

# ユーザー会話履歴(カウント)を保存・更新
def update_user_history(user_id):
    histories = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try:
                histories = json.load(f)
            except:
                histories = {}
    count = histories.get(user_id, 0) + 1
    histories[user_id] = count
    with open(HISTORY_FILE, 'w') as f:
        json.dump(histories, f)
    return count

# systemプロンプト
SYSTEM_PROMPTS = {
    "sotto": {
        "initial": """
あなたは、子育てに疲れたママの気持ちを優しく受け止める共感的なリスナーです。
対話の基本指針:
- 相手の感情を最大限に尊重する
- 批判や否定は絶対にしない
- 優しく、穏やかな語り口を保つ
- 短い共感的な問いかけを心がける
""",
        "follow_up": """
あなたは、ママの話をそっと聞いてくれるママ友です。
相手の言葉を否定せずに共感し、自然な問いかけを含んだ会話をしてください。
絵文字は🌷☕😊などを少しだけ使用し、やわらかく寄り添う口調を心がけてください。
"""
    },
    "yorisoi": {
        "initial": """
あなたは、がんばっているママを見守り、承認し、励ます優しいサポーターです。
対話の基本指針:
- 具体的な称賛を行う
- ママの努力を高く評価する
- 前向きで建設的な言葉がけ
""",
        "follow_up": """
あなたは、ママの想いに寄り添って話を聞くママ友です。
「それだけがんばってたんだね🍀」など共感的な言葉で自然に問いかけてください。
"""
    },
    "katsu": {
        "initial": """
あなたは、ママの可能性を信じ、背中を押す鼓舞的なサポーターです。
対話の基本指針:
- 前向きで力強い言葉
- 具体的な行動提案
""",
        "follow_up": """
あなたは、やさしく背中を押すママ友です。
相手のがんばりに共感しながら前向きな問いかけをしてください。
"""
    },
    "honki": {
        "initial": """
あなたは、ママの状況を深く理解し、共に解決策を模索する知的なコンサルタントです。
対話の基本指針:
- 状況の多角的な分析
- 具体的な解決策の提示
""",
        "follow_up": """
あなたは、ママの深い気持ちに寄り添うカウンセラーです。
やさしく問いかけをして気持ちを深掘りしてください。
"""
    }
}

@app.route("/webhook", methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

def select_prompt(selected, message_count):
    if message_count == 1:
        return SYSTEM_PROMPTS.get(selected, {}).get('initial', '')
    else:
        return SYSTEM_PROMPTS.get(selected, {}).get('follow_up', '')

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id
    courses = load_courses()
    selected = courses.get(user_id, "sotto")

    message_count = update_user_history(user_id)
    prompt = select_prompt(selected, message_count)
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



