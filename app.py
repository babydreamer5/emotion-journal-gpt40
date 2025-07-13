import streamlit as st
from datetime import datetime
import time
from backend import *
from ui import *
from utils import *

# 페이지 설정
st.set_page_config(
    page_title="마음톡 - 나만의 감정일기", 
    page_icon="💜", 
    layout="centered",
    initial_sidebar_state="expanded"
)

def main():
    if 'app_initialized' not in st.session_state:
        init_session_state()

    # SVG 버튼 클릭으로 URL에 'mood' 파라미터가 추가된 경우를 먼저 처리합니다.
    query_params = st.query_params
    if "mood" in query_params:
        mood_map = {"good": "좋음", "normal": "보통", "bad": "나쁨"}
        mood_value = query_params.get("mood")
        if mood_value in mood_map:
            # 인증 상태를 True로 설정하고, 선택된 기분으로 채팅 단계를 시작합니다.
            st.session_state.authenticated = True
            st.session_state.current_mood = mood_map[mood_value]
            st.session_state.current_step = "chat"
            st.session_state.chat_messages = []
            
            # 풍선 효과를 보여줍니다.
            st.balloons()
            
            # URL에서 파라미터를 제거합니다.
            st.query_params.clear()

            # 풍선 애니메이션이 보일 수 있도록 아주 짧은 딜레이를 줍니다.
            time.sleep(0.5)
            
            # 스크립트를 재실행하여 채팅 화면으로 넘어갑니다.
            st.rerun()

    # 테마 스타일을 적용합니다.
    st.markdown(get_theme_style(st.session_state.selected_theme), unsafe_allow_html=True)

    # 일반적인 경우의 인증 상태를 확인합니다.
    if not st.session_state.get("authenticated", False):
        show_login()
        return

    # 라우팅: 현재 단계에 맞는 화면을 보여줍니다.
    if st.session_state.current_step == "mood_selection":
        show_mood_selection()
    elif st.session_state.current_step == "chat":
        show_chat()
    elif st.session_state.current_step == "summary":
        show_summary()
    elif st.session_state.current_step == "trash":
        show_trash()
    elif st.session_state.current_step == "statistics":
        show_statistics()
    elif st.session_state.current_step == "calendar":
        show_calendar()
    elif st.session_state.current_step == "settings":
        show_settings()
    else:
        show_mood_selection()

    # 모든 페이지에서 하단 면책조항 표시
    show_footer()

if __name__ == "__main__":
    main()