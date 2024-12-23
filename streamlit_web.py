import streamlit as st
import requests
from datetime import datetime
import plotly.graph_objects as go
from openai import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta

# FastAPI에서 데이터를 가져오는 함수
def fetch_sensor_data():
    """고정된 센서 데이터를 반환"""
    try:
        # 현재 시간
        now = datetime.now()

        # 고정된 데이터 생성
        history = [
            {
                "timestamp": (now - timedelta(seconds=i * 2)).strftime("%Y-%m-%d %H:%M:%S"),
                "temperature": 21,  # 고정 온도
                "humidity": 29      # 고정 습도
            }
            for i in range(10)  # 10개의 데이터 생성
        ]

        # 최신 데이터 설정
        latest = history[0]

        # 고정된 센서 데이터 반환
        return {
            "latest": latest,
            "history": history
        }

    except Exception as e:
        st.error(f"Error generating mock data: {e}")
        return None


# 그래프 생성 함수
def generate_graph(history):
    """히스토리 데이터를 사용하여 그래프 생성"""
    if not history:
        return None

    # 시간, 온도, 습도 데이터를 분리
    timestamps = [data["timestamp"] for data in history]
    temperatures = [data["temperature"] for data in history]
    humidities = [data["humidity"] for data in history]

    # Plotly 그래프 생성
    fig = go.Figure()

    # 온도 데이터 추가
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=temperatures,
        mode='lines+markers',
        name='Temperature (°C)',
        line=dict(color='firebrick', width=2)
    ))

    # 습도 데이터 추가
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=humidities,
        mode='lines+markers',
        name='Humidity (%)',
        line=dict(color='royalblue', width=2)
    ))

    # 레이아웃 설정
    fig.update_layout(
        title="온도 및 습도 변화 추이",
        xaxis_title="시간",
        yaxis_title="값",
        xaxis=dict(tickangle=0),  # 시간 텍스트를 수평으로 설정
        legend=dict(orientation="h", xanchor="center", x=0.5, y=-0.2),
        margin=dict(l=40, r=40, t=60, b=80),
        template="plotly_white"
    )

    return fig

# Streamlit 애플리케이션
def main():
    st.title("스마트농업프로그래밍 기말 프로젝트")
    menu = st.sidebar.selectbox("메뉴 선택", ["홈", "음성대화 로그 보기", "챗봇"])
    # 현재 시간 표시
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if menu == "홈":
        # 1초마다 새로고침 (1000ms = 1초)
        st_autorefresh(interval=1000, key="home_page_refresh")

        st.write("### 온도 및 습도 데이터 확인")

        # FastAPI에서 데이터 가져오기
        sensor_data = fetch_sensor_data()

        if sensor_data:
            latest = sensor_data.get("latest", {})
            temperature = latest.get("temperature", "N/A")
            humidity = latest.get("humidity", "N/A")
            update_time = latest.get("timestamp", "N/A")

            col1, col2 = st.columns(2)

            # 각 컬럼에 데이터 배치
            with col1:
                st.metric(label="온도 (°C)", value=temperature)

            with col2:
                st.metric(label="습도 (%)", value=humidity)
            # st.write(f"데이터 업데이트 시간: {update_time}")
            st.write(f"현재 시간: {current_time}")

            history = sensor_data.get("history", [])

            # 그래프 표시
            graph_fig = generate_graph(history)
            if graph_fig:
                st.plotly_chart(graph_fig, use_container_width=True)

        else:
            st.warning("센서 데이터를 가져오는 데 실패했습니다.")


    elif menu == "음성대화 로그 보기":
        API_URL = "http://113.198.63.27:10150/log"

        # 페이지 제목
        st.title("음성대화 로그 뷰어")

        # FastAPI로부터 데이터 가져오기
        # 날짜 선택 위젯
        selected_date = st.date_input("날짜를 선택하세요:", value=datetime.now().date())

        # FastAPI에서 데이터 가져오는 함수
        def fetch_logs_for_date(date):
            formatted_date = date.strftime("%Y%m%d")  # 선택된 날짜를 YYYYMMDD 형식으로 변환
            params = {"date": formatted_date}  # API 요청 파라미터
            try:
                response = requests.get(API_URL, params=params)
                response.raise_for_status()  # 요청이 실패하면 예외 발생
                return response.json()
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to fetch logs: {e}")
                return {}

        # "조회하기" 버튼
        if st.button("조회하기"):
            logs = fetch_logs_for_date(selected_date)
            if logs:
                # 파일명을 기준으로 정렬 (가장 오래된 것부터)
                sorted_logs = sorted(logs.items(), key=lambda x: x[0])  # x[0]은 파일명

                for file_name, log_content in sorted_logs:
                    if log_content:  # 로그 내용이 비어있지 않은 경우만 처리
                        try:
                            log_data = eval(log_content)  # JSON 문자열을 파싱
                            timestamp = log_data.get("timestamp", "Unknown Timestamp")

                            # 시간만 추출 (HH:MM:SS)
                            if timestamp != "Unknown Timestamp":
                                time_only = timestamp.split("_")[1]  # "YYYYMMDD_HHMMSS"에서 HHMMSS 추출
                                formatted_time = f"{time_only[:2]}:{time_only[2:4]}:{time_only[4:]}"  # HH:MM:SS 형식으로 변환
                            else:
                                formatted_time = "Unknown Time"

                            user_question = log_data.get("user_question", "").strip()
                            gpt_response = log_data.get("gpt_response", "").strip()

                            # 사용자 메시지 (왼쪽)
                            st.chat_message("user").markdown(f"**[{formatted_time}]** {user_question}")

                            # GPT 응답 메시지 (오른쪽)
                            st.chat_message("assistant").markdown(f"**[{formatted_time}]** {gpt_response}")

                        except Exception as e:
                            st.warning(f"Error parsing log file {file_name}: {e}")
            else:
                st.info(f"{selected_date.strftime('%Y-%m-%d')}에 해당하는 로그 파일이 없습니다.")


    elif menu == "챗봇":
        st.title("Agricultural Chat Assistant")
        OPENAI_API_KEY = st.secrets["openai"]["api_key"]
      
        chat_model = ChatOpenAI(api_key=OPENAI_API_KEY, model_name="gpt-4o", temperature=0.8)

        # 시스템 프롬프트 설정
        system_prompt = """
         Your name is 'Famia'. The following is a friendly and professional conversation between a human and an AI.
         The AI is an expert agricultural assistant with years of experience in smart farming, crop management, and agricultural technology.
         The AI is talking to a user who needs help with agriculture-related questions or tasks.
         The AI provides clear and practical advice, focusing on smart agriculture solutions, crop health, pest management, and data-driven decision-making.

         The AI should feel free to suggest better farming practices, smart technology integration, or other useful approaches whenever needed.
         When giving advice or suggestions, the AI must start with "It might be better to consider this approach:"
         But even when suggesting improvements, the AI should engage in a friendly and helpful conversation to address the user's immediate question first.
         """

        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "system", "content": "안녕하세요! 저는 스마트 농업과 작물 관리에 전문성을 가진 AI 챗봇 '파미아'입니다. 효율적인 농업 기술과 데이터 기반 솔루션으로 여러분의 농업 고민을 해결해드립니다!"}  # 시스템 프롬프트 추가
            ]

        # 이전 메시지 표시
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # 사용자 입력 처리
        if prompt := st.chat_input("Ask me anything about agriculture..."):
            # 사용자 메시지 추가
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)


            # AI 응답 생성
            with st.chat_message("assistant"):
                response = chat_model(
                    messages=[
                        SystemMessage(content=system_prompt),
                        *[
                            HumanMessage(content=msg["content"])
                            if msg["role"] == "user"
                            else SystemMessage(content=msg["content"])
                            for msg in st.session_state.messages[1:]
                        ]
                    ]
                )
                st.session_state.messages.append({"role": "assistant", "content": response.content})
                st.markdown(response.content)

if __name__ == "__main__":
    main()
