import uvicorn
import random
import nltk
import lemminflect
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# ==========================================
# 1. 初始化與設定
# ==========================================
app = FastAPI()

# 允許跨網域 (讓你的 HTML 網頁可以連線)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 啟動時下載必要的語料庫 (Render 伺服器需要)
@app.on_event("startup")
async def startup_event():
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet')
        nltk.download('omw-1.4')
        nltk.download('averaged_perceptron_tagger')
    print("✅ NLTK 資料庫準備完成")

# ==========================================
# 2. 資料庫 (The Database)
# ==========================================
AGENTS = [
    {"word": "The teacher", "person": 3, "number": "singular", "type": "noun"},
    {"word": "The students", "person": 3, "number": "plural", "type": "noun"},
    {"word": "He", "person": 3, "number": "singular", "type": "pronoun"},
    {"word": "They", "person": 3, "number": "plural", "type": "pronoun"},
    {"word": "The chef", "person": 3, "number": "singular", "type": "noun"},
    {"word": "The writer", "person": 3, "number": "singular", "type": "noun"},
    {"word": "We", "person": 1, "number": "plural", "type": "pronoun"}
]

TRANSITIVE_VERBS = [
    {"base": "write", "vpp": "written", "target_req": "text"},
    {"base": "read", "vpp": "read", "target_req": "text"},
    {"base": "eat", "vpp": "eaten", "target_req": "food"},
    {"base": "cook", "vpp": "cooked", "target_req": "food"},
    {"base": "design", "vpp": "designed", "target_req": "project"},
    {"base": "build", "vpp": "built", "target_req": "project"},
    {"base": "buy", "vpp": "bought", "target_req": "food"},
    {"base": "clean", "vpp": "cleaned", "target_req": "place"}
]

TARGETS = [
    # Text 類
    {"word": "the book", "person": 3, "number": "singular", "category": "text"},
    {"word": "the letters", "person": 3, "number": "plural", "category": "text"},
    {"word": "the email", "person": 3, "number": "singular", "category": "text"},
    # Food 類
    {"word": "the apple", "person": 3, "number": "singular", "category": "food"},
    {"word": "the cookies", "person": 3, "number": "plural", "category": "food"},
    {"word": "the steak", "person": 3, "number": "singular", "category": "food"},
    # Project 類
    {"word": "the website", "person": 3, "number": "singular", "category": "project"},
    {"word": "the bridge", "person": 3, "number": "singular", "category": "project"},
    # Place 類
    {"word": "the room", "person": 3, "number": "singular", "category": "place"},
    {"word": "the kitchen", "person": 3, "number": "singular", "category": "place"}
]

TIME_MARKERS = {
    "past": ["yesterday", "last night", "two days ago", "last week", "in 2020"],
    "present": ["every day", "usually", "on Sundays", "every week", "always"]
}

PRONOUN_OBJ_MAP = {"I": "me", "He": "him", "She": "her", "We": "us", "They": "them", "You": "you"}

# ==========================================
# 3. 核心邏輯工具 (Helper Functions)
# ==========================================
def get_be_verb(target, tense):
    """決定 Be 動詞是 is/am/are 還是 was/were"""
    person, number = target["person"], target["number"]
    if tense == "past":
        if number == "singular": return "was"
        return "were"
    else: # present
        if person == 1 and number == "singular": return "am"
        if number == "singular": return "is"
        return "are"

def generate_passive_be_cloze_with_time():
    """生成帶有時間錨點的被動語態填空題"""
    
    # 1. 選材 (從資料庫隨機挑選)
    verb_obj = random.choice(TRANSITIVE_VERBS)
    
    # 篩選符合語意邏輯的受詞 (例如 eat 只能配 food)
    valid_targets = [t for t in TARGETS if t["category"] == verb_obj["target_req"]]
    if not valid_targets: # 防呆機制
        target = random.choice(TARGETS)
    else:
        target = random.choice(valid_targets)
        
    agent = random.choice(AGENTS)
    
    # 2. 隨機決定時態 (決定這一題考過去式還是現在式)
    tense = random.choice(["past", "present"])
    
    # 3. 計算正確答案
    correct_be = get_be_verb(target, tense)

    # 4. 選取對應的時間詞 (這是關鍵提示)
    time_marker = random.choice(TIME_MARKERS[tense])

    # 5. 組裝題目字串
    target_text = target["word"].capitalize()
    
    # 處理 Agent (代名詞轉受格, ex: by him)
    agent_text = agent["word"]
    if agent["type"] == "pronoun":
        agent_text = PRONOUN_OBJ_MAP.get(agent_text, agent_text)
    
    # 題目格式: [Target] ____ [Vpp] by [Agent] [Time].
    question_sentence = f"{target_text} ____ {verb_obj['vpp']} by {agent_text} {time_marker}."
    
    # 6. 生成選項 (包含正確答案與混淆項)
    distractors = set()
    
    # 邏輯 A: 加入錯誤的數 (單複數錯誤)
    if correct_be == "was": distractors.add("were")
    if correct_be == "were": distractors.add("was")
    if correct_be == "is": distractors.add("are")
    if correct_be == "are": distractors.add("is")
    
    # 邏輯 B: 加入錯誤的時態 (這是最重要的陷阱，因為有時間詞)
    if tense == "past":
        distractors.add("is")
        distractors.add("are")
    else:
        distractors.add("was")
        distractors.add("were")
        
    # 轉成列表並洗牌
    final_options = list(distractors)
    # 確保只有 3 個干擾項
    if len(final_options) > 3:
        final_options = final_options[:3]
    
    final_options.append(correct_be) # 加入正解
    random.shuffle(final_options)    # 再次洗牌，確保答案位置隨機
    
    return {
        "question": question_sentence,
        "options": final_options,
        "answer": correct_be
    }

# ==========================================
# 4. API 接口 (Endpoint)
# ==========================================
@app.get("/")
def read_root():
    return {"status": "Online", "message": "English Brain is Active!"}

@app.get("/api/generate-cloze")
def get_cloze_question():
    # 這裡不再回傳死資料，而是呼叫上面的生成函數
    return generate_passive_be_cloze_with_time()

# 給 Render 的啟動點
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
