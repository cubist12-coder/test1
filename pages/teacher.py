import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import pytz # 시간대 변환을 위한 라이브러리

# ── 1. 페이지 설정 ──
st.set_page_config(page_title="교사용 대시보드", layout="wide")

# ── 2. Supabase 연결 설정 (캐싱) ──
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

# ── 3. 간단한 로그인 (비밀번호 보호) ──
# 실제 배포 시에는 secrets.toml에 ADMIN_PASSWORD를 설정하는 것을 권장합니다.
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "1234") # 기본값 1234 (설정 필요)

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
    st.stop() # 인증 전에는 아래 코드 실행 중단

# =========================================================
# 로그인 성공 시 아래 내용 표시
# =========================================================

st.title("📊 학생 서술형 답안 대시보드")

# ── 4. 데이터 불러오기 및 가공 ──
@st.cache_data(ttl=60) # 60초마다 데이터 갱신 허용
def fetch_data():
    # created_at 기준 내림차순 정렬 (최신순)
    response = supabase.table("student_submissions").select("*").order("created_at", desc=True).execute()
    rows = response.data
    
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    
    # 시간대 변환 (UTC -> KST)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
        # DB에 저장된 시간이 UTC라고 가정하고 한국 시간으로 변환
        df["created_at"] = df["created_at"].dt.tz_convert("Asia/Seoul").dt.strftime("%Y-%m-%d %H:%M:%S")
        
    return df

# 새로고침 버튼
if st.button("🔄 데이터 새로고침"):
    fetch_data.clear() # 캐시 초기화
    st.rerun()

df = fetch_data()

# ── 5. 통계 및 메인 테이블 표시 ──
if df.empty:
    st.warning("아직 제출된 데이터가 없습니다.")
else:
    # (1) 요약 통계
    col1, col2 = st.columns(2)
    with col1:
        st.metric("총 제출 수", f"{len(df)}건")
    with col2:
        recent_student = df.iloc[0]['student_id']
        st.metric("최근 제출 학생", recent_student)

    st.markdown("---")

    # (2) 데이터 필터링 (학번 검색)
    search_query = st.text_input("🔍 학번 검색", placeholder="학번을 입력하세요 (모두 보려면 비워두세요)")
    
    if search_query:
        filtered_df = df[df['student_id'].str.contains(search_query)]
    else:
        filtered_df = df

    # (3) 메인 데이터프레임 (요약 보기용 컬럼만 선택)
    display_cols = ["student_id", "created_at", "answer_1", "feedback_1"] # 주요 컬럼만 미리보기
    st.subheader("📋 제출 현황 목록")
    st.dataframe(
        filtered_df, 
        use_container_width=True,
        column_config={
            "student_id": "학번",
            "created_at": "제출 시간",
            "answer_1": "Q1 답안 (요약)",
            "feedback_1": "Q1 피드백 (요약)"
        }
    )

    # (4) 엑셀 다운로드 버튼
    csv = filtered_df.to_csv(index=False).encode('utf-8-sig') # 한글 깨짐 방지
    st.download_button(
        label="📥 전체 데이터 CSV로 다운로드",
        data=csv,
        file_name="student_submissions.csv",
        mime="text/csv",
    )

    # ── 6. 상세 보기 (Expandable) ──
    st.markdown("---")
    st.subheader("📝 학생별 상세 답안 및 피드백 확인")
    
    # 선택박스로 학생 선택
    student_list = filtered_df['student_id'].unique()
    selected_student = st.selectbox("상세 내용을 확인할 학생을 선택하세요", student_list)

    if selected_student:
        # 해당 학생의 데이터 추출 (중복 제출 시 최신 것 1개만 가져오거나 리스트로 보여줌)
        # 여기서는 최신 1건만 보여주는 예시
        student_data = filtered_df[filtered_df['student_id'] == selected_student].iloc[0]

        with st.container(border=True):
            st.markdown(f"### 🧑‍🎓 학번: {student_data['student_id']}")
            st.caption(f"제출 시간: {student_data['created_at']}")
            
            # 문항별 탭 생성
            tab1, tab2, tab3 = st.tabs(["문제 1 (온도)", "문제 2 (보일)", "문제 3 (열이동)"])
            
            with tab1:
                st.markdown("**학생 답안:**")
                st.info(student_data.get("answer_1", "-"))
                st.markdown("**AI 피드백:**")
                # O/X에 따른 색상 구분
                fb = student_data.get("feedback_1", "")
                if fb.startswith("O:"):
                    st.success(fb)
                else:
                    st.warning(fb)

            with tab2:
                st.markdown("**학생 답안:**")
                st.info(student_data.get("answer_2", "-"))
                st.markdown("**AI 피드백:**")
                fb = student_data.get("feedback_2", "")
                if fb.startswith("O:"):
                    st.success(fb)
                else:
                    st.warning(fb)

            with tab3:
                st.markdown("**학생 답안:**")
                st.info(student_data.get("answer_3", "-"))
                st.markdown("**AI 피드백:**")
                fb = student_data.get("feedback_3", "")
                if fb.startswith("O:"):
                    st.success(fb)
                else:
                    st.warning(fb)
