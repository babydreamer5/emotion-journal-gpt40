import streamlit as st
from datetime import datetime, timedelta
from openai import OpenAI
import sqlite3
import json
from typing import List, Dict

# 상수 설정
APP_PASSWORD = "2752"
MAX_FREE_TOKENS = 100000
HARMFUL_KEYWORDS = [
    "자살", "죽고싶다", "죽고 싶다", "자살하고", "자해", "손목", "극단적", "생을 마감",
    "죽고 싶어", "사라지고 싶다", "끝내고 싶다", "힘들어서 죽을", "죽어버리고", 
    "죽었으면", "살기 싫다", "살고 싶지", "베고 싶다", "목 매달아"
]

VIOLENCE_KEYWORDS = [
    "때리고 싶다", "죽이고 싶다", "칼", "총", "성폭행", "강간", "폭행", "때렸다",
    "맞았다", "협박", "폭력", "성추행", "칼로 찌르", "총으로 쏘"
]

DEFAULT_AI_NAME = "루나"
RECOMMENDED_AI_NAMES = ["루나", "별이", "하늘이", "민트", "소라", "유나"]

THEMES = {
    "핑크": {
        "background": "linear-gradient(135deg, #fefefe 0%, #faf9f7 100%)",
        "button_bg": "linear-gradient(135deg, #ffeef0 0%, #ffe4e6 100%)",
        "button_hover": "linear-gradient(135deg, #ffd7dc 0%, #ffb3ba 100%)",
        "button_text": "#8e4b5a",
        "shadow": "rgba(255, 182, 193, 0.3)"
    },
    "블루": {
        "background": "linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%)",
        "button_bg": "linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)",
        "button_hover": "linear-gradient(135deg, #90caf9 0%, #64b5f6 100%)",
        "button_text": "#1565c0",
        "shadow": "rgba(33, 150, 243, 0.3)"
    },
    "그린": {
        "background": "linear-gradient(135deg, #f1f8e9 0%, #e8f5e8 100%)",
        "button_bg": "linear-gradient(135deg, #e8f5e8 0%, #c8e6c8 100%)",
        "button_hover": "linear-gradient(135deg, #a5d6a7 0%, #81c784 100%)",
        "button_text": "#2e7d32",
        "shadow": "rgba(76, 175, 80, 0.3)"
    },
    "라벤더": {
        "background": "linear-gradient(135deg, #faf9fc 0%, #f3e5f5 100%)",
        "button_bg": "linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%)",
        "button_hover": "linear-gradient(135deg, #ce93d8 0%, #ba68c8 100%)",
        "button_text": "#7b1fa2",
        "shadow": "rgba(156, 39, 176, 0.3)"
    }
}

DB_PATH = "mindtalk_diary.db"

# OpenAI 클라이언트 초기화
@st.cache_resource
def initialize_openai():
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
        if not api_key or not api_key.strip():
            st.error("OpenAI API 키가 비어있습니다!")
            st.stop()
        
        client = OpenAI(api_key=api_key)
        
        try:
            client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
                temperature=0
            )
        except Exception as test_error:
            st.error(f"OpenAI API 연결 실패: {str(test_error)}")
            st.stop()
            
        return client
        
    except KeyError:
        st.error("OpenAI API 키를 찾을 수 없습니다!")
        st.stop()
    except Exception as e:
        st.error(f"OpenAI 클라이언트 초기화 오류: {str(e)}")
        st.stop()

def check_api_key():
    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
        if not api_key:
            st.error("OpenAI API 키가 설정되지 않았습니다!")
            return False
        
        if len(api_key.strip()) < 10:
            st.error("API 키가 너무 짧습니다.")
            return False
            
        return True
    except Exception as e:
        st.error(f"API 키 확인 중 오류 발생: {str(e)}")
        return False

# API 키 체크 후 클라이언트 초기화
if check_api_key():
    try:
        client = initialize_openai()
    except Exception as e:
        st.error(f"초기화 실패: {str(e)}")
        st.stop()
else:
    st.stop()

# 데이터베이스 관련 함수들
def init_database():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS diary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            mood TEXT NOT NULL,
            summary TEXT NOT NULL,
            keywords TEXT,
            suggested_keywords TEXT,
            action_items TEXT,
            chat_messages TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS deleted_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id INTEGER,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            mood TEXT NOT NULL,
            summary TEXT NOT NULL,
            keywords TEXT,
            suggested_keywords TEXT,
            action_items TEXT,
            chat_messages TEXT,
            deleted_date TEXT NOT NULL,
            auto_delete_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_tokens INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"데이터베이스 초기화 오류: {e}")
        return False

def save_diary_to_db(diary_entry):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO diary_entries 
        (date, time, mood, summary, keywords, suggested_keywords, action_items, chat_messages)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            diary_entry['date'],
            diary_entry['time'],
            diary_entry['mood'],
            diary_entry['summary'],
            json.dumps(diary_entry.get('keywords', []), ensure_ascii=False),
            json.dumps(diary_entry.get('suggested_keywords', []), ensure_ascii=False),
            json.dumps(diary_entry.get('action_items', []), ensure_ascii=False),
            json.dumps(diary_entry.get('chat_messages', []), ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"일기 저장 오류: {e}")
        return False

def load_diaries_from_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT date, time, mood, summary, keywords, suggested_keywords, action_items, chat_messages
        FROM diary_entries 
        ORDER BY date, time
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        diaries = []
        for row in rows:
            diary = {
                'date': row[0],
                'time': row[1],
                'mood': row[2],
                'summary': row[3],
                'keywords': json.loads(row[4]) if row[4] else [],
                'suggested_keywords': json.loads(row[5]) if row[5] else [],
                'action_items': json.loads(row[6]) if row[6] else [],
                'chat_messages': json.loads(row[7]) if row[7] else []
            }
            diaries.append(diary)
        
        return diaries
    except Exception as e:
        print(f"일기 불러오기 오류: {e}")
        return []

def delete_diary_from_db(diary_entry):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT rowid FROM diary_entries 
        WHERE date = ? AND time = ? AND summary = ?
        ''', (diary_entry['date'], diary_entry['time'], diary_entry['summary']))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False
        
        original_id = result[0]
        
        deleted_date = datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')
        auto_delete_date = (datetime.now() + timedelta(days=30)).strftime('%Y년 %m월 %d일')
        
        cursor.execute('''
        INSERT INTO deleted_entries 
        (original_id, date, time, mood, summary, keywords, suggested_keywords, action_items, chat_messages, deleted_date, auto_delete_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            original_id,
            diary_entry['date'],
            diary_entry['time'],
            diary_entry['mood'],
            diary_entry['summary'],
            json.dumps(diary_entry.get('keywords', []), ensure_ascii=False),
            json.dumps(diary_entry.get('suggested_keywords', []), ensure_ascii=False),
            json.dumps(diary_entry.get('action_items', []), ensure_ascii=False),
            json.dumps(diary_entry.get('chat_messages', []), ensure_ascii=False),
            deleted_date,
            auto_delete_date
        ))
        
        cursor.execute('DELETE FROM diary_entries WHERE rowid = ?', (original_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"일기 삭제 오류: {e}")
        return False

def load_deleted_entries_from_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT date, time, mood, summary, keywords, suggested_keywords, action_items, chat_messages, deleted_date, auto_delete_date
        FROM deleted_entries 
        ORDER BY deleted_date DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        deleted_entries = []
        for row in rows:
            entry = {
                'date': row[0],
                'time': row[1],
                'mood': row[2],
                'summary': row[3],
                'keywords': json.loads(row[4]) if row[4] else [],
                'suggested_keywords': json.loads(row[5]) if row[5] else [],
                'action_items': json.loads(row[6]) if row[6] else [],
                'chat_messages': json.loads(row[7]) if row[7] else [],
                'deleted_date': row[8],
                'auto_delete_date': row[9]
            }
            deleted_entries.append(entry)
        
        return deleted_entries
    except Exception as e:
        print(f"휴지통 불러오기 오류: {e}")
        return []

def restore_from_trash_db(trash_entry):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO diary_entries 
        (date, time, mood, summary, keywords, suggested_keywords, action_items, chat_messages)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trash_entry['date'],
            trash_entry['time'],
            trash_entry['mood'],
            trash_entry['summary'],
            json.dumps(trash_entry.get('keywords', []), ensure_ascii=False),
            json.dumps(trash_entry.get('suggested_keywords', []), ensure_ascii=False),
            json.dumps(trash_entry.get('action_items', []), ensure_ascii=False),
            json.dumps(trash_entry.get('chat_messages', []), ensure_ascii=False)
        ))
        
        cursor.execute('''
        DELETE FROM deleted_entries 
        WHERE date = ? AND time = ? AND summary = ? AND deleted_date = ?
        ''', (trash_entry['date'], trash_entry['time'], trash_entry['summary'], trash_entry['deleted_date']))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"일기 복원 오류: {e}")
        return False

def permanent_delete_from_trash_db(trash_entry):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        DELETE FROM deleted_entries 
        WHERE date = ? AND time = ? AND summary = ? AND deleted_date = ?
        ''', (trash_entry['date'], trash_entry['time'], trash_entry['summary'], trash_entry['deleted_date']))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"영구 삭제 오류: {e}")
        return False

def clean_expired_trash_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        today = datetime.now().date()
        
        cursor.execute('SELECT auto_delete_date FROM deleted_entries')
        rows = cursor.fetchall()
        
        expired_dates = []
        for row in rows:
            try:
                auto_delete_date_str = row[0]
                auto_delete_date = datetime.strptime(auto_delete_date_str.replace('년 ', '-').replace('월 ', '-').replace('일', ''), '%Y-%m-%d').date()
                if auto_delete_date <= today:
                    expired_dates.append(auto_delete_date_str)
            except:
                continue
        
        for expired_date in expired_dates:
            cursor.execute('DELETE FROM deleted_entries WHERE auto_delete_date = ?', (expired_date,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"휴지통 정리 오류: {e}")
        return False

def save_setting_to_db(key, value):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO app_settings (setting_key, setting_value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, str(value)))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"설정 저장 오류: {e}")
        return False

def load_setting_from_db(key, default_value):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT setting_value FROM app_settings WHERE setting_key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        else:
            return default_value
    except Exception as e:
        print(f"설정 불러오기 오류: {e}")
        return default_value

def save_token_usage_to_db(tokens):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO token_usage (id, total_tokens, last_updated)
        VALUES (1, ?, CURRENT_TIMESTAMP)
        ''', (tokens,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"토큰 사용량 저장 오류: {e}")
        return False

def load_token_usage_from_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT total_tokens FROM token_usage WHERE id = 1')
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        else:
            return 0
    except Exception as e:
        print(f"토큰 사용량 불러오기 오류: {e}")
        return 0

def save_data_to_db():
    try:
        save_setting_to_db('ai_name', st.session_state.get('ai_name', DEFAULT_AI_NAME))
        save_setting_to_db('selected_theme', st.session_state.get('selected_theme', '라벤더'))
        save_setting_to_db('consecutive_days', st.session_state.get('consecutive_days', 0))
        save_setting_to_db('last_entry_date', st.session_state.get('last_entry_date', ''))
        
        save_token_usage_to_db(st.session_state.get('token_usage', 0))
        
        return True
    except Exception as e:
        print(f"데이터 저장 오류: {e}")
        return False

def load_data_from_db():
    try:
        st.session_state.diary_entries = load_diaries_from_db()
        st.session_state.deleted_entries = load_deleted_entries_from_db()
        
        st.session_state.ai_name = load_setting_from_db('ai_name', DEFAULT_AI_NAME)
        st.session_state.selected_theme = load_setting_from_db('selected_theme', '라벤더')
        st.session_state.consecutive_days = int(load_setting_from_db('consecutive_days', 0))
        st.session_state.last_entry_date = load_setting_from_db('last_entry_date', '')
        
        st.session_state.token_usage = load_token_usage_from_db()
        
        return True
    except Exception as e:
        print(f"데이터 불러오기 오류: {e}")
        return False

# AI 응답 관련 함수들
def get_ai_response(user_message: str, conversation_history: List[Dict], context: List[Dict] = None) -> Dict:
    if not user_message or not user_message.strip():
        return {
            "response": "메시지를 입력해주세요.",
            "tokens_used": 0,
            "success": False
        }
    
    if st.session_state.token_usage >= MAX_FREE_TOKENS:
        return {
            "response": "죄송해요. AI와 대화할 수 있는 에너지가 다 떨어졌어요.",
            "tokens_used": 0,
            "success": False
        }
    
    try:
        context_text = ""
        if context and isinstance(context, list):
            try:
                recent_context = context[-2:]
                context_summaries = []
                for ctx in recent_context:
                    if isinstance(ctx, dict) and 'summary' in ctx and 'action_items' in ctx:
                        action_items = ctx.get('action_items', [])
                        if isinstance(action_items, list):
                            context_summaries.append(f"지난번에 이야기했던 것: {ctx['summary']}")
                
                if context_summaries:
                    context_text = "\n\n이전 대화 참고:\n" + "\n".join(context_summaries) + "\n\n"
            except Exception:
                context_text = ""
        
        mood_styles = {
            "좋음": {
                "tone": "밝고 활기찬 말투로 기쁨을 함께 나누세요",
                "approach": "긍정적인 감정을 더 깊이 느낄 수 있도록 격려하세요",
            },
            "보통": {
                "tone": "편안하고 자연스러운 말투로 대화하세요",
                "approach": "일상의 소소한 의미를 찾을 수 있도록 도와주세요",
            },
            "나쁨": {
                "tone": "부드럽고 따뜻한 말투로 위로하세요",
                "approach": "힘든 감정을 안전하게 표현할 수 있도록 공간을 만들어주세요",
            }
        }
        
        current_mood = st.session_state.get('current_mood', '보통')
        mood_config = mood_styles.get(current_mood, mood_styles["보통"])
        ai_name = st.session_state.get('ai_name', DEFAULT_AI_NAME)
        
        system_prompt = f"""당신은 10대를 위한 따뜻하고 공감적인 AI 친구 {ai_name}입니다.

핵심 원칙:
- 친구처럼 편하게 대화하되, 존댓말을 사용하세요
- 판단하지 말고 있는 그대로 공감해주세요
- 자해나 위험한 행동은 절대 권하지 마세요
- 응답은 2-3문장으로 간결하게 해주세요

현재 기분: {current_mood}
대화 스타일:
- {mood_config['tone']}
- {mood_config['approach']}
- 먼저 짧게 공감하고, 구체적인 질문 1개만 하세요

구체적 대화 가이드:
- 사용자가 구체적인 내용을 언급하면 그것에 대해 구체적으로 반응하세요
- 예: "수학시험 망했어" → "수학시험 어려웠구나. 어떤 부분이 가장 힘들었어요?"
- 예: "친구랑 싸웠어" → "친구와 싸우니 속상하겠어요. 어떤 일이 있었나요?"
- 일반적인 응답 대신 사용자의 상황에 맞춘 질문을 하세요

응답 길이: 최대 2-3문장으로 간결하게
응원 멘트: 과도한 응원보다는 자연스러운 공감 우선

위험 상황 대응:
- 자해/자살 언급 시: 공감 후 "이런 마음이 들 때는 전문가와 이야기하는 것이 도움될 수 있어요. 자살예방상담 109번이나 청소년상담 1388번에서 도움받을 수 있어요."
- 폭력 상황 언급 시: "안전이 가장 중요해요. 위험하다면 112번이나 청소년상담 1388번에 도움을 요청하세요."

{context_text}

간결하고 자연스러운 대화를 해주세요."""

        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history and isinstance(conversation_history, list):
            for msg in conversation_history[-10:]:
                messages.append(msg)
        
        messages.append({"role": "user", "content": user_message})
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=200,
            timeout=30
        )
        
        ai_response = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        st.session_state.token_usage += tokens_used
        save_token_usage_to_db(st.session_state.token_usage)
        
        return {
            "response": ai_response,
            "tokens_used": tokens_used,
            "success": True
        }
        
    except Exception as e:
        error_msg = str(e).lower()
        
        if "api" in error_msg or "auth" in error_msg:
            error_response = "API 문제가 생겼어요. 잠시 후 다시 시도해주세요."
        elif "quota" in error_msg or "limit" in error_msg:
            error_response = "사용량 한도에 도달했어요. 관리자에게 문의해주세요."
        elif "timeout" in error_msg:
            error_response = "응답이 너무 오래 걸려요. 다시 시도해주세요."
        elif "rate" in error_msg:
            error_response = "요청이 너무 많아요. 잠시 후 다시 시도해주세요."
        else:
            error_response = "일시적으로 문제가 생겼어요. 다시 시도해주세요."
        
        return {
            "response": error_response,
            "tokens_used": 0,
            "success": False
        }

def generate_conversation_summary(messages: List[Dict]) -> Dict:
    try:
        if not messages or not isinstance(messages, list):
            return {
                "summary": "대화 내용이 없어요",
                "keywords": ["#감정나눔"],
                "action_items": ["오늘도 고생 많았어요"],
                "success": False
            }
        
        user_messages = []
        for msg in messages:
            try:
                if isinstance(msg, dict) and msg.get("role") == "user" and msg.get("content"):
                    user_messages.append(msg["content"])
            except Exception:
                continue
        
        if not user_messages:
            return {
                "summary": "사용자 메시지가 없어요",
                "keywords": ["#감정나눔"],
                "action_items": ["오늘도 고생 많았어요"],
                "success": False
            }
        
        conversation_text = "\n".join(user_messages)
        
        if len(conversation_text) > 2000:
            conversation_text = conversation_text[:2000] + "..."
        
        prompt = f"""다음 대화 내용을 분석해서 아래 형식으로 응답해주세요:

대화 내용:
{conversation_text}

분석 요청:
1. 오늘 있었던 일을 1-2줄로 요약
2. 대화에서 느껴진 감정 키워드 5개 추출 (예: #기쁨, #불안, #성취감 등)
3. 사용자에게 도움이 될 따뜻하고 친근한 조언 3개 제안 (친구 같은 말투로, ~해요/~랍니다 교차 사용)

응답 형식:
요약: [1-2줄 요약]
감정키워드: #키워드1, #키워드2, #키워드3, #키워드4, #키워드5
액션아이템: 
- [~해요 말투의 따뜻한 조언]
- [~랍니다 말투의 친근한 조언]
- [~해요 말투의 격려 메시지]"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
            timeout=30
        )
        
        result = response.choices[0].message.content
        st.session_state.token_usage += response.usage.total_tokens
        
        lines = result.strip().split('\n')
        summary = ""
        keywords = []
        action_items = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('요약:'):
                summary = line.replace('요약:', '').strip()
            elif line.startswith('감정키워드:'):
                keyword_text = line.replace('감정키워드:', '').strip()
                keywords = [k.strip() for k in keyword_text.split(',') if k.strip()]
            elif line.startswith('액션아이템:'):
                current_section = "actions"
            elif current_section == "actions" and line.startswith('-'):
                action_item = line.replace('-', '').strip()
                if action_item:
                    action_items.append(action_item)
        
        if not summary:
            summary = "오늘의 감정을 나누었어요"
        if not keywords:
            keywords = ["#감정나눔"]
        if not action_items:
            action_items = ["오늘도 고생 많았어요"]
        
        keywords = keywords[:5]
        action_items = action_items[:3]
        
        return {
            "summary": summary,
            "keywords": keywords,
            "action_items": action_items,
            "success": True
        }
        
    except Exception:
        return {
            "summary": "요약을 만드는 중에 문제가 생겼어요",
            "keywords": ["#감정나눔"],
            "action_items": ["오늘도 고생 많았어요"],
            "success": False
        }

def generate_emotion_keywords(chat_messages, mood):
    try:
        if not chat_messages:
            default_keywords = {
                "좋음": ["#기쁨", "#활기", "#만족", "#희망", "#평온"],
                "보통": ["#평범", "#일상", "#차분", "#보통", "#안정"],
                "나쁨": ["#우울", "#피곤", "#스트레스", "#불안", "#힘듦"]
            }
            return default_keywords.get(mood, ["#감정나눔", "#일상", "#생각", "#마음", "#기분"])
        
        user_messages = []
        for msg in chat_messages:
            if isinstance(msg, dict) and msg.get("role") == "user":
                user_messages.append(msg.get("content", ""))
        
        conversation_text = "\n".join(user_messages)
        if len(conversation_text) > 1500:
            conversation_text = conversation_text[:1500] + "..."
        
        prompt = f"""다음 대화 내용을 분석해서 사용자의 감정을 나타내는 키워드 5개를 제시해주세요.

대화 내용:
{conversation_text}

현재 기분: {mood}

요청사항:
- 대화에서 느껴지는 구체적인 감정 키워드 5개
- 각 키워드는 # 붙여서 해시태그 형태로
- 사용자가 실제로 느꼈을 감정들 위주로
- 너무 추상적이지 않고 구체적으로

응답 형식:
#키워드1, #키워드2, #키워드3, #키워드4, #키워드5"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100,
            timeout=20
        )
        
        result = response.choices[0].message.content.strip()
        st.session_state.token_usage += response.usage.total_tokens
        
        keywords = [k.strip() for k in result.split(',') if k.strip().startswith('#')]
        
        if len(keywords) < 5:
            default_extras = ["#감정나눔", "#일상", "#생각", "#마음", "#기분"]
            keywords.extend(default_extras[:5-len(keywords)])
        
        return keywords[:5]
        
    except Exception as e:
        print(f"감정 키워드 생성 오류: {e}")
        default_keywords = {
            "좋음": ["#기쁨", "#활기", "#만족", "#희망", "#평온"],
            "보통": ["#평범", "#일상", "#차분", "#보통", "#안정"],
            "나쁨": ["#우울", "#피곤", "#스트레스", "#불안", "#힘듦"]
        }
        return default_keywords.get(mood, ["#감정나눔", "#일상", "#생각", "#마음", "#기분"])

# 세션 상태 초기화
def init_session_state():
    defaults = {
        "authenticated": False,
        "current_step": "mood_selection",
        "current_mood": None,
        "chat_messages": [],
        "diary_entries": [],
        "conversation_context": [],
        "token_usage": 0,
        "deleted_entries": [],
        "temp_diary_data": {},
        "ai_name": DEFAULT_AI_NAME,
        "ai_typing": False,
        "menu_option": "🏠 홈",
        "selected_theme": "라벤더",
        "consecutive_days": 0,
        "last_entry_date": None,
        "app_initialized": True
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    load_data_from_db()
    
    for key, default_value in defaults.items():
        try:
            if key == "diary_entries" and not isinstance(st.session_state[key], list):
                st.session_state[key] = []
            elif key == "deleted_entries" and not isinstance(st.session_state[key], list):
                st.session_state[key] = []
            elif key == "token_usage" and not isinstance(st.session_state[key], (int, float)):
                st.session_state[key] = 0
        except Exception as e:
            st.session_state[key] = default_value

# 데이터베이스 초기화
init_database()