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

# ==========================================
# 更新後的 TARGETS (單複數平衡版)
# ==========================================
TARGETS = [
    # --- Text 類 (用於 write, read) ---
    {"word": "the book", "person": 3, "number": "singular", "category": "text"},
    {"word": "the email", "person": 3, "number": "singular", "category": "text"},
    {"word": "the letters", "person": 3, "number": "plural", "category": "text"}, # 複數
    {"word": "the reports", "person": 3, "number": "plural", "category": "text"}, # 複數 (新增)
    
    # --- Food 類 (用於 eat, cook, buy) ---
    {"word": "the apple", "person": 3, "number": "singular", "category": "food"},
    {"word": "the steak", "person": 3, "number": "singular", "category": "food"},
    {"word": "the cookies", "person": 3, "number": "plural", "category": "food"}, # 複數
    {"word": "the vegetables", "person": 3, "number": "plural", "category": "food"}, # 複數 (新增)
    
    # --- Project 類 (用於 design, build) ---
    {"word": "the website", "person": 3, "number": "singular", "category": "project"},
    {"word": "the bridge", "person": 3, "number": "singular", "category": "project"},
    {"word": "the houses", "person": 3, "number": "plural", "category": "project"}, # 複數 (新增)
    {"word": "the plans", "person": 3, "number": "plural", "category": "project"}, # 複數 (新增)

    # --- Place 類 (用於 clean) ---
    {"word": "the room", "person": 3, "number": "singular", "category": "place"},
    {"word": "the kitchen", "person": 3, "number": "singular", "category": "place"},
    {"word": "the windows", "person": 3, "number": "plural", "category": "place"}, # 複數 (新增)
    {"word": "the floors", "person": 3, "number": "plural", "category": "place"}   # 複數 (新增)
]
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
    # ==========================================
# 擴充版連接詞題庫 (Expanded Scenarios)
# ==========================================
CONJUNCTION_SCENARIOS = [
    # --- 因果 (Cause & Effect) ---
    {
        "part1": "It was raining heavily,", "part2": "I took an umbrella.",
        "answer": "so", "distractors": ["but", "because", "although"]
    },
    {
        "part1": "I went to bed early", "part2": "I was very tired.",
        "answer": "because", "distractors": ["so", "but", "although"]
    },
    {
        "part1": "He didn't study,", "part2": "he failed the test.",
        "answer": "so", "distractors": ["if", "because", "unless"]
    },
    {
        "part1": "The store was closed", "part2": "it was a holiday.",
        "answer": "because", "distractors": ["so", "but", "if"]
    },
    {
        "part1": "She was hungry,", "part2": "she made a sandwich.",
        "answer": "so", "distractors": ["because", "but", "if"]
    },
    
    # --- 轉折 (Contrast) ---
    {
        "part1": "He studied very hard,", "part2": "he failed the exam.",
        "answer": "but", "distractors": ["so", "and", "because"]
    },
    {
        "part1": "The car is very old,", "part2": "it runs fast.",
        "answer": "yet", "distractors": ["so", "because", "and"]
    },
    {
        "part1": "I wanted to buy the bag,", "part2": "it was too expensive.",
        "answer": "but", "distractors": ["so", "or", "because"]
    },
    {
        "part1": "____ he is rich,", "part2": "he is not happy.",
        "answer": "Although", "distractors": ["Because", "So", "If"]
    },
    {
        "part1": "____ it rained,", "part2": "we played soccer.",
        "answer": "Although", "distractors": ["Because", "So", "Unless"]
    },

    # --- 條件 (Condition) ---
    {
        "part1": "You will be late", "part2": "you hurry up.",
        "answer": "unless", "distractors": ["if", "so", "and"]
    },
    {
        "part1": "We can go to the park", "part2": "it rains.",
        "answer": "unless", "distractors": ["if", "because", "so"]
    },
    {
        "part1": "____ you study,", "part2": "you will pass.",
        "answer": "If", "distractors": ["Unless", "But", "So"]
    },
    {
        "part1": "I will call you", "part2": "I arrive.",
        "answer": "when", "distractors": ["but", "so", "although"]
    },

    # --- 時間與其他 (Time & Others) ---
    {
        "part1": "Please wait here", "part2": "I come back.",
        "answer": "until", "distractors": ["because", "so", "but"]
    },
    {
        "part1": "He was reading", "part2": "I was cooking.",
        "answer": "while", "distractors": ["so", "if", "unless"]
    },
    {
        "part1": "Would you like coffee", "part2": "tea?",
        "answer": "or", "distractors": ["so", "but", "because"]
    },
    {
        "part1": "I like apples", "part2": "bananas.",
        "answer": "and", "distractors": ["or", "but", "so"]
    },
    {
        "part1": "Don't go out", "part2": "you finish your homework.",
        "answer": "before", "distractors": ["so", "but", "while"]
    }
]
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
