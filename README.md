# test1
🧪 AI 기반 과학 서술형 평가 시스템이 프로젝트는 Streamlit을 활용하여 학생들의 서술형 답안을 수집하고, OpenAI GPT 모델을 통해 실시간으로 채점 및 피드백을 제공하며, 그 결과를 Supabase 데이터베이스에 영구 저장하는 교육용 웹 애플리케이션입니다.📊 시스템 흐름도 (System Workflow)사용자(학생)가 답안을 제출하면 시스템 내부에서 어떤 처리가 일어나는지 보여주는 구조입니다.graph TD
    User([학생 / 사용자]) -->|1. 학번 & 답안 입력| UI[Streamlit 웹 인터페이스]
    
    subgraph "Step 1: 제출 & 검증"
        UI -->|제출 버튼 클릭| Validate{입력값 검증}
        Validate -- 실패 --> Alert[경고 메시지 출력]
        Validate -- 성공 --> Session[세션 상태 저장]
    end

    subgraph "Step 2: AI 채점 & 저장"
        Session -->|2. 피드백 요청| GPT{OpenAI API}
        GPT -->|3. O/X 및 피드백 생성| Logic[결과 처리 로직]
        Logic -->|4. 데이터 저장| DB[(Supabase Cloud DB)]
    end

    DB -->|저장 완료| UI
    Logic -->|5. 피드백 화면 표시| User
🛠️ 주요 기능서술형 문제 인터페이스 (Step 1-2)학번 입력 및 3가지 과학 서술형 문항 제공기체 운동, 보일 법칙, 열에너지 이동 방식에 대한 텍스트 입력 폼필수 입력값 검증 (학번 및 공란 체크)AI 자동 채점 및 피드백 (Step 2)OpenAI API를 연동하여 교사가 설정한 GRADING_GUIDELINES에 맞춰 채점단순 점수가 아닌, "O/X 판정 + 구체적인 피드백" 제공출력 형식 정규화 기능 포함 (200자 이내 요약)클라우드 데이터 저장 (Supabase)채점 결과와 학생의 답안을 Supabase 테이블에 실시간 저장student_submissions 테이블에 학번, 답안, 피드백, 채점 기준 등을 모두 기록⚙️ 설치 및 설정 (Setup)1. 라이브러리 설치프로젝트 실행을 위해 requirements.txt에 다음 패키지들이 필요합니다.pip install streamlit openai supabase
2. 비밀 키 설정 (secrets.toml)프로젝트 루트의 .streamlit/secrets.toml 파일에 API 키를 설정해야 합니다.(주의: 이 파일은 절대 GitHub 등에 공개하면 안 됩니다.)# .streamlit/secrets.toml

OPENAI_API_KEY = "sk-..."

SUPABASE_URL = "[https://your-project.supabase.co](https://your-project.supabase.co)"
SUPABASE_SERVICE_ROLE_KEY = "eyJhb..."
📝 코드 상세 설명🔹 Step 1: UI 및 제출 처리st.form: 입력 지연을 방지하기 위해 3개의 문항을 하나의 폼으로 묶어서 처리합니다.상태 관리: st.session_state를 사용하여 제출 상태(submitted_ok)를 관리, 새로고침 시에도 로직이 유지되도록 합니다.🔹 Step 2: AI 채점 (GPT)프롬프트 엔지니어링: 교사 페르소나를 부여하고, 출력 형식을 O: ... 또는 X: ...로 엄격하게 제한하여 데이터의 일관성을 확보합니다.후처리 함수 (normalize_feedback): AI 응답이 형식을 벗어날 경우를 대비해 강제로 포맷을 맞춰주는 안전 장치가 포함되어 있습니다.🔹 Database: Supabase 연동get_supabase_client: 리소스 캐싱(@st.cache_resource)을 통해 DB 연결 효율을 높입니다.save_to_supabase: 학생의 ID, 답안(Q1~Q3), 피드백, 사용 모델 정보를 JSON 형태로 구조화하여 DB에 Insert 합니다.🚀 실행 방법터미널에서 다음 명령어를 실행하여 웹 앱을 시작합니다.streamlit run app.py
브라우저가 열리면 학번과 답안을 입력하고 **[제출]
