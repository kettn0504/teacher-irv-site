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
# 2. 資料庫 (Passive Voice 專用)
# ==========================================
# 為了節省篇幅，這裡保留我們上次擴充的完整版 TARGETS (包含國中單字)
# 請確認您上次的 TARGETS 資料還在，如果不在，請把上次的 TARGETS 貼回來
# 這裡僅列出結構示意，請務必保留您豐富的單字庫！

AGENTS = [
    {"word": "The teacher", "person": 3, "number": "singular", "type": "noun"},
    {"word": "The students", "person": 3, "number": "plural", "type": "noun"},
    {"word": "He", "person": 3, "number": "singular", "type": "pronoun"},
    {"word": "They", "person": 3, "number": "plural", "type": "pronoun"},
    {"word": "My mother", "person": 3, "number": "singular", "type": "noun"},
    {"word": "The doctor", "person": 3, "number": "singular", "type": "noun"}
]

TRANSITIVE_VERBS = [
    {"base": "write", "vpp": "written", "target_req": "text"},
    {"base": "read", "vpp": "read", "target_req": "text"},
    {"base": "eat", "vpp": "eaten", "target_req": "food"},
    {"base": "cook", "vpp": "cooked", "target_req": "food"},
    {"base": "buy", "vpp": "bought", "target_req": "food"},
    {"base": "design", "vpp": "designed", "target_req": "project"},
    {"base": "build", "vpp": "built", "target_req": "project"},
    {"base": "clean", "vpp": "cleaned", "target_req": "place"},
    {"base": "visit", "vpp": "visited", "target_req": "place"},
    {"base": "fix", "vpp": "fixed", "target_req": "device"}
]

# (請務必保留上次擴充的 TARGETS，這裡僅放少量範例以免程式碼過長)
TARGETS = [
    {"word": "the book", "person": 3, "number": "singular", "category": "text", "min_level": 1},
    {"word": "the letter", "person": 3, "number": "singular", "category": "text", "min_level": 1},
    {"word": "the apple", "person": 3, "number": "singular", "category": "food", "min_level": 1},
    {"word": "the computer", "person": 3, "number": "singular", "category": "device", "min_level": 2},
    {"word": "the museum", "person": 3, "number": "singular", "category": "place", "min_level": 2},
    # ... 請貼上您完整的清單 ...
]

TIME_MARKERS = {
    "past": ["yesterday", "last night", "two days ago", "last week"],
    "present": ["every day", "usually", "always", "often"]
}

PRONOUN_OBJ_MAP = {"I": "me", "He": "him", "She": "her", "We": "us", "They": "them", "You": "you"}



# ==========================================
# 3. [核心修復] 動態連接詞生成引擎
# ==========================================

class ConjunctionGenerator:
    """
    動態連接詞生成器 (修復雙重主詞 Bug 版)
    """
    
    SCENARIOS = {
        # ... (這裡的情境資料保持不變，直接沿用原本的即可) ...
        # 為了方便您複製，我把資料縮減顯示，請保留您原本完整的 SCENARIOS 資料
        "weather_bad": {
            "subjects": ["It", "The weather"],
            "causes": ["was raining hard", "was very stormy", "was terrible outside"],
            "effects_logical": ["we stayed at home", "the game was canceled", "I took a taxi", "we didn't go out"],
            "effects_contrast": ["we went swimming", "he still went out", "the game continued"], 
            "level": 1
        },
        "health_sick": {
            "subjects": ["He", "She", "Tom", "The boy"],
            "causes": ["was sick", "had a fever", "didn't feel well", "had a bad cold"],
            "effects_logical": ["went to the doctor", "took some medicine", "stayed in bed", "didn't go to school"],
            "effects_contrast": ["still went to work", "refused to see a doctor", "looked very happy"],
            "level": 1
        },
        "study_hard": {
            "subjects": ["The student", "Mary", "He", "She"],
            "causes": ["studied very hard", "prepared for the test", "read many books"],
            "effects_logical": ["passed the exam", "got a good grade", "became very smart"],
            "effects_contrast": ["failed the test", "got a bad score", "didn't understand the question"],
            "level": 2
        },
        "money_expensive": {
            "subjects": ["The car", "The house", "The bag"],
            "causes": ["was too expensive", "cost a lot of money", "was not cheap"],
            "effects_logical": ["I didn't buy it", "we couldn't afford it", "he decided not to get it"],
            "effects_contrast": ["he bought it anyway", "she paid for it", "it sold out quickly"],
            "level": 2
        },
        "physical_hungry": {
            "subjects": ["I", "He", "The dog", "The baby"],
            "causes": ["was very hungry", "hadn't eaten all day", "was starving"],
            "effects_logical": ["ate a big burger", "cooked a meal", "asked for food"],
            "effects_contrast": ["didn't want to eat", "gave the food away", "kept working"],
            "level": 1
        },
        "time_late": {
            "subjects": ["We", "They", "You"],
            "causes": ["were late", "missed the bus", "didn't hear the alarm"],
            "effects_logical": ["had to run", "took a taxi", "missed the meeting"],
            "effects_contrast": ["walked slowly", "weren't worried", "stopped for coffee"],
            "level": 2
        }
    }

    @staticmethod
    def generate(level_req=1):
        available_keys = [k for k, v in ConjunctionGenerator.SCENARIOS.items() if v["level"] <= level_req]
        if not available_keys: available_keys = list(ConjunctionGenerator.SCENARIOS.keys())
        
        key = random.choice(available_keys)
        data = ConjunctionGenerator.SCENARIOS[key]
        subj = random.choice(data["subjects"])
        
        pattern_type = random.choice(["so", "because", "but", "although"])
        cause = random.choice(data["causes"])
        
        # 決定代名詞 (He/She/It/They...)
        pronoun = "he"
        if subj in ["She", "Mary", "The girl"]: pronoun = "she"
        elif subj in ["It", "The weather", "The car", "The house"]: pronoun = "it"
        elif subj in ["We"]: pronoun = "we"
        elif subj in ["They", "The students"]: pronoun = "they"
        elif subj in ["I"]: pronoun = "I"
        elif subj in ["You"]: pronoun = "you"
        
        # --- [關鍵修改點] 智慧代名詞添加函數 ---
        def add_pronoun(text, pron):
            # 1. 取得句子的第一個字 (轉小寫方便比對)
            first_word = text.split()[0].lower()
            
            # 2. 定義「這些字開頭就不用加代名詞」的清單
            # 包含：限定詞 (the, a, my...) 和 代名詞 (I, he, we...)
            skip_words = [
                "the", "a", "an", "my", "your", "his", "her", "our", "their", "this", "that",
                "i", "he", "she", "it", "we", "you", "they",
                "tom", "mary", "john" # 常見人名
            ]
            
            # 3. 檢查
            if first_word in skip_words:
                return text # 原句已經有主詞，直接回傳
            
            # 4. 如果不是上面那些字 (通常是動詞開頭，如 "went home")，才補代名詞
            return f"{pron} {text}"
        # -------------------------------------

        effect_logical = add_pronoun(random.choice(data["effects_logical"]), pronoun)
        effect_contrast = add_pronoun(random.choice(data["effects_contrast"]), pronoun)

        question = ""
        answer = ""
        distractors = []

        if pattern_type == "so":
            question = f"{subj} {cause}, ____ {effect_logical}."
            answer = "so"
            distractors = ["but", "because", "although"]

        elif pattern_type == "because":
            # 這裡也要小心，如果是 "because [Subject] [Cause]"
            # 我們的 cause 通常是 "was sick" (無主詞)，所以這裡必須強制加上代名詞
            # 但 q_part1 (Effect) 已經經過 add_pronoun 處理，是安全的
            q_part1 = effect_logical 
            q_part1 = q_part1[0].upper() + q_part1[1:] # 句首大寫
            
            q_part2 = f"{pronoun} {cause}" # Cause 通常是動詞片語，所以這裡強制加 pronoun 是安全的
            
            question = f"{q_part1} ____ {q_part2}."
            answer = "because"
            distractors = ["so", "but", "although"]

        elif pattern_type == "but":
            question = f"{subj} {cause}, ____ {effect_contrast}."
            answer = "but"
            distractors = ["so", "because", "if"]

        elif pattern_type == "although":
            question = f"____ {subj} {cause}, {effect_contrast}."
            answer = "Although"
            distractors = ["Because", "So", "But"]

        random.shuffle(distractors)
        final_options = distractors[:3]
        final_options.append(answer)
        random.shuffle(final_options)

        return {
            "question": question,
            "options": final_options,
            "answer": answer
        }

# ... (後面的代碼不變)
# ==========================================
# 4. 邏輯函數 (Passive 專用)
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
    if level_req == 1:
        available_targets = [t for t in TARGETS if t.get("min_level", 1) == 1]
    else:
        available_targets = [t for t in TARGETS if t.get("min_level", 1) >= 2]

    if not available_targets: available_targets = TARGETS

    target = random.choice(available_targets)
    valid_verbs = [v for v in TRANSITIVE_VERBS if v["target_req"] == target["category"]]
    
    if not valid_verbs:
        verb_obj = TRANSITIVE_VERBS[0]
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

# ==========================================
# 5. API 接口
# ==========================================
@app.get("/")
def read_root():
    return {"status": "Online"}

@app.get("/api/generate-cloze")
def get_cloze_question(q_type: str = "passive", level: int = 1):
    if q_type == "conjunction":
        # 使用新的動態生成器
        return ConjunctionGenerator.generate(level_req=level)
    else:
        return generate_passive_be_cloze_with_time(level_req=level)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
