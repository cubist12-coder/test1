import streamlit as st
import pandas as pd
import altair as alt # 시각화를 위한 라이브러리
from supabase import create_client, Client
from datetime import datetime

# ── 1. 페이지 설정 ──
st.set_page_config(page_title="교사용 대시보드", layout="wide")

# ── 2. Supabase 연결 설정 ──
@st.cache_resource
def get_supabase_client() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
        return create_client(url, key)
    except Exception:
        st.error("Secrets 설정이 누락되었습니다. (.streamlit/secrets.toml 확인)")
        st.stop()

supabase = get_supabase_client()

# ── 3. 로그인 설정 ──
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "1234")

if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False

def check_password():
    if st.session_state.password_input == ADMIN_PASSWORD:
        st.session_state.is_authenticated = True
    else:
        st.error("비밀번호가 틀렸습니다.")

if not st.session_state.is_authenticated:
    st.title("🔒 교사용 대시보드 로그인")
    st.text_input("비밀번호를 입력하세요", type="password", key="password_input", on_change=check_password)
    st.stop()

# =========================================================
# 메인 대시보드 시작
# =========================================================

st.title("📊 학생 서술형 답안 대시보드")

# ── 4. 데이터 불러오기 및 전처리 ──
@st.cache_data(ttl=60)
def fetch_data():
    response = supabase.table("student_submissions").select("*").order("created_at", desc=True).execute()
    rows = response.data
    
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    
    # (1) 시간대 변환 (UTC -> KST)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["created_at"] = df["created_at"].dt.tz_convert("Asia/Seoul").dt.strftime("%Y-%m-%d %H:%M:%S")

    # (2) 정답 여부(O/X) 추출 로직 추가
    # 피드백 문자열이 "O:"로 시작하면 정답(1), 아니면 오답(0)으로 처리
    def check_correct(text):
        if isinstance(text, str) and text.strip().startswith("O:"):
            return 1
        return 0

    df["Q1_정답"] = df["feedback_1"].apply(check_correct)
    df["Q2_정답"] = df["feedback_2"].apply(check_correct)
    df["Q3_정답"] = df["feedback_3"].apply(check_correct)
    
    # 학생별 총점 계산 (3점 만점)
    df["총점"] = df["Q1_정답"] + df["Q2_정답"] + df["Q3_정답"]

    return df

# 새로고침 버튼
if st.button("🔄 데이터 새로고침"):
    fetch_data.clear()
    st.rerun()

df = fetch_data()

# ── 5. 시각화 및 통계 표시 ──
if df.empty:
