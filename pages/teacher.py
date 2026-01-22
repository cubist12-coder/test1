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
        q_stats = pd.DataFrame({
            "문항": ["문제 1 (온도)", "문제 2 (보일)", "문제 3 (열이동)"],
            "정답률": [df["Q1_정답"].mean(), df["Q2_정답"].mean(), df["Q3_정답"].mean()]
        })
        
        bar_chart = alt.Chart(q_stats).mark_bar().encode(
            x=alt.X("문항", sort=None),
            y=alt.Y("정답률", axis=alt.Axis(format='%', title='정답률')),
            color=alt.Color("문항", legend=None),
            tooltip=[alt.Tooltip("문항"), alt.Tooltip("정답률", format=".1%")]
        ).properties(height=300)
        
        st.altair_chart(bar_chart, use_container_width=True)

    with chart_col2:
        st.subheader("🏆 학생 점수 분포")
        score_counts = df["총점"].value_counts().reset_index()
        score_counts.columns = ["점수", "학생수"]
        
        pie_chart = alt.Chart(score_counts).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="학생수", type="quantitative"),
            color=alt.Color(field="점수", type="nominal", legend=alt.Legend(title="맞춘 개수")),
            tooltip=["점수", "학생수"]
        ).properties(height=300)
        
        st.altair_chart(pie_chart, use_container_width=True)
    
    # 분석 멘트
    min_idx = q_stats['정답률'].idxmin()
    hardest_q = q_stats.loc[min_idx, '문항']
    hardest_val = q_stats.loc[min_idx, '정답률'] * 100
    
    st.info(f"💡 분석: 학생들이 가장 어려워한 문제는 **'{hardest_q}'** 입니다. (정답률: {hardest_val:.1f}%)")

    st.markdown("---")

    # [하단] 상세 데이터 테이블
    st.subheader("📋 상세 제출 현황")
    
    search_query = st.text_input("🔍 학번 검색", placeholder="학번 입력")
    if search_query:
        filtered_df = df[df['student_id'].str.contains(search_query, na=False)]
    else:
        filtered_df = df

    # 표시용 데이터프레임 생성
    display_df = filtered_df.copy()
    for col in ["Q1_정답", "Q2_정답", "Q3_정답"]:
        display_df[col] = display_df[col].apply(lambda x: "✅" if x == 1 else "❌")

    st.dataframe(
        display_df, 
        use_container_width=True,
        column_order=["student_id", "created_at", "Q1_정답", "Q2_정답", "Q3_정답", "총점"],
        column_config={
            "student_id": "학번",
            "created_at": "제출 시간",
            "Q1_정답": "문제 1",
            "Q2_정답": "문제 2",
            "Q3_정답": "문제 3",
            "총점": "점수"
        }
    )

    # 엑셀 다운로드
    csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 전체 데이터(분석 포함) CSV 다운로드",
        data=csv,
        file_name="student_analysis.csv",
        mime="text/csv",
    )

    # ── 6. 개별 상세 보기 ──
    with st.expander("🔎 학생별 피드백 상세 보기"):
        student_list = filtered_df['student_id'].unique()
        if len(student_list) > 0:
            selected_student_detail = st.selectbox("학생 선택", student_list)
            if selected_student_detail:
                # 선택한 학생 데이터 필터링
                student_rows = filtered_df[filtered_df['student_id'] == selected_student_detail]
                if not student_rows.empty:
                    student_data = student_rows.iloc[0]
                    st.markdown(f"### 🧑‍🎓 {student_data['student_id']} 학생 상세 결과")
                    
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.caption("문제 1 (온도)")
                        st.write(student_data.get("feedback_1", "-"))
                    with c2:
                        st.caption("문제 2 (보일)")
                        st.write(student_data.get("feedback_2", "-"))
                    with c3:
                        st.caption("문제 3 (열이동)")
                        st.write(student_data.get("feedback_3", "-"))
        else:
            st.write("표시할 학생 데이터가 없습니다.")
