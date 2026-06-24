# 3장 설명: Agent 개념과 상태 관리

## 이 장의 목적

3장은 단순 질문·답변에서 목표와 역할을 가진 agent 형태로 이동한다. 핵심은 모델을 사람처럼 표현하는 것이 아니라 모델 호출 주변에 상태와 행동 구조가 왜 필요한지 이해하는 것이다.

## Chatbot과 Agent

```text
Chatbot: 질문 -> 답변
Agent: 목표 -> 상황 인식 -> 계획 -> 도구/행동 -> 결과 확인
```

Agent의 대표 mental model은 Sense-Think-Act다.

- Sense: 사용자 요청과 현재 상태를 읽는다.
- Think: 필요한 작업과 도구를 정한다.
- Act: 답변 생성이나 도구 호출을 수행한다.

## 핵심 파일

| 파일 | 역할 |
| --- | --- |
| `3.4.2_agent_app.py` | 역할 지시문 기반 기본 agent |
| `3.4.4_agent_with_calculator.py` | 정확한 도구가 필요한 이유 |
| `3.4.5_stateful_agent.py` | 메시지 리스트로 상태 유지 |

## Prompt-style agent의 범위

3장의 agent는 Foundry 프로젝트에 등록된 독립 리소스가 아니다. `run_prompt_agent()`가 system instruction과 user input을 일반 Responses API 호출로 전달한다.

따라서 이 단계의 핵심은 다음이다.

- 역할을 instruction으로 분리
- agent 이름과 실행 시나리오 구분
- 외부 도구가 필요한 질문에서 모델의 한계 발견
- 이전 메시지를 다음 호출에 포함

실제 Foundry Agent Service agent는 8장에서 만든다.

## 왜 도구가 필요한가

실시간 날씨, 정확한 계산, 사내 DB 조회는 모델의 언어 생성 능력만으로 해결하면 안 된다. 모델은 “어떤 도구가 필요하다”는 판단을 도울 수 있지만 실제 데이터 조회와 권한 검사는 외부 코드가 담당해야 한다.

## State의 실제 위치

`3.4.5_stateful_agent.py`는 `messages` 리스트에 user와 assistant 메시지를 append한다. 두 번째 질문 때 누적된 리스트 전체가 모델로 전송된다.

- Python 프로세스 안에만 존재한다.
- 프로그램 종료 시 사라진다.
- 여러 사용자를 처리하려면 사용자별 격리가 필요하다.
- 영구 memory가 필요하면 DB와 보존 정책을 설계해야 한다.

## Agent framework가 해결하는 문제

- 상태 저장과 복구
- 도구 schema와 호출
- 분기와 반복 실행
- 실패 처리와 재시도
- 사람 승인 지점
- trace와 평가

모든 문제를 자율 agent로 만들 필요는 없다. 실행 순서가 고정되고 위험한 업무는 명시적 workflow가 더 안전하다.

## 이 장을 읽고 답할 수 있어야 하는 질문

1. Chatbot과 agent의 구조적 차이는 무엇인가?
2. 3장의 agent가 8장의 agent와 다른 점은 무엇인가?
3. 실시간 날씨에 외부 도구가 필요한 이유는 무엇인가?
4. `messages` 리스트는 영구 memory인가?
5. 자율 agent보다 고정 workflow가 적합한 경우는 언제인가?

## 다음 장과의 연결

3장에서 도구의 필요성을 발견했다. 4장에서는 계산기, 문서 검색, RAG, AI 도구 라우터를 실제 코드로 붙인다.
