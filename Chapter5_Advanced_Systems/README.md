# 제5장: 고급 에이전트 시스템: 다중 에이전트 협업과 UI

> [!NOTE]
> 이 장의 명령 예시는 OS에 따라 문법이 다른 경우 **Windows (PowerShell)** 와 **macOS / Linux (bash·zsh)** 블록으로 나눠 표기합니다. 본인이 사용하는 OS의 블록을 따라 실행하세요. `uv run ...`처럼 양쪽이 동일한 명령은 그대로 사용하면 됩니다.

## 5.1 이 장의 목표 (Learning Objectives)

지금까지 우리는 AI를 대화 상대로 만들고(1장), 자율적인 행동 주체(3장)를 거쳐, 마침내 특정 분야의 지식과 다양한 도구를 갖춘 개별 전문가 에이전트(4장)를 탄생시켰습니다. 하지만 현실 세계의 복잡한 비즈니스 문제는 한 명의 천재만으로는 해결할 수 없습니다. 연구원, 작가, 비평가, 프로젝트 관리자가 한 팀을 이루어야 위대한 결과물이 탄생하듯, AI도 마찬가지입니다.

이 장은 개별 AI 전문가들을 하나의 유기적인 팀으로 조직하고, 그 결과물을 사용자가 직접 만져볼 수 있는 Streamlit UI로 감싸는 방법을 다룹니다.

이 장을 성공적으로 마치면, 여러분은 다음 역량을 갖추게 됩니다.

- **AI 팀 설계 능력:** 복잡한 문제를 해결하기 위해, 각기 다른 역할과 전문성을 가진 여러 AI 에이전트가 협력하는 **'다중 에이전트 시스템(Multi-Agent System)'**의 개념을 이해하고 직접 설계할 수 있습니다.
- **API key 기반 협업 구성:** Responses API를 사용하여, '연구원', '작가', '검토자' 역할을 순차적으로 연결하는 협업 흐름을 코드로 구현할 수 있습니다.
- **협업 흐름 설계:** 실제 원격 agent 연결 대신, 역할별 prompt 호출을 순차적으로 연결하는 교육용 협업 흐름에 집중합니다.
- **프로덕션 배포 개념 이해:** '내 컴퓨터'에서만 작동하던 에이전트를 전 세계 누구나 접근할 수 있는 **'프로덕션(Production) 환경'**에 배포하는 것의 의미와 기술적 과제를 이해합니다.
- **웹 서비스화 능력:** 개발된 에이전트를 **Streamlit**과 같은 도구를 사용하여 간단한 **웹 애플리케이션(Web Application)**으로 패키징하고, 사용자가 직접 상호작용할 수 있는 UI를 제공할 수 있습니다.

## 5.2 개별 전문가를 넘어: 다중 에이전트 협업 패턴 (Multi-Agent Pattern)

"최신 AI 기술 트렌드에 대한 심층 분석 블로그 포스트를 작성하라"는 복잡한 목표가 주어졌다고 상상해 봅시다. 한 명의 에이전트가 이 모든 것을 완벽하게 해낼 수 있을까요? 다중 에이전트 패턴은 **'분업과 협업'**이라는 인간 사회의 가장 효율적인 문제 해결 방식을 AI 세계에 도입한 것입니다.

> **[Mental Model Shift]**
> 더 이상 당신은 한 명의 '만능 비서'를 고용하는 것이 아닙니다. 당신은 **'프로젝트 매니저(Project Manager)'**가 되어, 각 분야 최고의 전문가들로 구성된 **AI 어벤져스 팀**을 꾸리는 것입니다.
>
> - **연구원 (Researcher) 에이전트:** 최신 정보를 수집하고 분석하는 역할.
> - **작가 (Writer) 에이전트:** 연구원의 보고서를 바탕으로 매력적인 글을 작성하는 역할.
> - **비평가 (Critic) 에이전트:** 작가의 글을 검토하고 피드백하는 역할.

이 커리큘럼에서는 역할 기반의 다중 에이전트 시스템을 API key 기반 prompt-style agent 관점에서 설계합니다. 5장은 로컬 multi-agent 협업과 UI에 집중하고, 실제 Foundry Agent Service 기반 실행은 8장에서 다룹니다.

### 5.2.1 Hands-on: "AI 트렌드 분석" 블로그 포스트를 작성하는 AI 팀 구축하기

이 실습은 `5.2.1_multi_agent_system.py` 파일에 해당합니다. '선임 연구 분석가'와 '기술 콘텐츠 전략가'라는 두 역할을 API key 기반 Responses 호출로 연결하여, 2026년 AI 트렌드에 대한 블로그 포스트를 순차적으로 작성하게 만듭니다.

### 5.2.2 다음 단계: 실제 Foundry Agent Service로 확장하기

5장에는 원격 agent connector 실행 파일을 두지 않습니다. 파일명이 실제 Foundry connector를 암시하면서 내부는 prompt 호출만 수행하면 학습자가 혼동할 수 있기 때문입니다. 실제 Foundry Project SDK 기반 agent 생성, tool 연결, trace 분석은 8장에서 진행합니다.

## 5.3 실험실을 넘어 사용자 화면으로: Streamlit UI

지금까지 만든 에이전트는 개발자인 우리만 터미널에서 실행할 수 있는 실습형 프로토타입입니다. 5장에서는 이를 웹 브라우저에서 사용할 수 있는 Streamlit UI로 감싸, 사용자-facing 앱의 첫 형태를 만듭니다. 실제 프로덕션 운영 통제는 7장에서 trace, guardrails, human review 관점으로 다시 다룹니다.

> **[Key Concept]**
> UI를 붙이는 것은 프로덕션 배포의 시작점일 뿐입니다. 사용자 입력, 세션 상태, 인증, 보안, 관찰 가능성까지 함께 설계해야 실제 서비스가 됩니다.

Python 개발자가 가장 빠르고 쉽게 자신의 AI 에이전트를 웹 애플리케이션으로 만들 수 있는 **Streamlit**을 사용해 배포의 첫걸음을 떼어보겠습니다.

### 5.3.1 Hands-on: 나의 첫 AI 에이전트 웹 앱 배포하기

이 실습은 `5.3.1_streamlit_app.py` 파일에 해당합니다. 3장에서 만든 prompt-style agent 호출을 Streamlit UI로 감싸, 사용자가 직접 질문을 입력하고 답변을 볼 수 있는 `Prompt-style Agent Web App`을 만들어 봅니다. 이어서 `5.3.2_streamlit_chatbot_with_memory.py`에서 `Prompt-style Chatbot with Memory` 형태로 확장합니다.

Streamlit 파일도 `_bootstrap.py`를 통해 저장소 루트 import 경로를 잡으므로, 아래처럼 `uv run`으로 실행하면 같은 `.venv` 환경에서 `foundry_hands_on` 모듈을 찾습니다.

```bash
uv run streamlit run Chapter5_Advanced_Systems/5.3.1_streamlit_app.py
uv run streamlit run Chapter5_Advanced_Systems/5.3.2_streamlit_chatbot_with_memory.py
```

## 5.4 실행 결과를 볼 때 확인할 점

터미널 실습은 실행 시작 시 학습 목표 안내 블록을 출력합니다. Streamlit 실습은 웹 화면에서 입력과 답변을 확인하고, 터미널에서는 앱 실행 로그와 모델 호출 trace를 함께 확인합니다.

`5.2.1_multi_agent_system.py`는 실제 원격 agent registry가 아니라 여러 역할의 prompt 호출을 순차적으로 연결하는 예제입니다. 첫 번째 역할의 결과 문자열이 두 번째 역할의 입력에 포함되므로, “에이전트가 서로 대화한다”는 느낌은 코드가 이전 결과를 다음 prompt로 넘기는 방식에서 만들어집니다.

`5.3.2_streamlit_chatbot_with_memory.py`의 메모리는 Foundry Agent Service thread, 데이터베이스, 파일 저장소가 아니라 Streamlit의 `st.session_state.messages` 리스트를 사용합니다. `run_threaded_prompt()`는 이 리스트에 user/assistant 메시지를 계속 추가하고, 다음 질문을 보낼 때 누적된 대화 기록 전체를 다시 모델 입력으로 전달합니다. 그래서 앱 세션이 유지되는 동안에는 이전 대화를 기억하는 것처럼 동작하지만, 세션을 새로 시작하거나 앱을 재시작하면 메모리가 초기화됩니다.
