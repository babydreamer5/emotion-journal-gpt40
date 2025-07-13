import streamlit as st
from datetime import datetime, timedelta
import time
from backend import *

def get_theme_style(theme_name):
    theme = THEMES.get(theme_name, THEMES["라벤더"])
    
    return f"""
    <style>
    .stApp {{
        background: {theme['background']} !important;
    }}
    
    .main .block-container {{
        background: transparent !important;
        padding-bottom: 80px !important;
    }}
    
    .stButton > button {{
        border-radius: 20px !important;
        border: none !important;
        padding: 1rem !important;
        font-size: 1.2rem !important;
        font-weight: bold !important;
        height: 200px !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        white-space: pre-line !important;
        box-shadow: 0 4px 15px {theme['shadow']} !important;
        text-align: center !important;
        cursor: pointer !important;
        background: {theme['button_bg']} !important;
        color: {theme['button_text']} !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-5px) !important;
        box-shadow: 0 10px 30px {theme['shadow']} !important;
        background: {theme['button_hover']} !important;
    }}
    
    .stButton > button:active {{
        transform: translateY(-2px) !important;
    }}
    
    .main-header {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        font-size: 18px;
    }}
    .main-header h1 {{
        font-size: 2.2rem;
        margin-bottom: 0.5rem;
    }}
    .chat-container {{
        background: white;
        border: 2px solid #e3f2fd;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        min-height: 400px;
        font-size: 16px;
    }}
    .ai-message {{
        background: linear-gradient(135deg, #ffeef0 0%, #ffe4e6 100%);
        padding: 1.2rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 4px solid #ff69b4;
        font-size: 16px;
        text-align: left;
    }}
    .user-message {{
        background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
        padding: 1.2rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 4px solid #2196f3;
        text-align: left;
        font-size: 16px;
    }}
    .warning-box {{
        background: linear-gradient(135deg, #ffebee 0%, #fce4ec 100%);
        border: 2px solid #f44336;
        color: #c62828;
        padding: 1.8rem;
        border-radius: 15px;
        margin: 1rem 0;
        font-size: 16px;
    }}
    .summary-box {{
        background: linear-gradient(135deg, #fff3e0 0%, #fce4ec 100%);
        border: 2px solid #ff9800;
        padding: 1.8rem;
        border-radius: 15px;
        margin: 1rem 0;
        font-size: 16px;
    }}
    .token-bar {{
        background: #f0f0f0;
        border-radius: 20px;
        padding: 8px;
        margin: 12px 0;
        font-size: 15px;
    }}
    .footer {{
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: rgba(248, 249, 250, 0.95);
        color: #6c757d;
        text-align: center;
        padding: 12px 20px;
        font-size: 12px;
        border-top: 1px solid #dee2e6;
        backdrop-filter: blur(10px);
        z-index: 999;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    }}
    .stSelectbox label, .stTextArea label, .stButton button {{
        font-size: 16px !important;
    }}
    .stTextArea textarea {{
        font-size: 16px !important;
    }}
    .stSelectbox div {{
        font-size: 16px !important;
    }}
    </style>
    """

def get_korean_postposition(name):
    if not name:
        return "가"
    last_char = name[-1]
    if '가' <= last_char <= '힣':
        has_jongseong = (ord(last_char) - 0xAC00) % 28 > 0
        return "이가" if has_jongseong else "가"
    else:
        return "가"

def check_harmful_content(text: str) -> bool:
    if not text or not isinstance(text, str):
        return False
    
    try:
        text_lower = text.lower().replace(" ", "")
        harmful_patterns = [
            "자살", "죽고싶", "자해", "죽고싶어", "사라지고싶", "끝내고싶", 
            "살기싫", "살고싶지", "죽어버리", "죽었으면", "베고싶", "자살하고"
        ]
        
        return any(pattern in text_lower for pattern in harmful_patterns)
    except Exception:
        return False

def check_violence_content(text: str) -> bool:
    if not text or not isinstance(text, str):
        return False
    
    try:
        text_lower = text.lower().replace(" ", "")
        violence_patterns = [
            "때리고싶", "죽이고싶", "칼", "총", "성폭행", "강간", "폭행", 
            "때렸다", "맞았다", "협박", "폭력", "성추행"
        ]
        
        return any(pattern in text_lower for pattern in violence_patterns)
    except Exception:
        return False

def check_content_with_moderation(text: str) -> dict:
    if not text or not isinstance(text, str):
        return {
            "flagged": False,
            "self_harm": False,
            "violence": False,
            "error": "Empty or invalid text"
        }
    
    try:
        response = client.moderations.create(input=text)
        result = response.results[0]
        
        is_self_harm = (result.categories.self_harm or 
                       result.categories.self_harm_intent or
                       result.categories.self_harm_instructions)
        
        is_violence = (result.categories.violence or 
                      result.categories.harassment or
                      result.categories.harassment_threatening)
        
        return {
            "flagged": result.flagged,
            "self_harm": is_self_harm,
            "violence": is_violence,
            "categories": result.categories,
            "success": True
        }
        
    except Exception as e:
        return {
            "flagged": check_harmful_content(text) or check_violence_content(text),
            "self_harm": check_harmful_content(text),
            "violence": check_violence_content(text),
            "error": str(e),
            "fallback": True
        }

def display_token_bar():
    try:
        token_usage = max(0, int(st.session_state.get('token_usage', 0)))
        max_tokens = MAX_FREE_TOKENS
        
        usage_ratio = min(token_usage / max_tokens, 1.0)
        remaining = max(0, max_tokens - token_usage)
        
        if usage_ratio < 0.5:
            color = "#4CAF50"
            status = "충분해요"
        elif usage_ratio < 0.95:
            color = "#FF9800" 
            status = "적당해요"
        else:
            color = "#F44336"
            status = "조금 부족해요"
        
        st.markdown(f"""
        <div class="token-bar">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <span style="font-size: 14px; font-weight: bold;">💫 AI와 대화할 수 있는 에너지</span>
                <span style="font-size: 12px; color: #666;">{remaining:,} / {max_tokens:,} 남음</span>
            </div>
            <div style="background: #e0e0e0; height: 8px; border-radius: 10px;">
                <div style="background: {color}; width: {usage_ratio * 100:.1f}%; height: 100%; border-radius: 10px;"></div>
            </div>
            <div style="text-align: center; font-size: 12px; color: {color}; margin-top: 5px;">
                상태: {status}
            </div>
        </div>
        """, unsafe_allow_html=True)
    except Exception:
        pass

def calculate_consecutive_days():
    try:
        if not st.session_state.diary_entries:
            return 0
        
        entry_dates = {datetime.strptime(entry['date'], '%Y-%m-%d').date() 
                       for entry in st.session_state.diary_entries if 'date' in entry}
        
        if not entry_dates:
            return 0
        
        sorted_dates = sorted(list(entry_dates), reverse=True)
        
        today = datetime.now().date()
        
        if today not in sorted_dates:
            start_date = today - timedelta(days=1)
            consecutive = 0
        else:
            start_date = today
            consecutive = 1
        
        if consecutive == 1:
            for i in range(1, len(sorted_dates)):
                if sorted_dates[i] == start_date - timedelta(days=i):
                    consecutive += 1
                else:
                    break
        else:
            for i, date in enumerate(sorted_dates):
                if date == start_date - timedelta(days=i):
                    consecutive += 1
                else:
                    break
                    
        return consecutive
    except Exception as e:
        print(f"연속 작성일 계산 오류: {e}")
        return 0

def generate_emotion_stats():
    try:
        if not st.session_state.diary_entries:
            return None
        
        mood_counts = {}
        keyword_counts = {}
        
        for entry in st.session_state.diary_entries:
            try:
                mood = entry.get('mood', '알 수 없음')
                mood_counts[mood] = mood_counts.get(mood, 0) + 1
                
                keywords = entry.get('keywords', [])
                for keyword in keywords:
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
                    
            except Exception:
                continue
        
        total = sum(mood_counts.values())
        mood_stats = []
        for mood, count in mood_counts.items():
            percentage = (count / total) * 100
            mood_stats.append({
                'mood': mood,
                'count': count,
                'percentage': round(percentage, 1)
            })
        
        popular_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'mood_stats': sorted(mood_stats, key=lambda x: x['count'], reverse=True),
            'popular_keywords': popular_keywords
        }
        
    except Exception:
        return None

def search_diaries(keyword):
    try:
        if not keyword or not st.session_state.diary_entries:
            return []
        
        results = []
        keyword_lower = keyword.lower()
        
        for entry in st.session_state.diary_entries:
            try:
                summary = entry.get('summary', '').lower()
                keywords = ' '.join(entry.get('keywords', [])).lower()
                
                if keyword_lower in summary or keyword_lower in keywords:
                    results.append(entry)
            except Exception:
                continue
        
        return results
    except Exception:
        return []

def export_diary_data():
    try:
        active_count = len(st.session_state.diary_entries)
        deleted_count = len(st.session_state.deleted_entries)
        
        if active_count == 0 and deleted_count == 0:
            return "내보낼 일기가 없어요."
        
        export_text = "=== 💜 마음톡 감정일기 백업 ===\n\n"
        
        if active_count > 0:
            export_text += f"📚 나의 일기들 ({active_count}개)\n"
            export_text += "=" * 50 + "\n\n"
            
            for i, entry in enumerate(st.session_state.diary_entries):
                try:
                    export_text += f"📅 날짜: {entry.get('date', '날짜 없음')} {entry.get('time', '')}\n"
                    export_text += f"😊 기분: {entry.get('mood', '기분 없음')}\n"
                    export_text += f"📝 오늘 있었던 일: {entry.get('summary', '내용 없음')}\n"
                    
                    if entry.get('keywords'):
                        export_text += f"🏷️ 감정 키워드: {', '.join(entry['keywords'])}\n"
                    
                    if entry.get('action_items'):
                        export_text += f"💡 AI 친구의 조언:\n"
                        for item in entry['action_items']:
                            export_text += f"   • {item}\n"
                    
                    export_text += "\n" + "-"*30 + "\n\n"
                except Exception:
                    continue
        
        if deleted_count > 0:
            export_text += f"\n🗑️ 임시 보관함 ({deleted_count}개)\n"
            export_text += "=" * 50 + "\n\n"
            
            for i, entry in enumerate(st.session_state.deleted_entries):
                try:
                    export_text += f"📅 원본 날짜: {entry.get('date', '날짜 없음')} {entry.get('time', '')}\n"
                    export_text += f"🗑️ 보관함에 들어온 날: {entry.get('deleted_date', '알 수 없음')}\n"
                    export_text += f"⏰ 자동삭제 예정일: {entry.get('auto_delete_date', '알 수 없음')}\n"
                    export_text += f"😊 기분: {entry.get('mood', '기분 없음')}\n"
                    export_text += f"📝 오늘 있었던 일: {entry.get('summary', '내용 없음')}\n"
                    
                    if entry.get('keywords'):
                        export_text += f"🏷️ 감정 키워드: {', '.join(entry['keywords'])}\n"
                    
                    export_text += "\n" + "-"*30 + "\n\n"
                except Exception:
                    continue
        
        export_text += f"\n📊 총계: 일기 {active_count}개, 임시보관 {deleted_count}개\n"
        export_text += f"백업 날짜: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}"
        
        return export_text
    except Exception as e:
        return f"❌ 데이터 내보내기 중 문제가 생겼어요: {str(e)}"

def move_to_trash(diary_entry):
    try:
        if delete_diary_from_db(diary_entry):
            st.session_state.diary_entries = load_diaries_from_db()
            st.session_state.deleted_entries = load_deleted_entries_from_db()
            return True
        return False
    except Exception as e:
        print(f"일기 삭제 오류: {e}")
        return False

def restore_from_trash(trash_entry):
    try:
        if restore_from_trash_db(trash_entry):
            st.session_state.diary_entries = load_diaries_from_db()
            st.session_state.deleted_entries = load_deleted_entries_from_db()
            return True
        return False
    except Exception as e:
        print(f"일기 복원 오류: {e}")
        return False

def permanent_delete_from_trash(trash_entry):
    try:
        if permanent_delete_from_trash_db(trash_entry):
            st.session_state.deleted_entries = load_deleted_entries_from_db()
            return True
        return False
    except Exception as e:
        print(f"영구 삭제 오류: {e}")
        return False

def clean_expired_trash():
    try:
        if clean_expired_trash_db():
            st.session_state.deleted_entries = load_deleted_entries_from_db()
        return True
    except Exception as e:
        print(f"휴지통 정리 오류: {e}")
        return False