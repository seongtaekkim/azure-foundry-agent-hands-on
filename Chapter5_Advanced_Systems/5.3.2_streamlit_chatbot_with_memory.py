# Run: uv run streamlit run Chapter5_Advanced_Systems/5.3.2_streamlit_chatbot_with_memory.py
# 학습 포인트: Streamlit session_state로 챗봇 대화 메모리를 유지합니다.
# 초보자 읽기: st.session_state.messages에 대화가 쌓이면서 웹 챗봇이 이전 질문과 답변을 화면에 유지하는 방식을 봅니다.
import streamlit as st
from dotenv import load_dotenv

import _bootstrap  # noqa: F401
from foundry_hands_on import run_threaded_prompt

load_dotenv()

# Streamlit 앱은 반드시 `streamlit run`으로 띄워야 합니다. `uv run <파일>`처럼 직접 실행하면
# Streamlit 런타임이 없어 session_state/위젯이 동작하지 않고 ScriptRunContext 경고만 반복됩니다.
# 그 경우 올바른 명령을 안내하고 깔끔하게 종료합니다.
if not st.runtime.exists():
    print(
        "\n[실행 방법 안내] 이 파일은 Streamlit 앱입니다. `uv run <파일>`로 직접 실행하면 동작하지 않습니다.\n"
        "다음 명령으로 실행하세요:\n"
        "  uv run streamlit run Chapter5_Advanced_Systems/5.3.2_streamlit_chatbot_with_memory.py"
    )
    raise SystemExit(1)

st.set_page_config(page_title="Prompt-style Chatbot with Memory", layout="wide")
st.title("Prompt-style Chatbot with Memory")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": "You are a Microsoft Foundry hands-on assistant. Answer in Korean and remember the conversation.",
        }
    ]

for message in st.session_state.messages:
    if message["role"] in {"user", "assistant"}:
        with st.chat_message(message["role"]):
            st.write(message["content"])

if prompt := st.chat_input("prompt-style agent에게 질문하세요"):
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        answer = run_threaded_prompt(
            st.session_state.messages,
            prompt,
            scenario_name="chapter5.streamlit.memory",
        )
        st.write(answer)
