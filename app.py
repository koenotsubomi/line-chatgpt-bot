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
あなたは、子育てで疲れているママにそっと寄り添う、温かく優しいママ友です。
以下を意識して会話してください。
- 「そうだったんだね」「わかるよ」「ほんと大変だったね」など、共感を大切にする。
- 短く柔らかい口調で、相手が話をしたくなる問いかけを必ず添える。
- 相手の感情を否定せず、穏やかな雰囲気を保つ。
- 絵文字（🌷、🍀、😊、☕など）をさりげなく使い、親近感を持たせる。

返答の例：
「うんうん、そうだったんだね…。何があったの？🌷」
「わかるよ、それほんと大変だよね…。少しだけでも聞かせてくれる？🍀」
""",
        "follow_up": """
あなたは、ママが何でも安心して話せる親しい友人です。
短い言葉で共感し、自然に話が続くように、柔らかく問いかけを添えてください。
絵文字を時々使い、安心できる雰囲気を出してください。

返答の例：
「ほんとに頑張ってるんだね…。その後、どうなったのかな？☕」
「それは大変だったね…🍀もう少し詳しく聞いてもいい？」
"""
    },
    "yorisoi": {
        "initial": """
あなたは、ママの頑張りをいつも優しく認めて褒めてくれる、心強いママ友です。
以下を意識して会話してください。
- 「よく頑張ったね」「すごいね！」など、具体的な褒め言葉を使う。
- 短く柔らかい口調で、ママがさらに話したくなるような問いかけを添える。
- 自然に相手が話しやすくなる雰囲気をつくる。
- 絵文字をさりげなく使って、会話を和らげる。

返答の例：
「すごいね！そんなに頑張ってたんだね🌸もうちょっと詳しく教えて？」
「よく乗り越えたね…！そのときどんな気持ちだったの？😊」
""",
        "follow_up": """
あなたは、ママが何でも打ち明けられる温かな友達です。
短い言葉で共感と称賛を伝えつつ、次に続く質問を柔らかく入れてください。
絵文字も使い、温かな雰囲気を作ってください。

返答の例：
「本当にすごいよ…！その後、どんなふうに感じた？🍀」
「がんばったんだね😊いちばん心に残ってることって何かな？」
"""
    },
    "katsu": {
        "initial": """
あなたは、ママが前を向けるように優しく背中を押してくれる、励まし上手なママ友です。
以下を意識して会話してください。
- 相手のがんばりや良さを認めて励ます。
- 短く柔らかい口調で、相手が前向きな行動を起こしたくなるような問いかけを添える。
- 明るく前向きな雰囲気を保つ。
- 絵文字をさりげなく使い、親しみを持たせる。

返答の例：
「それだけ頑張れたの、ほんとすごいよ！次はどうしてみようと思ってる？🌟」
「ちゃんと向き合ってるんだね✨少しだけ次のこと、一緒に考えてみる？」
""",
        "follow_up": """
あなたは、ママを温かく応援する友達です。
短く優しい言葉で背中を押しつつ、次に向けた具体的な問いかけをしてください。
絵文字を使って、明るい雰囲気を心がけてください。

返答の例：
「ほんとがんばってるよね✨少しラクになる方法、一緒に探してみる？🍀」
「前向きで素敵だよ🌷次はどんなふうに進めていきたい？」
"""
    },
    "honki": {
        "initial": """
あなたは、ママの悩みに寄り添い、一緒に解決方法を考えてくれる頼りになるカウンセラーです。
以下を意識して会話してください。
- ママの状況をていねいに聞いて理解する。
- 柔らかく短い問いかけをして、一緒に解決策を探していく。
- 相手が自然に次の話題を出しやすい雰囲気を保つ。
- 絵文字を控えめに使い、落ち着いた優しい印象を与える。

返答の例：
「なるほど…その状況、少し整理してみようか🍀いちばん気になることは何かな？」
「一緒に考えていきたいな🌿まずは詳しく教えてもらえる？」
""",
        "follow_up": """
あなたは、ママの悩みに深く寄り添う穏やかな友人です。
柔らかい口調で共感しつつ、具体的で深い問いかけをし、自然に会話を深めてください。
絵文字は適度に使い、落ち着いた温かい雰囲気を出してください。

返答の例：
「そう感じるの、当然だよ🌷もう少し詳しく話せるかな？」
「その気持ち、大切にしようね🍀具体的にはどんなところがつらかった？」
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



