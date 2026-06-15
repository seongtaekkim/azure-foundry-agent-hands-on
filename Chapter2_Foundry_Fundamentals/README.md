# 제2장: Microsoft Foundry 프로젝트와 공통 실행 기반

> [!NOTE]
> 이 장의 명령 예시는 OS에 따라 문법이 다른 경우 **Windows (PowerShell)** 와 **macOS / Linux (bash, zsh)** 블록으로 나눠 표기합니다. 본인이 사용하는 OS의 블록을 따라 실행하세요. `uv run ...`처럼 양쪽이 동일한 명령은 그대로 사용하면 됩니다.

## 2.1 이 장의 목표

1장에서 모델 호출과 프롬프트 패턴을 경험했다면, 2장에서는 이후 모든 챕터가 공유하는 Foundry 실행 기반을 정리합니다. `foundry_hands_on` 패키지는 숨겨진 예제가 아니라, 전체 실습을 안정적으로 반복하기 위한 공통 계층입니다.

이 장을 마치면 다음을 설명할 수 있습니다.

- OpenAI-compatible endpoint, API key, 모델 배포명이 왜 모든 실습의 출발점인지 이해합니다.
- API key 기반 인증 흐름을 확인합니다.
- `foundry_hands_on/config.py`, `client.py`, `agents.py`, `tracing.py`의 역할을 구분합니다.
- 공통 유틸을 사용해 Responses API 호출과 trace span을 실행합니다.

## 2.2 핵심 파일

- `2.1_check_foundry_settings.py`: `.env`와 Foundry 설정 확인
- `2.2_foundry_responses_smoke_test.py`: 공통 client 유틸로 Responses API 호출
- `2.3_foundry_tracing_smoke_test.py`: OpenTelemetry trace 설정 확인

## 2.3 공통 계층 구조

| 파일 | 역할 |
| --- | --- |
| `foundry_hands_on/config.py` | `.env`에서 endpoint, API key, model deployment, reasoning effort, optional project endpoint 설정을 읽습니다. |
| `foundry_hands_on/client.py` | API key 기반 OpenAI 호환 client를 만들고 Responses API 호출을 수행합니다. 기본 reasoning effort는 `low`입니다. |
| `foundry_hands_on/agents.py` | API key 기반 prompt-style agent 실행을 담당합니다. |
| `foundry_hands_on/tracing.py` | 기본은 console exporter로 OpenTelemetry span을 출력하고, Application Insights connection string이 있을 때만 Azure Monitor로 보냅니다. |
| `foundry_hands_on/rag.py` | 교육용 로컬 RAG 검색/생성 흐름을 제공합니다. |
| `foundry_hands_on/learning.py` | 각 실습 파일의 실행 명령과 학습 포인트를 읽어 초보자용 안내 블록을 출력합니다. |

각 챕터 폴더의 `_bootstrap.py`는 저장소 루트를 Python import 경로에 추가합니다. 그래서 VS Code 실행 버튼, 챕터 폴더에서 직접 실행, `uv run streamlit run`처럼 실행 위치가 달라도 `foundry_hands_on` 모듈을 찾을 수 있습니다.

## 2.4 실행 순서

아래 세 파일을 번호 순서대로 실행합니다. 모두 2장 핵심 실습이며, `2.3`은 Application Insights 연결이 없어도 콘솔 trace로 동작하므로 그대로 실행하면 됩니다.

```bash
uv run Chapter2_Foundry_Fundamentals/2.1_check_foundry_settings.py
uv run Chapter2_Foundry_Fundamentals/2.2_foundry_responses_smoke_test.py
uv run Chapter2_Foundry_Fundamentals/2.3_foundry_tracing_smoke_test.py
```

## 2.5 강의 포인트

- 1장 예제도 2장의 공통 client를 사용합니다.
- 3장부터는 같은 설정 위에서 prompt-style agent 실행을 사용합니다.
- 7장은 human review, reflection, guardrails처럼 운영 통제 패턴을 다룹니다.
- 8장은 실제 Foundry Agent Service agent 생성/실행, Knowledge base, MCPTool 코드 연결, 포털 모니터링을 다룹니다.

## 2.6 실행 결과를 볼 때 확인할 점

각 파일은 실행 시작 시 `학습 목표`, `쉽게 말하면`, `관찰 포인트`를 먼저 출력합니다. 2장은 공통 실행 기반을 확인하는 장이므로, 안내 블록 다음에 `.env` 값, Responses API 호출, OpenTelemetry span이 어떤 순서로 출력되는지 봅니다.

`2.1_check_foundry_settings.py`는 기본 모델 호출에 필요한 endpoint, API key, API version, model deployment, embedding deployment, reasoning effort를 확인합니다.

`2.2_foundry_responses_smoke_test.py`는 공통 client가 Responses API를 정상 호출하는지 확인하는 최소 테스트입니다. 이 호출 경로가 이후 장의 prompt-style agent, RAG, guardrails 예제에서도 재사용됩니다.

`2.3_foundry_tracing_smoke_test.py`는 현재 기본 설정에서 OpenTelemetry span이 콘솔에 출력되는지 확인합니다. Application Insights는 별도 connection string을 설정한 경우에만 Azure Monitor로 전송됩니다.
