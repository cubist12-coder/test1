import streamlit as st
import pandas as pd
import altair as alt
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
# 비밀번호가 설정되지 않았으면 기본값 1234
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
    # 데이터 가져오기 (최신순 정렬)
    response = supabase.table("student_submissions").select("*").order("created_at", desc=True).execute()
    rows = response.data
    
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    
    # (1) 시간대 변환 (UTC -> KST)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
        # DB 시간이 UTC라고 가정
        df["created_at"] = df["created_at"].dt.tz_convert("Asia/Seoul").dt.strftime("%Y-%m-%d %H:%M:%S")

    # (2) 정답 여부(O/X) 추출 로직
    def check_correct(text):
        if isinstance(text, str) and text.strip().startswith("O:"):
            return 1
        return 0

    # 안전하게 컬럼이 있는지 확인 후 처리
    if "feedback_1" in df.columns:
        df["Q1_정답"] = df["feedback_1"].apply(check_correct)
    else:
        df["Q1_정답"] = 0

    if "feedback_2" in df.columns:
        df["Q2_정답"] = df["feedback_2"].apply(check_correct)
    else:
        df["Q2_정답"] = 0

    if "feedback_3" in df.columns:
        df["Q3_정답"] = df["feedback_3"].apply(check_correct)
    else:
        df["Q3_정답"] = 0
    
    # 총점 계산
    df["총점"] = df["Q1_정답"] + df["Q2_정답"] + df["Q3_정답"]

    return df

# 새로고침 버튼
if st.button("🔄 데이터 새로고침"):
    fetch_data.clear()
    st.rerun()

df = fetch_data()

# ── 5. 시각화 및 통계 표시 ──
if df.empty:
    st.warning("아직 제출된 데이터가 없습니다.")
else:
    # [상단] 주요 지표 (KPI)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 제출 학생", f"{len(df)}명")
    with col2:
        total_correct = df[["Q1_정답", "Q2_정답", "Q3_정답"]].sum().sum()
        total_questions = len(df) * 3
        avg_rate = (total_correct / total_questions) * 100 if total_questions > 0 else 0
        st.metric("전체 정답률", f"{avg_rate:.1f}%")
    with col3:
        avg_score = df["총점"].mean()
        st.metric("반 평균 점수", f"{avg_score:.1f} / 3.0")
    with col4:
        # 최근 제출자가 있는지 확인
        if not df.empty and 'student_id' in df.columns:
            recent_student = df.iloc[0]['student_id']
            st.metric("최근 제출", recent_student)

    st.markdown("---")

    # [중단] 그래프 섹션
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("📉 문항별 정답률 비교")
