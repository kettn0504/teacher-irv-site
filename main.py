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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
# 2. 資料庫
# ==========================================
AGENTS = [
    {"word": "The teacher", "person": 3, "number": "singular", "type": "noun"},
    {"word": "The students", "person": 3, "number": "plural", "type": "noun"},
    {"word": "He", "person": 3, "number": "singular", "type": "pronoun"},
    {"word": "They", "person": 3, "number": "plural", "type": "pronoun"},
    {"word": "The chef", "person": 3, "number": "singular", "type": "noun"},
    {"word": "The writer", "person": 3, "number": "singular", "type": "noun"},
    {"word": "We", "person": 1, "number": "plural", "type": "pronoun"},
    {"word": "John", "person": 3, "number": "singular", "type": "proper_noun"} # 測試專有名詞
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
    {"word": "the book", "person": 3, "number": "singular", "category": "text"},
    {"word": "the letters", "person": 3, "number": "plural", "category": "text"},
    {"word": "the email", "person": 3, "number": "singular", "category": "text"},
    {"word": "the apple", "person": 3, "number": "singular", "category": "food"},
    {"word": "the cookies", "person": 3, "number": "plural", "category": "food"},
    {"word": "the steak", "person": 3, "number": "singular", "category": "food"},
    {"word": "the website", "person": 3, "number": "singular", "category": "project"},
    {"word": "the bridge", "person": 3, "number": "singular", "category": "project"},
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

# [關鍵修正] 新增這個函數來處理句子中間的大小寫
def format_mid_sentence(word_obj, case_type="subject"):
    """
    處理句子中間的單字格式：
    1. 代名詞 -> 轉受格或小寫
    2. 普通名詞 (The teacher) -> 轉小寫 (the teacher)
    3. 專有名詞 (John) -> 保持大寫
    """
    text = word_obj["word"]
    w_type = word_obj.get("type", "noun")
    
    # 狀況 A: 代名詞
    if w_type == "pronoun":
        if case_type == "object":
            # 轉受格 (He -> him)
            return PRONOUN_OBJ_MAP.get(text, text)
        else:
            # 轉小寫 (He -> he), 但 I 除外
            if text == "I": return "I"
            return text.lower()

    # 狀況 B: 普通名詞 (The teacher -> the teacher)
    elif w_type == "noun":
        return text.lower()

    # 狀況 C: 專有名詞 (John -> John)
    elif w_type == "proper_noun":
        return text
    
    return text

def get_be_verb(target, tense):
    person, number = target["person"], target["number"]
    if tense == "past":
        if number == "singular": return "was"
        return "were"
    else: # present
        if person == 1 and number == "singular": return "am"
        if number == "singular": return "is"
        return "are"

def generate_passive_be_cloze_with_time():
    verb_obj = random.choice(TRANSITIVE_VERBS)
    
    # 篩選符合語意邏輯的受詞
    valid_targets = [t for t in TARGETS if t["category"] == verb_obj["target_req"]]
    if not valid_targets:
        target = random.choice(TARGETS)
    else:
        target = random.choice(valid_targets)
        
    agent = random.choice(AGENTS)
    tense = random.choice(["past", "present"])
    correct_be = get_be_verb(target, tense)
    time_marker = random.choice(TIME_MARKERS[tense])

    # 組裝題目
    target_text = target["word"].capitalize()
    
    # [關鍵修正] 使用 format_mid_sentence 來處理 Agent
    # 因為是 by + Agent，所以是用 "object" (受格) 模式
    agent_text = format_mid_sentence(agent, case_type="object")
    
    question_sentence = f"{target_text} ____ {verb_obj['vpp']} by {agent_text} {time_marker}."
    
    # 生成選項
    distractors = set()
    if correct_be == "was": distractors.add("were")
    if correct_be == "were": distractors.add("was")
    if correct_be == "is": distractors.add("are")
    if correct_be == "are": distractors.add("is")
    
    if tense == "past":
        distractors.add("is")
        distractors.add("are")
    else:
        distractors.add("was")
        distractors.add("were")
        
    final_options = list(distractors)
    if len(final_options) > 3:
        final_options = final_options[:3]
    
    final_options.append(correct_be)
    random.shuffle(final_options)
    
    return {
        "question": question_sentence,
        "options": final_options,
        "answer": correct_be
    }

# ==========================================
# 4. API 接口
# ==========================================
@app.get("/")
def read_root():
    return {"status": "Online", "message": "Grammar API v2 (Fixed Case)"}

@app.get("/api/generate-cloze")
def get_cloze_question():
    return generate_passive_be_cloze_with_time()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
