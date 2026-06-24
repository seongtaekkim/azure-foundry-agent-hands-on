# Microsoft Foundry Agent Hands-on 사전 학습 가이드

> 대상: 생성형 AI와 에이전트를 처음 배우는 사람  
> 목적: 코드를 실행하기 전에 이 저장소가 무엇을 가르치는지, 각 기술이 왜 필요한지 이해하기  
> 기준 저장소: `azure-foundry-agent-hands-on-cost-review`

## 1. 이 자료를 먼저 읽어야 하는 이유

이 저장소는 단순히 챗봇 하나를 만드는 예제가 아니다. 하나의 사내 정책 Q&A 프로그램을 다음 순서로 발전시키면서, AI 애플리케이션이 실제 서비스에 가까워지는 과정을 보여준다.

```text
모델에 질문
  -> 역할과 대화 기록 추가
  -> 에이전트 형태로 구성
  -> 계산기와 사내 문서 검색 연결
  -> 여러 역할이 협업
  -> 웹 화면 제공
  -> 기능을 HTTP 도구 서버로 분리
  -> 안전장치와 추적 추가
  -> Microsoft Foundry Agent Service에 실제 agent 등록
```

이 흐름에서 가장 중요한 사실은 다음과 같다.

> AI 에이전트는 특별한 지능 하나를 새로 만드는 것이 아니다. 모델 호출을 중심으로 상태, 도구, 검색, 실행 순서, 안전장치, 관찰 기능을 소프트웨어로 조립한 시스템이다.

## 2. 전체 구조를 한 장으로 이해하기

```text
사용자
  |
  v
웹 UI 또는 Python 프로그램
  |
  +--> Guardrail: 이 요청을 처리해도 되는가?
  |
  +--> Agent/Orchestrator: 어떤 작업과 도구가 필요한가?
          |
          +--> LLM: 문장을 이해하고 답변을 생성
          +--> RAG: 관련 사내 문서를 검색
          +--> Tool: 계산기, API, MCP 서버 등을 호출
          +--> State: 이전 대화와 중간 결과를 보관
          +--> Human review: 위험한 결정을 사람이 승인
  |
  v
최종 답변
  |
  +--> Trace/Monitoring: 실행 과정, 오류, 시간, 토큰 사용량 기록
```

저장소의 장별 역할은 다음과 같다.

| 장 | 핵심 질문 | 배우는 내용 |
| --- | --- | --- |
| 1장 | 모델과 어떻게 대화하는가? | Responses API, prompt, token, multi-turn |
| 2장 | 반복되는 연결 코드를 어떻게 정리하는가? | `.env`, 공통 client, tracing |
| 3장 | 챗봇과 에이전트는 무엇이 다른가? | 역할, 상태, Sense-Think-Act |
| 4장 | 모델이 모르는 정보와 계산은 어떻게 보완하는가? | Tool use, embedding, RAG, routing |
| 5장 | 복잡한 일을 어떻게 분업하고 사용자에게 보여주는가? | Multi-agent, Streamlit UI |
| 6장 | 기능을 다른 프로그램도 쓰게 하려면? | HTTP 서버, session, MCP 스타일 도구 |
| 7장 | 잘못된 답변과 위험한 행동은 어떻게 통제하는가? | HITL, reflection, guardrails |
| 8장 | 로컬 시연을 실제 관리형 agent로 어떻게 옮기는가? | Agent Service, AI Search, Knowledge Base, MCPTool, monitoring |

---

## 3. 먼저 알아야 할 핵심 용어

### 3.1 생성형 AI와 LLM

생성형 AI는 입력을 바탕으로 새로운 텍스트, 코드, 이미지 등을 만든다. 이 실습에서 사용하는 LLM은 입력된 문맥을 토대로 다음에 올 토큰을 예측하면서 답변을 생성한다.

LLM은 데이터베이스처럼 사실을 정확히 조회하는 장치가 아니다. 자연스러운 문장을 잘 만들지만, 모르는 내용도 그럴듯하게 말할 수 있다. 이것이 환각(hallucination)이다.

### 3.2 토큰

토큰은 모델이 텍스트를 읽고 쓰는 단위다. 단어와 정확히 일치하지 않으며, 한 단어가 여러 토큰으로 나뉠 수도 있다.

- 입력 토큰: system prompt, 질문, 이전 대화, 검색 문서 등 모델에 보낸 내용
- 출력 토큰: 모델이 생성한 답변과 모델에 따라 청구되는 reasoning token
- 비용과 최대 문맥 길이는 토큰 수를 기준으로 계산된다.

대화 기록을 계속 전송하면 모델이 기억하는 것처럼 보이지만, 호출할 때마다 이전 기록을 다시 보내므로 입력 토큰과 비용도 증가한다.

### 3.3 Prompt

Prompt는 모델에 전달하는 지시와 데이터 전체다.

- system prompt: 역할, 규칙, 금지 사항, 출력 형식
- user prompt: 사용자의 질문이나 작업 요청
- assistant message: 이전 모델 응답

좋은 prompt는 단순히 문장을 예쁘게 쓰는 기술이 아니다. 목표, 사용할 근거, 제약 조건, 실패 시 행동, 출력 형식을 명확히 정의하는 인터페이스 설계다.

### 3.4 Endpoint, API key, 모델 배포명

- endpoint: 요청을 보낼 Azure 서비스 주소
- API key: 해당 서비스를 호출할 권한을 증명하는 비밀 값
- 모델 배포명: Azure 프로젝트 안에 배포된 모델을 가리키는 이름

모델 이름이 `gpt-5.2`라고 해서 배포명도 반드시 같은 것은 아니다. 코드에는 Azure에 실제로 만든 배포명을 전달해야 한다.

API key는 코드나 Git에 올리면 안 된다. 이 저장소는 `.env`에 저장하고 `.env.example`에는 변수 이름과 자리표시자만 둔다.

### 3.5 Responses API

Responses API는 모델에 입력을 보내고 응답을 받는 호출 방식이다. 이 저장소에서는 1~7장의 거의 모든 지능형 동작이 결국 `openai.responses.create(...)` 호출로 내려간다.

에이전트, RAG, reflection도 가장 아래에서는 모델 호출이다. 차이는 호출 전후에 어떤 데이터와 실행 절차를 붙이는가에 있다.

### 3.6 Embedding과 vector

Embedding은 텍스트의 의미를 숫자 배열(vector)로 표현한 것이다. 의미가 비슷한 문장은 벡터 공간에서도 가까워지는 경향이 있다.

예를 들어 “연차는 며칠인가요?”라는 질문 벡터와 “정규 직원은 연 15일의 연차를 사용할 수 있다”라는 문서 조각의 벡터는 비교적 가까워진다. 이 거리를 이용해 관련 문서를 찾는다.

Embedding 모델은 답변을 작성하지 않는다. 텍스트를 검색 가능한 숫자 표현으로 바꾸는 역할을 한다.

### 3.7 RAG

RAG는 Retrieval-Augmented Generation의 약자다. 모델이 답변하기 전에 외부 문서에서 관련 내용을 검색하고, 검색 결과를 prompt에 넣은 뒤 답하게 한다.

```text
문서 준비: Load -> Split -> Embed -> Store
질문 처리: Query -> Embed -> Retrieve -> Augment -> Generate
```

RAG는 모델을 다시 학습시키는 fine-tuning이 아니다. 질문할 때 참고자료를 찾아 함께 제공하는 방식이다.

### 3.8 Tool

Tool은 모델 밖에서 실제 작업을 수행하는 기능이다.

- 계산기 함수
- 사내 문서 검색
- 날씨 API
- 데이터베이스 조회
- MCP 서버의 문서 검색 기능

모델은 어떤 도구가 필요한지 판단하거나 도구의 입력을 만들 수 있다. 실제 실행과 권한 통제는 애플리케이션 또는 Agent Service가 담당한다.

### 3.9 Agent

에이전트는 목표를 받고, 필요한 정보를 확인하고, 계획을 세우고, 도구를 사용해 결과를 만드는 프로그램이다.

```text
Sense: 사용자 요청과 현재 상태를 읽는다.
Think: 다음 작업과 사용할 도구를 결정한다.
Act: 도구를 호출하거나 답변을 생성한다.
```

이 저장소에서 반드시 구분해야 할 두 종류가 있다.

| 구분 | 1~7장의 prompt-style agent | 8장의 Foundry Agent Service agent |
| --- | --- | --- |
| 실체 | 역할 prompt를 사용한 일반 Responses API 호출 | Foundry 프로젝트에 등록된 실제 agent version |
| 실행 제어 | 로컬 Python 코드 | Foundry Agent Service와 Python 코드 |
| 도구 | 로컬 함수와 교육용 라우팅 | Azure AI Search, Knowledge Base, MCPTool |
| 수명 | 프로그램 실행 동안 | 프로젝트에 생성되며 삭제 전까지 확인 가능 |

Prompt에 “너는 연구원이다”라고 쓰는 것만으로 완전한 자율 에이전트가 되는 것은 아니다.

### 3.10 State와 memory

State는 현재 작업을 계속하기 위해 보관하는 정보다. 이 저장소의 대부분의 memory는 영구 저장소가 아니다.

- 1장과 3장: Python의 `messages` 리스트
- 5장: `st.session_state.messages`
- 6장: 서버 프로세스 메모리의 session별 메시지
- 8장: 필요하면 Foundry conversation ID 사용

프로그램이나 서버를 종료하면 로컬 메모리는 사라진다. 실제 서비스에서는 DB, 캐시, 만료 정책, 사용자별 격리, 개인정보 삭제 정책이 필요하다.

### 3.11 Trace와 monitoring

- log: 특정 시점에 기록한 텍스트
- trace: 한 요청이 여러 단계를 지나간 전체 경로
- span: trace 안의 개별 작업 구간
- metric: 호출 수, 지연 시간, 토큰 사용량처럼 집계 가능한 수치

이 저장소는 OpenTelemetry span을 사용한다. Application Insights 연결 문자열이 없으면 콘솔에 출력하고, 있으면 Azure Monitor로 보낸다.

### 3.12 MCP

MCP(Model Context Protocol)는 모델이나 에이전트가 외부 도구와 정해진 방식으로 연결되도록 하는 프로토콜이다. 서로 다른 에이전트와 도구가 매번 전용 연결 코드를 만들지 않도록 공통 규약을 제공한다.

6장은 MCP 표준 전체를 구현한 서버가 아니라, HTTP endpoint와 JSON 요청/응답으로 “기능을 별도 도구 서버로 분리하는 감각”을 익히는 MCP 스타일 예제다. 실제 `MCPTool` 연결은 8장에서 다룬다.

---

## 4. 저장소의 공통 실행 구조

### 4.1 환경 구성

`pyproject.toml`은 필요한 Python 패키지를 선언하고, `uv.lock`은 정확한 패키지 버전 조합을 고정한다. `.python-version`은 Python 3.11.9를 지정한다.

`uv sync`를 실행하면 다음이 준비된다.

1. Python 3.11.9 확인 또는 설치
2. `.venv` 가상 환경 생성
3. lockfile에 맞는 패키지 설치

가상 환경은 이 프로젝트만을 위한 독립적인 Python 실행 공간이다. 다른 프로젝트의 패키지 버전과 충돌하는 것을 줄여준다.

### 4.2 `.env`의 핵심 값

1~7장의 최소 설정은 다음과 같다.

```dotenv
FOUNDRY_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
FOUNDRY_API_KEY=<secret>
FOUNDRY_OPENAI_API_VERSION=2025-04-01-preview
FOUNDRY_OPENAI_ENDPOINT_TYPE=azure_openai
FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-5.2
FOUNDRY_EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-small
FOUNDRY_REASONING_EFFORT=low
```

8장에서는 project endpoint, Azure AI Search, Knowledge Base, Application Insights 설정이 추가된다.

### 4.3 `foundry_hands_on` 패키지

| 파일 | 역할 |
| --- | --- |
| `config.py` | 환경 변수를 읽고 설정 객체 생성 |
| `client.py` | OpenAI 호환 client 생성, Responses API 호출, 대화 메시지 변환 |
| `agents.py` | prompt-style agent 실행 |
| `rag.py` | chunk, embedding, cosine similarity, RAG 답변 |
| `tracing.py` | OpenTelemetry 설정과 span 생성 |
| `learning.py` | 각 파일의 학습 목표 안내 출력 |

`_bootstrap.py`는 각 장의 스크립트가 저장소 루트의 `foundry_hands_on`을 import할 수 있도록 경로를 추가한다.

### 4.4 일반 모델 호출의 실제 흐름

```text
실습 스크립트
  -> run_single_turn_prompt()
  -> run_chat_prompt()
  -> get_settings()
  -> get_openai_client()
  -> openai.responses.create()
  -> 응답 텍스트와 token usage 출력
```

설정된 모델이 reasoning 옵션을 지원하지 않으면 공통 client는 reasoning 값을 제거하고 한 번 재시도한다.

### 4.5 보안상 반드시 알아둘 점

현재 `config.py`는 교육장이나 회사 프록시 환경을 고려해 `FOUNDRY_DISABLE_SSL_VERIFY`의 기본값을 `true`로 두고 있다. 이는 TLS 인증서 검증을 끄므로 중간자 공격을 탐지하지 못할 수 있다.

실제 서비스에서는 다음 원칙을 지켜야 한다.

```dotenv
FOUNDRY_DISABLE_SSL_VERIFY=false
```

회사 프록시가 있다면 검증을 끄기보다 회사 Root CA를 신뢰 저장소 또는 `REQUESTS_CA_BUNDLE`에 올바르게 등록하는 것이 원칙이다.

---

## 5. 장별 내용 해설

### 5.1 1장: 모델 호출과 Prompt

#### 무엇을 배우는가

첫 번째 목표는 Python이 Azure의 모델 endpoint로 요청을 보내고 텍스트 응답을 받는 전체 왕복을 이해하는 것이다.

필수 파일은 다음 두 개다.

- `1.5_first_openai_call.py`: system/user prompt로 첫 요청
- `1.6.4.4_mulit_turn.py`: 이전 대화를 다음 요청에 다시 포함

선택 파일에서는 역할 부여, few-shot, 분류, 출력 형식 제어, 창의적 생성 등을 다룬다.

#### Multi-turn의 진짜 동작

모델이 서버 안에서 자연스럽게 모든 대화를 기억하는 것이 아니다. 코드가 다음과 같은 리스트를 유지한다.

```python
messages = [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "첫 질문"},
    {"role": "assistant", "content": "첫 답변"},
    {"role": "user", "content": "후속 질문"},
]
```

두 번째 호출에서 이 리스트 전체를 다시 전송한다. 따라서 문맥이 길어질수록 비용, 지연 시간, 최대 context 제한을 고려해야 한다.

#### 기억해야 할 것

- Prompt는 모델의 행동을 유도하지만 사실성을 보장하지 않는다.
- Few-shot은 모델을 재학습시키는 것이 아니라 호출 시 예시를 제공하는 것이다.
- 단계적 답변을 요청하는 것과 모델의 비공개 내부 사고를 열람하는 것은 다르다.

### 5.2 2장: 공통 실행 기반과 Trace

여러 파일에서 endpoint와 API key 처리 코드를 반복하면 설정 누락과 버그가 늘어난다. 2장은 반복 기능을 공통 패키지로 모은다.

#### 세 개의 확인 단계

1. `2.1_check_foundry_settings.py`: 필요한 환경 변수가 있는지 확인
2. `2.2_foundry_responses_smoke_test.py`: 최소 모델 호출이 되는지 확인
3. `2.3_foundry_tracing_smoke_test.py`: trace가 콘솔 또는 Azure Monitor에 기록되는지 확인

Smoke test는 복잡한 기능을 시험하기 전에 기반 연결이 정상인지 빠르게 확인하는 작은 테스트다.

Trace는 답변의 내용만 보는 것이 아니라 “어느 단계에서 실패했는가, 얼마나 걸렸는가”를 분석하게 해준다. 운영 환경에서는 응답 본문에 개인정보나 비밀 값이 있을 수 있으므로 trace에 prompt와 응답 원문을 기록할 때 주의해야 한다. 저장소의 본문 기록 기본값은 꺼져 있다.

### 5.3 3장: Chatbot에서 Agent로

3장은 역할 지시문을 사용한 prompt-style agent를 만든다.

- `3.4.2_agent_app.py`: 역할을 가진 기본 agent
- `3.4.4_agent_with_calculator.py`: 계산기 같은 외부 도구가 필요한 이유
- `3.4.5_stateful_agent.py`: `messages` 리스트로 대화 상태 유지

실시간 날씨를 묻는 예제의 핵심은 답을 맞히는 것이 아니다. 모델 자체에는 현재 날씨를 확인할 능력이 없으므로 실시간 API 도구가 필요하다는 한계를 발견하는 것이다.

에이전트 프레임워크가 주로 해결하는 문제는 다음과 같다.

- 상태 관리
- 도구 정의와 호출
- 여러 단계의 실행 순서
- 실패 시 재시도와 대안 선택
- 관찰 가능성과 중단/재개

이 장의 예제는 역할과 상태 개념을 보여주는 입문 단계다. 실제 등록형 agent는 8장에서 생성한다.

### 5.4 4장: Tool Use와 RAG

#### Tool Use

언어 모델은 문장 생성에는 강하지만 정확한 산술, 최신 데이터 조회, 권한이 필요한 업무 수행에는 외부 도구가 더 적합하다.

`4.2.1_multi_tool_agent.py`는 로컬 계산기와 정책 조회 결과를 모델이 종합하게 한다. 실제 서비스에서는 도구마다 입력 schema, timeout, 재시도, 권한, 감사 기록이 필요하다.

#### 로컬 RAG의 동작

`foundry_hands_on/rag.py`와 `4.3.2_rag_agent.py`는 다음 과정을 구현한다.

1. `company_policy.txt`를 읽는다.
2. 문서를 겹치는 작은 chunk로 나눈다.
3. 질문과 모든 chunk를 embedding한다.
4. cosine similarity로 질문과 가까운 chunk를 정렬한다.
5. 상위 chunk를 context로 모델에 제공한다.
6. 모델에게 context 밖의 내용은 추측하지 말라고 지시한다.

Chunk가 너무 크면 불필요한 내용이 많이 들어가고, 너무 작으면 하나의 의미가 잘릴 수 있다. overlap은 chunk 경계에서 내용이 끊기는 문제를 줄인다.

Cosine similarity는 두 벡터의 방향이 얼마나 비슷한지 측정한다. 값이 높을수록 의미가 유사하다고 해석한다.

#### PDF와 문서 이해

`4.3.3_advanced_rag_mistral.py`는 PDF에서 텍스트를 추출해 구조화 context로 만드는 예다. 복잡한 표, 이미지, 레이아웃은 단순 PDF 텍스트 추출만으로 손실될 수 있다. 실제 환경에서는 OCR이나 Document Intelligence 같은 문서 이해 단계가 필요할 수 있다.

#### Agentic router

`4.4.4.6_multi_tool_agent.py`는 모델이 도구 계획을 JSON으로 만든 뒤 Python이 실제 도구를 실행한다.

```text
요청
  -> 모델이 JSON tool plan 작성
  -> Python이 plan을 검증
  -> 선택된 로컬 도구 실행
  -> 실행 결과를 다시 모델에 전달
  -> 최종 답변
```

모델이 만든 JSON은 신뢰할 수 없는 입력으로 취급해야 한다. 허용된 도구인지, 인자가 안전한지, 실행 권한이 있는지 코드에서 검증해야 한다. `eval` 같은 기능은 입력 제한이 부족하면 특히 위험하다.

#### RAG가 환각을 완전히 없애지는 않는다

검색이 잘못된 문서를 가져오거나 모델이 context를 잘못 해석할 수 있다. 프로덕션 RAG에는 출처 표시, 검색 품질 평가, 근거성 평가, 접근 권한 필터, 최신성 관리가 필요하다.

### 5.5 5장: Multi-agent와 Streamlit

`5.2.1_multi_agent_system.py`는 연구원 역할의 결과를 작가 역할의 입력으로 넘긴다.

```text
주제
  -> 연구원 prompt 호출
  -> 연구 노트
  -> 작가 prompt 호출
  -> 블로그 초안
```

여기서 여러 agent가 독립 서버로 서로 통신하는 것은 아니다. 한 Python 프로그램이 여러 역할의 모델 호출을 순서대로 연결한다. 역할 분리는 각 단계의 책임과 prompt를 명확히 하고, 단계별 평가와 재시도를 가능하게 한다.

하지만 agent 수를 늘린다고 항상 품질이 좋아지지는 않는다. 호출 비용과 지연 시간이 증가하고, 앞 단계의 오류가 다음 단계에 전파될 수 있다. 업무가 실제로 분리 가능한 경우에만 사용해야 한다.

Streamlit 예제는 Python 함수에 웹 입력창과 출력 화면을 붙인다.

- `5.3.1_streamlit_app.py`: 한 번 질문하고 답변 표시
- `5.3.2_streamlit_chatbot_with_memory.py`: session state에 대화 누적

UI가 생겼다고 프로덕션 서비스가 완성되는 것은 아니다. 인증, 사용자 격리, rate limit, secret 관리, 배포, 장애 대응, 데이터 보존 정책이 추가로 필요하다.

### 5.6 6장: HTTP 도구 서버와 MCP 개념

하나의 Python 프로그램 안에 모든 기능이 있으면 다른 앱이 재사용하기 어렵다. 6장은 기능을 서버 endpoint로 분리한다.

#### 세션 채팅 서버

`6.4.2_mcp_flask_server.py`는 `/session`으로 session ID를 만들고 `/chat`으로 메시지를 받는다. `6.4.3_mcp_client.py`가 이 서버를 호출한다.

세션 기록은 서버 메모리에만 있으므로 서버 재시작 시 사라지고, 서버가 여러 대라면 서로 상태를 공유하지 못한다. 운영 환경에서는 Redis나 DB 같은 외부 상태 저장소를 고려한다.

#### RAG 도구 서버

`6.6.1_mcp_server_ai_search.py`는 4장의 RAG 기능을 HTTP endpoint로 노출하고, `6.6.2_mcp_client_ai_search.py`가 질문을 보낸다.

이 구조가 주는 장점은 다음과 같다.

- 여러 애플리케이션이 같은 검색 기능 재사용
- 모델 앱과 검색 서비스의 배포 및 확장 분리
- 권한, 로깅, 버전 관리를 서버 경계에서 적용

다시 강조하면 6장 코드는 MCP의 핵심 감각을 익히는 HTTP 예제이며, 완전한 MCP 서버 구현이라고 보면 안 된다.

### 5.7 7장: 운영 통제와 책임 있는 AI

#### Human-in-the-Loop

HITL은 위험하거나 모호한 작업을 자동 실행하지 않고 사람이 검토하게 한다. 금액 승인, 인사 결정, 개인정보 처리처럼 실패 비용이 큰 업무에 필요하다.

`7.3.1_langgraph_interrupt.py`는 파일명과 달리 현재 핵심 구현이 Foundry Responses API와 로컬 사용자 입력을 이용한 중간 피드백 흐름이다. 완전한 영구 워크플로 중단/재개 시스템으로 오해하면 안 된다.

#### Reflection

`7.4.1_reflection_loop.py`는 초안을 만든 후 그 결과를 다시 입력으로 보내 비평하고 개선한다.

Reflection은 모델의 숨겨진 생각을 보는 것이 아니다. 첫 출력물을 다음 호출의 입력으로 넣는 외부 소프트웨어 루프다. 품질이 개선될 수 있지만 호출 비용과 시간이 늘어나며, 같은 모델이 자신의 오류를 항상 발견하는 것도 아니다.

#### Guardrails

`7.6.1_guardrails.py`는 다음 순서로 요청을 처리한다.

```text
입력 수신
  -> 명시적 위험 패턴 검사
  -> 필요하면 모델 분류
  -> BLOCK / NEEDS_HUMAN_REVIEW / ALLOW
  -> 허용된 질문만 정책 context로 답변
  -> 답변의 근거성 재검사
```

규칙 기반 검사는 빠르고 예측 가능하지만 새로운 표현을 놓칠 수 있다. 모델 분류는 유연하지만 결과가 변동할 수 있고 비용이 든다. 실제 시스템에서는 두 방식을 조합하고, 최종 권한 검사는 서버 코드에서 수행한다.

Guardrail은 prompt 한 줄이 아니라 다층 방어다.

- 입력 검증
- 사용자 인증과 권한 확인
- 도구 allowlist
- 민감 정보 제거
- 출력 근거성 검사
- 사람 승인
- 감사 log와 rate limit

### 5.8 8장: 실제 Foundry Agent Service

8장은 로컬 prompt 조합에서 관리형 agent 리소스로 넘어간다.

#### 8.1 Azure AI Search RAG agent

`8.1_create_and_run_foundry_agent.py`는 다음 작업을 수행한다.

1. 회사 정책 문서를 chunk하고 embedding 생성
2. Azure AI Search index 생성 또는 갱신
3. chunk와 vector 업로드
4. Foundry 프로젝트의 Search connection 탐색
5. `AzureAISearchTool`이 연결된 agent version 생성
6. `agent_reference`를 사용해 Responses API 호출
7. 기본값에서는 agent version 삭제

Search 연결이 없으면 정책 context를 user message에 직접 넣는 fallback이 있다. 따라서 실행 성공만 보고 Search tool이 실제 사용됐다고 판단하면 안 되고, 로그에서 tool 연결 여부를 확인해야 한다.

#### 8.2 Knowledge Base agent

Knowledge Base는 미리 만들어 둔 지식 소스를 관리형 검색 도구로 제공한다. 코드가 직접 embedding 검색을 수행하는 8.1과 달리, 8.2는 Knowledge Base의 MCP endpoint에 `knowledge_base_retrieve` 도구로 연결한다.

```text
Foundry agent
  -> MCPTool
  -> Knowledge Base MCP endpoint
  -> Azure AI Search의 지식 소스
```

Knowledge Base는 포털에서 먼저 만들어야 하며, 프로젝트 managed identity와 Search 권한이 맞아야 한다.

#### 8.3 Microsoft Learn MCP agent

`8.3_create_foundry_agent_with_mcp.py`는 Microsoft Learn MCP 서버를 agent 도구로 연결한다.

- `microsoft_docs_search`
- `microsoft_docs_fetch`
- `microsoft_code_sample_search`

모델이 Microsoft 기술 질문을 받으면 공식 문서를 검색하고 가져오는 도구를 사용할 수 있다. `allowed_tools`는 agent가 호출할 수 있는 도구 범위를 제한한다.

예제는 `require_approval="never"`를 사용한다. 교육용 공개 문서 검색에는 편리하지만, 변경이나 결제가 발생하는 도구는 자동 승인으로 두면 안 된다.

#### 8.4 Monitoring

`8.4_foundry_agent_monitoring.py`는 모델을 호출하지 않는다. 포털에서 다음 항목을 확인하는 안내 파일이다.

- 실행 횟수
- 토큰 사용량
- 시간대별 호출과 지연
- 평가 구성 여부
- 안전성/레드팀 실행
- Application Insights 연결 상태

모니터링을 보려면 `FOUNDRY_KEEP_AGENT=true`로 agent를 남겨야 한다. 확인 후에는 직접 삭제해야 한다.

#### 8장의 인증 구분

| 작업 | 인증 방식 | 이유 |
| --- | --- | --- |
| 1~7장 일반 모델 호출 | API key | OpenAI-compatible data plane 호출 |
| 8장 agent 생성/삭제 | Microsoft Entra ID | Azure 리소스 제어 작업 |
| 8.1 agent 답변 | 구성에 따라 API key 사용 가능 | 일반 Search tool 경로 |
| 8.2 Knowledge Base | Entra ID/OBO 필요 | 사용자를 대신한 도구 권한 전달 |
| 8.3 MCP agent | 예제 구성상 Entra ID 사용 | 원격 도구 연결과 agent 실행 |

OBO(On-Behalf-Of)는 agent가 로그인한 사용자 또는 호출 주체를 대신해 다른 보호된 서비스에 접근하도록 토큰 권한을 전달하는 흐름이다.

#### 생성과 정리의 범위를 구분하라

`FOUNDRY_KEEP_AGENT=false`이면 코드가 agent version을 삭제한다. 그러나 다음 리소스까지 자동으로 삭제되는 것은 아니다.

- Foundry 프로젝트
- 모델 배포
- Azure AI Search service와 index
- Knowledge Base와 connection
- Application Insights
- Log Analytics workspace

실습용 리소스를 하나의 전용 resource group에 만들고 종료 후 resource group 전체를 삭제하는 이유가 여기에 있다.

---

## 6. 자주 혼동하는 개념 비교

### Prompt, RAG, fine-tuning

| 방법 | 바꾸는 것 | 적합한 문제 |
| --- | --- | --- |
| Prompt | 호출 시 지시와 예시 | 역할, 형식, 간단한 규칙 |
| RAG | 호출 시 외부 근거 추가 | 사내 문서, 최신 정보, 출처가 필요한 답변 |
| Fine-tuning | 모델의 행동 패턴을 추가 학습 | 반복되는 스타일이나 특수 작업 형식 |

최신 사내 정책을 알려주기 위해 매번 fine-tuning할 필요는 없다. 일반적으로 문서를 갱신하기 쉬운 RAG가 더 적합하다.

### Tool과 RAG

- RAG는 관련 정보를 검색해 모델의 context에 넣는 패턴이다.
- Tool은 계산, 조회, 변경 등 외부 기능 전체를 의미한다.
- RAG 검색기도 agent가 호출하는 하나의 tool이 될 수 있다.

### Workflow와 Agent

- workflow: 실행 순서를 코드가 명확히 결정
- agent: 다음 행동을 모델이 일정 부분 선택

예측 가능성과 감사 가능성이 중요한 업무에서는 모든 것을 자율 agent로 만들기보다, 결정적인 단계는 workflow로 고정하는 편이 안전하다.

### Local memory와 persistent memory

- local memory: 리스트나 프로세스 메모리, 종료하면 사라짐
- persistent memory: DB나 관리형 conversation, 재시작 후에도 유지 가능

장기 보관은 편리하지만 개인정보, 삭제 요청, 사용자 격리, 보존 기간 문제가 생긴다.

### API key와 Entra ID

- API key: 간단하지만 키를 가진 주체를 세밀하게 구분하기 어렵다.
- Entra ID: 사용자/서비스 주체, RBAC, 만료 토큰을 이용해 권한을 세밀하게 관리한다.

프로덕션에서는 가능하면 managed identity와 최소 권한 RBAC를 선호한다.

---

## 7. 실습 전에 이해해야 할 운영 관점

### 7.1 정확성

- 답변이 자연스러운가가 아니라 근거와 일치하는가를 확인한다.
- RAG에서는 검색 결과와 최종 답변을 함께 본다.
- 문서에 답이 없을 때 “모른다”고 말하는지 확인한다.

### 7.2 보안

- `.env`와 API key를 Git에 commit하지 않는다.
- 모델이 만든 tool argument를 검증한다.
- 사용자의 문서 접근 권한을 검색 단계에도 적용한다.
- TLS 검증 비활성화는 실습용 예외로만 취급한다.
- prompt나 trace에 개인정보가 남지 않도록 한다.

### 7.3 비용

비용은 주로 모델의 입력/출력 토큰과 시간당 Azure 리소스에서 발생한다.

- 긴 대화 기록과 긴 검색 context는 입력 비용 증가
- reflection과 multi-agent는 모델 호출 횟수 증가
- Azure AI Search는 생성 후 사용하지 않아도 SKU에 따라 시간당 과금
- Application Insights와 Log Analytics는 telemetry 수집량에 따라 과금 가능

모델 배포는 실습에서 종량제 Standard/Global Standard를 사용하고, 고정 용량 비용이 발생하는 Provisioned Throughput을 실수로 선택하지 않는다.

### 7.4 신뢰성

- timeout과 재시도 횟수 제한
- 외부 도구 장애 시 fallback
- 같은 작업이 재시도돼도 중복 결제나 중복 변경이 생기지 않는 설계
- JSON schema 검증
- 모델 버전과 prompt 버전 기록

### 7.5 평가

AI 시스템은 일반 코드의 성공/실패만으로 품질을 판단하기 어렵다. 다음 항목을 별도로 측정해야 한다.

- 정답성
- 근거성
- 검색 적중률
- 출처 정확성
- 위험 요청 차단률과 정상 요청 오탐률
- 응답 시간
- 요청당 토큰과 비용

---

## 8. 실습할 때 파일을 읽는 방법

각 파일을 실행하기 전에 다음 순서로 읽으면 된다.

1. 파일 위쪽의 `# 학습 포인트` 확인
2. 입력 데이터와 system prompt 찾기
3. 모델을 호출하는 함수 찾기
4. 로컬 도구나 검색 함수가 있는지 확인
5. 이전 출력이 다음 입력에 들어가는 위치 찾기
6. 상태가 어디에 저장되는지 확인
7. 실패 시 fallback과 정리 코드 확인
8. 실행 후 trace와 token usage 확인

실행 결과가 예상과 달라도 곧바로 실패라고 판단하지 않는다. 생성형 모델의 문장은 매번 조금씩 달라질 수 있다. 대신 구조적으로 다음이 맞는지 확인한다.

- 올바른 모델과 endpoint를 호출했는가?
- 의도한 문서나 도구가 사용됐는가?
- 금지된 요청이 차단됐는가?
- 근거가 없는 답변을 제한했는가?
- 생성한 리소스를 정리했는가?

---

## 9. 실습 전 자가 점검 문제

아래 질문에 자신의 말로 답할 수 있으면 실습을 시작할 준비가 된 것이다.

1. LLM이 데이터베이스와 다른 점은 무엇인가?
2. Multi-turn 대화에서 모델은 이전 대화를 어떻게 알게 되는가?
3. system prompt와 user prompt의 역할은 어떻게 다른가?
4. Embedding 모델과 답변 생성 모델의 역할은 어떻게 다른가?
5. RAG의 indexing 단계와 retrieval/generation 단계는 무엇인가?
6. RAG가 환각을 완전히 제거하지 못하는 이유는 무엇인가?
7. 모델이 계산기나 API를 직접 실행하는 것과 tool을 선택하는 것은 어떻게 다른가?
8. 이 저장소의 3장 agent와 8장 agent의 차이는 무엇인가?
9. 5장의 multi-agent는 실제로 어떻게 결과를 주고받는가?
10. 6장의 예제가 완전한 MCP 구현이 아닌 이유는 무엇인가?
11. Reflection은 왜 모델의 내부 사고를 읽는 기능이 아닌가?
12. Guardrail을 prompt 하나로 끝내면 안 되는 이유는 무엇인가?
13. API key와 Entra ID 인증은 언제 각각 사용되는가?
14. `FOUNDRY_KEEP_AGENT=false`가 삭제하지 않는 Azure 리소스는 무엇인가?
15. Trace에 prompt 본문을 저장할 때 어떤 위험이 있는가?

## 10. 한 문장으로 정리한 전체 과정

> 이 실습은 LLM 호출을 출발점으로 삼아, 문맥과 상태를 관리하고, RAG와 도구로 능력을 확장하고, 역할 분업과 서버 경계로 구조화하고, guardrail과 trace로 통제한 뒤, Microsoft Foundry Agent Service에 실제 운영 가능한 형태로 연결하는 과정이다.

## 11. 원본 자료에서 다음에 읽을 파일

이 가이드를 읽은 후 실제 실습 전에 다음 순서로 원문을 확인한다.

1. [`../README.md`](../README.md): 환경 준비와 전체 실행 순서
2. [`../CURRICULUM_SCENARIO.md`](../CURRICULUM_SCENARIO.md): 6시간 강의 흐름
3. 각 장의 `README.md`: 장별 실행 명령과 관찰 포인트
4. [`../APPENDIX.md`](../APPENDIX.md): `.env`, 인증, trace 정리
5. [`../TROUBLESHOOTING.md`](../TROUBLESHOOTING.md): 회사 프록시와 인증서 문제

실제 실행 시에는 모든 선택 예제를 한꺼번에 돌리기보다 루트 README의 권장 실행 순서를 먼저 따라가고, 각 단계에서 입력·중간 결과·최종 출력·trace를 비교한다.
