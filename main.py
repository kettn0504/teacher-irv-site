import uvicorn
import random
import nltk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

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
# 2. 資料庫 (原有資料 + 新增連接詞資料)
# ==========================================
# ... (為了節省篇幅，原有的 AGENTS, VERBS, TARGETS, TIME_MARKERS 維持不變，請保留原本的資料) ...
# 如果你已經刪掉了，請把上一輪的 AGENTS~PRONOUN_OBJ_MAP 複製回來，或是直接用下面的簡化版測試：

AGENTS = [
    {"word": "The teacher", "person": 3, "number": "singular", "type": "noun"},
    {"word": "The students", "person": 3, "number": "plural", "type": "noun"},
    {"word": "He", "person": 3, "number": "singular", "type": "pronoun"},
    {"word": "They", "person": 3, "number": "plural", "type": "pronoun"},
    {"word": "John", "person": 3, "number": "singular", "type": "proper_noun"}
]

TRANSITIVE_VERBS = [
    {"base": "write", "vpp": "written", "target_req": "text"},
    {"base": "eat", "vpp": "eaten", "target_req": "food"},
    {"base": "clean", "vpp": "cleaned", "target_req": "place"}
]

TARGETS = [
    {"word": "the book", "person": 3, "number": "singular", "category": "text"},
    {"word": "the apple", "person": 3, "number": "singular", "category": "food"},
    {"word": "the room", "person": 3, "number": "singular", "category": "place"}
]

TIME_MARKERS = {
    "past": ["yesterday", "last night", "two days ago"],
    "present": ["every day", "usually", "always"]
}

PRONOUN_OBJ_MAP = {"I": "me", "He": "him", "She": "her", "We": "us", "They": "them", "You": "you"}

# --- [新增] 連接詞情境庫 ---
# 結構: (前半句, 後半句, 正確連接詞, 錯誤選項)
CONJUNCTION_SCENARIOS = [
    # 因果 (Cause & Effect)
    {
        "part1": "It was raining heavily,",
        "part2": "I took an umbrella.",
        "answer": "so",
        "distractors": ["but", "because", "although"]
    },
    {
        "part1": "I went to bed early",
        "part2": "I was very tired.",
        "answer": "because",
        "distractors": ["so", "but", "although"]
    },
    # 轉折 (Contrast)
    {
        "part1": "He studied very hard,",
        "part2": "he failed the exam.",
        "answer": "but",
        "distractors": ["so", "and", "because"]
    },
    {
        "part1": "The car is very old,",
        "part2": "it runs fast.",
        "answer": "yet",
        "distractors": ["so", "because", "and"]
    },
    # 讓步 (Concession)
    {
        "part1": "____ it was cold,",
        "part2": "we went swimming.",
        "answer": "Although",
        "distractors": ["Because", "So", "However"] # 注意大小寫
    },
    # 條件 (Condition)
    {
        "part1": "You will be late",
        "part2": "you hurry up.",
        "answer": "unless",
        "distractors": ["if", "so", "and"]
    }
]

# ==========================================
# 3. 邏輯函數
# ==========================================

# ... (原有的 format_mid_sentence, get_be_verb 維持不變) ...
def format_mid_sentence(word_obj, case_type="subject"):
    text = word_obj["word"]
    w_type = word_obj.get("type", "noun")
    if w_type == "pronoun":
        if case_type == "object": return PRONOUN_OBJ_MAP.get(text, text)
        else: return text.lower() if text != "I" else "I"
    elif w_type == "noun": return text.lower()
    return text

def get_be_verb(target, tense):
    person, number = target["person"], target["number"]
    if tense == "past": return "was" if number == "singular" else "were"
    else:
        if person == 1 and number == "singular": return "am"
        return "is" if number == "singular" else "are"

# ... (原有的 generate_passive_be_cloze_with_time 維持不變) ...
def generate_passive_be_cloze_with_time():
    verb_obj = random.choice(TRANSITIVE_VERBS)
    valid_targets = [t for t in TARGETS if t["category"] == verb_obj["target_req"]]
    target = random.choice(valid_targets) if valid_targets else random.choice(TARGETS)
    agent = random.choice(AGENTS)
    tense = random.choice(["past", "present"])
    correct_be = get_be_verb(target, tense)
    time_marker = random.choice(TIME_MARKERS[tense])

    target_text = target["word"].capitalize()
    agent_text = format_mid_sentence(agent, case_type="object")
    
    question_sentence = f"{target_text} ____ {verb_obj['vpp']} by {agent_text} {time_marker}."
    
    distractors = set()
    if correct_be == "was": distractors.add("were")
    if correct_be == "were": distractors.add("was")
    if correct_be == "is": distractors.add("are")
    if correct_be == "are": distractors.add("is")
    
    if tense == "past": distractors.update(["is", "are"])
    else: distractors.update(["was", "were"])
        
    final_options = list(distractors)[:3]
    final_options.append(correct_be)
    random.shuffle(final_options)
    
    return {
        "question": question_sentence,
        "options": final_options,
        "answer": correct_be
    }

# --- [新增] 連接詞生成函數 ---
def generate_conjunction_cloze():
    scenario = random.choice(CONJUNCTION_SCENARIOS)
    
    # 判斷挖空位置
    # 如果 answer 首字大寫 (例如 Although)，代表它是句首，不需要在中間加空格
    if scenario["answer"][0].isupper():
        # 題目: ____ it was cold, we went swimming.
        question = f"____ {scenario['part1'][5:]} {scenario['part2']}" # 去掉 part1 的提示字(Mock logic simple handling) -> 這裡直接用字串拼接更穩
        
        # 簡單一點：直接用 scenario 裡的結構
        question = f"____ {scenario['part1'].replace('____ ', '')} {scenario['part2']}"
    else:
        # 題目: It was raining, ____ I took an umbrella.
        question = f"{scenario['part1']} ____ {scenario['part2']}"
    
    # 選項
    options = scenario["distractors"][:]
    options.append(scenario["answer"])
    random.shuffle(options)
    
    return {
        "question": question,
        "options": options,
        "answer": scenario["answer"]
    }

# ==========================================
# 4. API 接口
# ==========================================
@app.get("/")
def read_root():
    return {"status": "Online"}

# [修改] 新增 q_type 參數
@app.get("/api/generate-cloze")
def get_cloze_question(q_type: str = "passive"):
    if q_type == "conjunction":
        return generate_conjunction_cloze()
    else:
        return generate_passive_be_cloze_with_time()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
