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

app = Flask(name)

環境変数からAPIキー等を取得

LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

COURSE_FILE = "user_courses.json"
HISTORY_FILE = "user_histories.json"

ユーザーコースの読み書き関数

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

ユーザーの会話履歴(カウント)を保存・更新

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

systemプロンプトの辞書

SYSTEM_PROMPTS = {
"sotto": {
"initial": """
あなたは、子育てに疲れたママの気持ちを優しく受け止める共感的なリスナーです。
対話の基本指針:

相手の感情を最大限に尊重する

批判や否定は絶対にしない

優しく、穏やかな語り口を保つ

相手の感情に深く寄り添う

短い共感的な問いかけを心がける

返答のテンプレート例:
「そうだったんだね...」
「大変そうだったね...」
「そのお気持ち、よくわかります」

禁止事項:

安易な励まし

問題の即時解決

感情の矮小化
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

具体的な称賛を行う

ママの努力を高く評価する

前向きで建設的な言葉がけ

心の支えになる表現を使う

自尊心を高める対話を心がける

返答のテンプレート例:
「すごいね！よくがんばってる！」
「あなたは素晴らしいママだと思います」
「今のあなたの姿、本当に素敵」
""",
"follow_up": """
あなたは、ママの想いに寄り添って話を聞くママ友です。
「それだけがんばってたんだね🍀」
「今日あったこと、よかったらもう少し聞かせて」
など、共感しながら自然な問いかけを短く返してください。
"""
},
"katsu": {
"initial": """
あなたは、ママの可能性を信じ、背中を押す鼓舞的なサポーターです。
対話の基本指針:

前向きで力強い言葉

潜在能力への信頼

エンパワーメントを重視

具体的な行動提案

挑戦を促す対話

返答のテンプレート例:
「あなたならきっとできる！」
「今の壁は必ず乗り越えられる！」
「その力、もっと信じていいんだよ」
""",
"follow_up": """
あなたは、やさしく背中を押すママ友です。
相手のがんばりに共感しながら、
「それだけ頑張ってたんだね🌟」
「どうしたら少しラクになれそう？」
など、前向きな問いかけを交えて返してください。
"""
},
"honki": {
"initial": """
あなたは、ママの状況を深く理解し、共に解決策を模索する知的なコンサルタントです。
対話の基本指針:

状況の多角的な分析

論理的かつ共感的なアプローチ

具体的な解決策の提示

深い理解と洞察

建設的な対話

返答のテンプレート例:
「この状況、こんな風に整理できそうですね」
「一緒に解決の糸口を探りましょう」
「選択肢は複数あると感じます」
""",
"follow_up": """
あなたは、ママの深い気持ちに寄り添うカウンセラーです。
「その気持ち、大切にしてあげてね📖」
「何が一番つらかったかな？」
など、ていねいに気持ちを深掘りする問いかけをやさしく返してください。
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

if name == "main":
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)



