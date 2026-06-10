# 제1장: 생성 AI 첫걸음: Python으로 시작하기

## 1.1 이 장의 목표 (Learning Objectives)

AI 개발이라는 흥미진진한 여정의 출발선에 오신 것을 환영합니다. 이 장을 마치면, 여러분은 더 이상 AI를 막연한 개념이 아닌, 코드를 통해 직접 소통하고 제어할 수 있는 강력한 도구로 인식하게 될 것입니다. 이 장의 학습 목표는 다음과 같습니다.

- 생성 AI와 LLM(대규모 언어 모델)의 핵심 개념을 자신의 언어로 설명할 수 있습니다.
- AI 개발을 위한 안정적인 Python 개발 환경을 직접 구축할 수 있습니다.
- Microsoft Foundry 또는 Azure OpenAI에서 모델을 배포하고, endpoint와 API key 인증 흐름을 관리할 수 있습니다.
- Python 코드를 작성하여 Foundry 프로젝트의 Responses API에 첫 요청을 보내고, AI가 생성한 응답을 성공적으로 받아볼 수 있습니다.
- 역할 부여(Role), 제로샷(Zero-shot) 등 가장 기본적인 프롬프트 엔지니어링 기법을 이해하고 적용할 수 있습니다.

## 1.2 필수 도구 선택: 왜 Python과 Microsoft Foundry인가?

본격적인 실습에 앞서, 우리가 왜 수많은 기술 조합 중 **Python**과 **Microsoft Foundry**를 선택했는지 이해하는 것은 중요합니다.

- **Python:** 데이터 과학과 AI의 세상에서 Python은 '공용어(Lingua Franca)'입니다. 배우기 쉬운 문법과 Azure SDK 생태계는 아이디어를 가장 빠르게 프로토타입으로 만들 수 있게 해줍니다.
- **Microsoft Foundry:** 단순 모델 호출을 넘어, 모델 배포, 에이전트형 실행, 도구 연결, MCP, trace 관찰을 한 곳에서 다룰 수 있는 운영형 AI 개발 플랫폼입니다.

## 1.3 AI의 뇌 해부하기: 핵심 개념 정복

- **생성 AI (Generative AI):** 기존 데이터를 학습하여 **세상에 없던 새로운 콘텐츠(텍스트, 이미지, 코드 등)를 생성**하는 인공지능의 한 분야입니다.
- **LLM (Large Language Model):** 생성 AI를 구현하는 엔진의 한 종류로, **'다음에 올 단어를 가장 확률 높게 예측하는 정교한 프로그램'**이라고 할 수 있습니다.
- **토큰 (Token):** LLM이 텍스트를 처리하는 기본 단위입니다. Foundry 프로젝트의 모델 사용량과 비용을 이해할 때 매우 중요한 개념입니다.

## 1.4 Hands-on: 나의 첫 AI 개발 지휘소 구축하기

## 1.5 권장 실행 순서

6시간 hands-on에서는 아래 파일만 필수로 실행합니다.

```bash
uv run Chapter1_Getting_Started/1.5_first_openai_call.py
uv run Chapter1_Getting_Started/1.6.4.4_mulit_turn.py
```

나머지 파일은 프롬프트 패턴을 더 연습하기 위한 선택 실습입니다.

| 파일 | 구분 | 학습 포인트 |
| --- | --- | --- |
| `1.6.3.1_role_assignment.py` | 선택 | 역할 부여 prompt |
| `1.6.4.2_few_shot_code.py` | 선택 | few-shot 예시 제공 |
| `1.6.4.3_cot_example.py` | 선택 | 단계적 추론 요청 방식 |
| `1.6.4.5_category_classifier.py` | 선택 | 간단한 분류기 prompt |
| `1.6.4.6_prompt_engineering_1.py` | 선택 | 출력 형식 제어 |
| `1.6.4.7_story_generator.py` | 선택 | 창의적 생성 prompt |
| `1.6.4.8_prompt_engineering_2.py` | 선택 | 제약 조건이 있는 생성 |

`1.5_first_openai_call.py`는 기존 파일명을 유지하지만, 내부 구현은 Foundry 프로젝트의 OpenAI 호환 Responses API를 사용합니다.

## 1.6 실행 결과를 볼 때 확인할 점

모든 1장 실습 파일은 실행 직후 학습 목표 안내 블록을 출력합니다. 먼저 `쉽게 말하면` 문장을 읽고, 이어서 실제로 출력되는 system/user prompt와 모델 응답을 비교합니다.

`run_single_turn_prompt()`를 사용하는 예제는 공통 함수에서 system prompt와 user prompt를 먼저 출력한 뒤 모델 응답을 출력합니다. 따라서 터미널에서 “모델에게 어떤 지시가 전달되었는지”와 “그 결과가 어떻게 달라졌는지”를 함께 비교합니다.

`1.6.4.4_mulit_turn.py`는 이전 대화를 `messages` 리스트에 누적합니다. 1단계에서 만든 파리 여행 계획 전체가 assistant 메시지로 저장되고, 2단계 요청에서는 그 기록이 다시 모델 입력으로 전달됩니다. 이 상태는 실행 중인 Python 메모리에만 있으며 프로그램을 종료하면 사라집니다.

`1.6.4.3_cot_example.py`의 목적은 모델의 숨겨진 내부 사고를 보는 것이 아니라, 사용자가 문제를 단계적으로 풀도록 요청했을 때 최종 답변 구조가 어떻게 달라지는지 확인하는 것입니다.
