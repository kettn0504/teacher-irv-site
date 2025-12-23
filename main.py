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
# 3. [核心升級] 動態連接詞生成引擎
# ==========================================

class ConjunctionGenerator:
    """
    動態連接詞生成器：
    利用「情境模組」來組裝句子，而非死背硬記。
    """
    
    # 定義情境模組 (Logic Modules)
    SCENARIOS = {
        # --- 情境 1: 天氣 (Weather) ---
        "weather_bad": {
            "subjects": ["It", "The weather"],
            "causes": ["was raining hard", "was very stormy", "was terrible outside"],
            "effects_logical": ["we stayed at home", "the game was canceled", "I took a taxi", "we didn't go out"],
            "effects_contrast": ["we went swimming", "he still went out", "the game continued"], # 用於 but/although
            "level": 1
        },
        
        # --- 情境 2: 健康 (Health) ---
        "health_sick": {
            "subjects": ["He", "She", "Tom", "The boy"],
            "causes": ["was sick", "had a fever", "didn't feel well", "had a bad cold"],
            "effects_logical": ["went to the doctor", "took some medicine", "stayed in bed", "didn't go to school"],
            "effects_contrast": ["still went to work", "refused to see a doctor", "looked very happy"],
            "level": 1
        },

        # --- 情境 3: 學習與考試 (Study) ---
        "study_hard": {
            "subjects": ["The student", "Mary", "He", "She"],
            "causes": ["studied very hard", "prepared for the test", "read many books"],
            "effects_logical": ["passed the exam", "got a good grade", "became very smart"],
            "effects_contrast": ["failed the test", "got a bad score", "didn't understand the question"],
            "level": 2
        },

        # --- 情境 4: 經濟與購買 (Money) ---
        "money_expensive": {
            "subjects": ["The car", "The house", "The bag"],
            "causes": ["was too expensive", "cost a lot of money", "was not cheap"],
            "effects_logical": ["I didn't buy it", "we couldn't afford it", "he decided not to get it"],
            "effects_contrast": ["he bought it anyway", "she paid for it", "it sold out quickly"],
            "level": 2
        },

        # --- 情境 5: 飢餓 (Hunger) ---
        "physical_hungry": {
            "subjects": ["I", "He", "The dog", "The baby"],
            "causes": ["was very hungry", "hadn't eaten all day", "was starving"],
            "effects_logical": ["ate a big burger", "cooked a meal", "asked for food"],
            "effects_contrast": ["didn't want to eat", "gave the food away", "kept working"],
            "level": 1
        },
        
        # --- 情境 6: 趕時間 (Time/Hurry) ---
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
        # 1. 篩選符合等級的情境
        available_keys = [k for k, v in ConjunctionGenerator.SCENARIOS.items() if v["level"] <= level_req]
        if not available_keys: available_keys = list(ConjunctionGenerator.SCENARIOS.keys())
        
        # 2. 隨機選一個情境 (例如: weather_bad)
        key = random.choice(available_keys)
        data = ConjunctionGenerator.SCENARIOS[key]
        
        # 3. 隨機選主詞
        subj = random.choice(data["subjects"])
        
        # 4. 隨機決定考哪種邏輯 (因果 vs 轉折 vs 條件)
        # patterns: 
        # A: [Cause], so [Effect].
        # B: [Effect] because [Cause].
        # C: [Cause], but [Contrast].
        # D: Although [Cause], [Contrast].
        
        pattern_type = random.choice(["so", "because", "but", "although"])
        
        # 根據 pattern 準備句子成分
        cause = random.choice(data["causes"])
        
        # 處理主詞單複數/人稱對應 (簡易版：如果主詞是 It/The weather，動詞不變；如果是人，需注意代名詞)
        # 為了簡化，我們假設 effect 的主詞可以共用或省略，或者我們在 effect 裡寫完整句子
        # 這裡做一個簡單的代名詞替換邏輯
        pronoun = "he" # default
        if subj in ["She", "Mary", "The girl"]: pronoun = "she"
        elif subj in ["It", "The weather", "The car", "The house"]: pronoun = "it"
        elif subj in ["We"]: pronoun = "we"
        elif subj in ["They", "The students"]: pronoun = "they"
        elif subj in ["I"]: pronoun = "I"
        elif subj in ["You"]: pronoun = "you"
        
        # 簡單修飾：有些 effect 句子可能需要加上代名詞
        # 我們直接從 data 裡選，這裡假設 data 裡的 effect 都是完整的子句或動詞片語
        # 為了讓句子通順，如果 effect 開頭是動詞 (went, ate)，我們加上代名詞
        
        def add_pronoun(text, pron):
            # 簡單判斷：如果開頭是小寫單字，通常是動詞，加上代名詞
            if text[0].islower(): return f"{pron} {text}"
            return text

        effect_logical = add_pronoun(random.choice(data["effects_logical"]), pronoun)
        effect_contrast = add_pronoun(random.choice(data["effects_contrast"]), pronoun)

        # 5. 組裝題目
        question = ""
        answer = ""
        distractors = []

        if pattern_type == "so":
            # [Subject] [Cause], ____ [Effect].
            question = f"{subj} {cause}, ____ {effect_logical}."
            answer = "so"
            distractors = ["but", "because", "although"]

        elif pattern_type == "because":
            # [Subject/Pronoun] [Effect] ____ [Subject] [Cause].
            # 這裡要注意，because 通常接原因。
            # 例: He went to doctor ____ he was sick.
            # 為了句子通順，我們重組一下：
            q_part1 = effect_logical.capitalize() # Effect 放前
            # Cause 放後，需加上主詞 (如果 cause 字串沒主詞)
            # data['causes'] 通常是 "was sick"，所以要加 subj
            q_part2 = f"{subj} {cause}"
            
            # 修正：如果 q_part1 已經有主詞 (He went...)，那 q_part2 用代名詞 (he was...)
            # 但我們的 effect_logical 是用 add_pronoun 產生的 (e.g., "he went...")
            # 所以 q_part1 = "He went...", q_part2 = "he was sick"
            q_part2 = f"{pronoun} {cause}"
            
            question = f"{q_part1} ____ {q_part2}."
            answer = "because"
            distractors = ["so", "but", "although"]

        elif pattern_type == "but":
            # [Subject] [Cause], ____ [Contrast].
            question = f"{subj} {cause}, ____ {effect_contrast}."
            answer = "but"
            distractors = ["so", "because", "if"]

        elif pattern_type == "although":
            # ____ [Subject] [Cause], [Contrast].
            # 句首大寫處理
            question = f"____ {subj} {cause}, {effect_contrast}."
            answer = "Although"
            distractors = ["Because", "So", "But"] # 大寫干擾項

        random.shuffle(distractors)
        final_options = distractors[:3]
        final_options.append(answer)
        random.shuffle(final_options)

        return {
            "question": question,
            "options": final_options,
            "answer": answer
        }

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
