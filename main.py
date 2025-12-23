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
# 2. 資料庫 (整合國中 2000 單字)
# ==========================================
AGENTS = [
    {"word": "The teacher", "person": 3, "number": "singular", "type": "noun"},
    {"word": "The students", "person": 3, "number": "plural", "type": "noun"},
    {"word": "He", "person": 3, "number": "singular", "type": "pronoun"},
    {"word": "They", "person": 3, "number": "plural", "type": "pronoun"},
    {"word": "John", "person": 3, "number": "singular", "type": "proper_noun"}
]

# 動詞庫：為了配合國中單字，我擴充了對應的動詞
TRANSITIVE_VERBS = [
    {"base": "write", "vpp": "written", "target_req": "text"},
    {"base": "read", "vpp": "read", "target_req": "text"},
    {"base": "eat", "vpp": "eaten", "target_req": "food"},
    {"base": "cook", "vpp": "cooked", "target_req": "food"},
    {"base": "buy", "vpp": "bought", "target_req": "food"},
    {"base": "design", "vpp": "designed", "target_req": "project"},
    {"base": "build", "vpp": "built", "target_req": "project"},
    {"base": "clean", "vpp": "cleaned", "target_req": "place"},
    {"base": "visit", "vpp": "visited", "target_req": "place"}, # 新增
    {"base": "fix", "vpp": "fixed", "target_req": "device"}     # 新增
]

# 目標名詞庫：加入 min_level 標籤 (1=國小/入門, 2=國中/進階)
# 這些單字均來自你提供的 PDF 檔案
TARGETS = [
    # --- Text 類 ---
    {"word": "the book", "person": 3, "number": "singular", "category": "text", "min_level": 1}, [cite: 117]
    {"word": "the letter", "person": 3, "number": "singular", "category": "text", "min_level": 1}, [cite: 653]
    {"word": "the comic books", "person": 3, "number": "plural", "category": "text", "min_level": 1},
    {"word": "the newspaper", "person": 3, "number": "singular", "category": "text", "min_level": 2}, [cite: 789]
    {"word": "the dictionary", "person": 3, "number": "singular", "category": "text", "min_level": 2}, [cite: 337]
    {"word": "the magazine", "person": 3, "number": "singular", "category": "text", "min_level": 2}, [cite: 730]

    # --- Food 類 ---
    {"word": "the apple", "person": 3, "number": "singular", "category": "food", "min_level": 1}, [cite: 32]
    {"word": "the egg", "person": 3, "number": "singular", "category": "food", "min_level": 1}, [cite: 433]
    {"word": "the banana", "person": 3, "number": "singular", "category": "food", "min_level": 1}, [cite: 47]
    {"word": "the noodles", "person": 3, "number": "plural", "category": "food", "min_level": 1}, [cite: 805]
    {"word": "the sandwich", "person": 3, "number": "singular", "category": "food", "min_level": 2}, [cite: 1025]
    {"word": "the steak", "person": 3, "number": "singular", "category": "food", "min_level": 2}, [cite: 1241]
    {"word": "the vegetables", "person": 3, "number": "plural", "category": "food", "min_level": 2}, [cite: 1431]
    {"word": "the spaghetti", "person": 3, "number": "singular", "category": "food", "min_level": 2}, [cite: 1175]

    # --- Place 類 ---
    {"word": "the park", "person": 3, "number": "singular", "category": "place", "min_level": 1}, [cite: 905]
    {"word": "the zoo", "person": 3, "number": "singular", "category": "place", "min_level": 1}, [cite: 1496]
    {"word": "the room", "person": 3, "number": "singular", "category": "place", "min_level": 1}, [cite: 1080]
    {"word": "the kitchen", "person": 3, "number": "singular", "category": "place", "min_level": 1}, [cite: 645]
    {"word": "the restaurant", "person": 3, "number": "singular", "category": "place", "min_level": 2}, [cite: 1000]
    {"word": "the museum", "person": 3, "number": "singular", "category": "place", "min_level": 2}, [cite: 801]
    {"word": "the apartment", "person": 3, "number": "singular", "category": "place", "min_level": 2}, [cite: 31]
    
    # --- Device/Project 類 (較進階) ---
    {"word": "the robot", "person": 3, "number": "singular", "category": "device", "min_level": 1}, [cite: 1060]
    {"word": "the computer", "person": 3, "number": "singular", "category": "device", "min_level": 2}, [cite: 280]
    {"word": "the refrigerator", "person": 3, "number": "singular", "category": "device", "min_level": 2}, [cite: 1079]
    {"word": "the helicopter", "person": 3, "number": "singular", "category": "device", "min_level": 2}, [cite: 530]
    {"word": "the bridge", "person": 3, "number": "singular", "category": "project", "min_level": 1}, [cite: 190]
    {"word": "the website", "person": 3, "number": "singular", "category": "project", "min_level": 2}
]

TIME_MARKERS = {
    "past": ["yesterday", "last night", "two days ago", "last week"],
    "present": ["every day", "usually", "always", "often"]
}

PRONOUN_OBJ_MAP = {"I": "me", "He": "him", "She": "her", "We": "us", "They": "them", "You": "you"}

# 連接詞題庫 (已包含混合難度)
CONJUNCTION_SCENARIOS = [
    {"part1": "It was raining,", "part2": "I took an umbrella.", "answer": "so", "distractors": ["but", "because"], "level": 1},
    {"part1": "I was tired", "part2": "I went to bed.", "answer": "so", "distractors": ["but", "if"], "level": 1},
    {"part1": "He is rich,", "part2": "he is not happy.", "answer": "but", "distractors": ["so", "and"], "level": 1},
    {"part1": "____ it rained,", "part2": "we played soccer.", "answer": "Although", "distractors": ["Because", "So"], "level": 2},
    {"part1": "You will be late", "part2": "you hurry up.", "answer": "unless", "distractors": ["if", "so"], "level": 2},
    {"part1": "Please wait", "part2": "I come back.", "answer": "until", "distractors": ["so", "but"], "level": 2}
]

# ==========================================
# 3. 邏輯函數
# ==========================================

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

def generate_passive_be_cloze_with_time(level_req=1):
    # 1. 根據難度過濾名詞
    # 如果選 Level 1 (國小)，只會出現 min_level=1 的字
    # 如果選 Level 2 (國中)，則所有字都可能出現
    if level_req == 1:
        available_targets = [t for t in TARGETS if t.get("min_level", 1) == 1]
    else:
        available_targets = TARGETS # Level 2 包含全部

    # 防呆：萬一過濾完沒字了 (理論上不會)，就用全部
    if not available_targets:
        available_targets = TARGETS

    target = random.choice(available_targets)
    
    # 2. 尋找搭配的動詞
    valid_verbs = [v for v in TRANSITIVE_VERBS if v["target_req"] == target["category"]]
    if not valid_verbs:
        # 如果找不到搭配動詞(例如選了device卻沒對應動詞)，重選一個通用動詞+通用名詞
        verb_obj = TRANSITIVE_VERBS[0] # write
        target = random.choice([t for t in available_targets if t["category"] == "text"])
    else:
        verb_obj = random.choice(valid_verbs)

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

def generate_conjunction_cloze(level_req=1):
    # 根據難度過濾連接詞題目
    if level_req == 1:
        available_scenarios = [s for s in CONJUNCTION_SCENARIOS if s.get("level", 1) == 1]
    else:
        available_scenarios = CONJUNCTION_SCENARIOS
        
    scenario = random.choice(available_scenarios)
    
    if scenario["answer"][0].isupper():
        question = f"____ {scenario['part1'][5:]} {scenario['part2']}" # 簡單模擬
        question = f"____ {scenario['part1'].replace('____ ', '')} {scenario['part2']}"
    else:
        question = f"{scenario['part1']} ____ {scenario['part2']}"
    
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

@app.get("/api/generate-cloze")
def get_cloze_question(q_type: str = "passive", level: int = 1):
    # 接收 level 參數 (1=Elementary, 2=Junior)
    if q_type == "conjunction":
        return generate_conjunction_cloze(level_req=level)
    else:
        return generate_passive_be_cloze_with_time(level_req=level)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
