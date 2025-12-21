# main.py
import uvicorn
import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # 關鍵！
from pydantic import BaseModel
from typing import List, Optional
import nltk
import lemminflect

# ==========================================
# 1. 初始化與設定 (Setup)
# ==========================================
app = FastAPI()

# 設定 CORS (允許跨網域存取)
# 這是為了讓你的 React 網站 (例如 localhost:3000 或 my-site.com) 能呼叫這個 API
origins = [
    "*", # 生產環境建議改成你前端網站的具體網址，目前先全開方便測試
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 在伺服器啟動時，自動下載必要的語料庫
@app.on_event("startup")
async def startup_event():
    nltk.download('wordnet')
    nltk.download('omw-1.4')
    nltk.download('averaged_perceptron_tagger')
    print("✅ NLTK 資料載入完成")

# ==========================================
# 2. 資料庫與邏輯 (這裡貼上我們之前寫好的完整邏輯)
# ==========================================

# ... (請將我們最後完成的 AGENTS, VERBS, TARGETS, TIME_MARKERS 等資料貼在這裡) ...
# ... (請將 generate_passive_be_cloze_with_time 等函數貼在這裡) ...

# 為了示範，我這裡放一個簡化版的資料與函數
# --- 這裡只是佔位符，請換成你完整的程式碼 ---
AGENTS = [{"word": "The teacher", "person": 3, "number": "singular", "type": "noun"}]
TRANSITIVE_VERBS = [{"base": "write", "vpp": "written", "target_req": "text"}]
TARGETS = [{"word": "the book", "person": 3, "number": "singular", "category": "text"}]
# ---------------------------------------------

class ClozeRequest(BaseModel):
    level: str = "medium" # 預留未來擴充參數

@app.get("/")
def read_root():
    return {"status": "Online", "message": "English Generator API is running!"}

@app.get("/api/generate-cloze")
def get_cloze_question():
    # 呼叫你的生成邏輯
    # question = generate_passive_be_cloze_with_time() 
    # return question
    
    # 測試回傳
    return {
        "question": "The book ____ written by the teacher yesterday.",
        "options": ["was", "were", "is", "are"],
        "answer": "was"
    }

# 這行是給 Render 用的啟動點，不需要 if __name__ == "__main__":
