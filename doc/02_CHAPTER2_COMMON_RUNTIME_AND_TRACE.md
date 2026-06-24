# 2장 설명: 공통 실행 기반과 Trace

## 이 장의 목적

2장은 여러 실습이 같은 방식으로 endpoint, API key, 모델 배포명을 사용하도록 공통 코드를 만든다. 기능 개발 전에 연결 상태를 작은 smoke test로 확인하는 습관도 배운다.

## 왜 공통 계층이 필요한가

각 파일이 직접 환경 변수를 읽고 client를 만들면 설정 이름, 오류 처리, tracing 방식이 달라진다. 공통 계층을 두면 변경 지점이 한곳으로 줄고 모든 장이 같은 실행 규칙을 사용한다.

## 핵심 파일

| 파일 | 역할 |
| --- | --- |
| `2.1_check_foundry_settings.py` | `.env` 필수 값 검사 |
| `2.2_foundry_responses_smoke_test.py` | 최소 Responses API 호출 |
| `2.3_foundry_tracing_smoke_test.py` | OpenTelemetry span 확인 |
| `foundry_hands_on/config.py` | 환경 변수와 인증 설정 |
| `foundry_hands_on/client.py` | client 생성과 모델 호출 |
| `foundry_hands_on/tracing.py` | console/Application Insights exporter |

## `.env`를 사용하는 이유

설정과 코드를 분리하면 같은 코드를 개발·테스트·운영 환경에서 재사용할 수 있다. `.env.example`에는 변수 이름만 두고 실제 key는 `.env`에 둔다.

```text
.env -> config.py -> FoundrySettings -> client.py -> 모델 호출
```

`.env`는 편리한 로컬 방식이지 중앙 secret 관리 시스템은 아니다. 운영 환경에서는 Key Vault나 배포 플랫폼의 secret 기능을 사용한다.

## Smoke test

Smoke test는 복잡한 agent를 실행하기 전에 가장 기본적인 연결만 확인하는 작은 테스트다.

1. 설정을 읽을 수 있는가?
2. 인증에 성공하는가?
3. 모델 배포명이 존재하는가?
4. 최소 응답이 반환되는가?

이 테스트가 실패하면 RAG나 agent 코드부터 디버깅할 필요가 없다.

## Trace와 span

```text
Trace: 사용자 요청 하나의 전체 여정
  +-- Span: 설정 확인
  +-- Span: 모델 호출
  +-- Span: 검색 또는 도구 호출
```

이 저장소는 Application Insights 연결 문자열이 없으면 span을 콘솔에 출력한다. 연결 문자열이 있으면 Azure Monitor로 전송한다.

Trace에서 볼 수 있는 대표 정보는 실행 구간, 시작/종료 시각, 오류, 지연 시간이다. Prompt와 응답 본문 기록은 개인정보와 secret 유출 위험이 있어 기본적으로 꺼져 있다.

## Reasoning fallback

공통 client는 기본 reasoning effort를 `low`로 보낸다. endpoint나 모델이 이 옵션을 거부하면 reasoning 값을 제거하고 재시도한다. 공통 계층이 호환성 차이를 흡수하는 예다.

## 보안 주의

현재 교육용 설정은 회사 TLS 프록시 대응을 위해 SSL 검증 비활성화 기본값을 사용한다. 실제 서비스에서는 다음처럼 검증을 켜야 한다.

```dotenv
FOUNDRY_DISABLE_SSL_VERIFY=false
```

회사 인증서 문제는 검증을 계속 끄기보다 Root CA를 올바르게 등록해 해결하는 것이 원칙이다.

## 이 장을 읽고 답할 수 있어야 하는 질문

1. 공통 client가 없으면 어떤 문제가 생기는가?
2. Smoke test를 복잡한 실습보다 먼저 실행하는 이유는 무엇인가?
3. Trace와 log는 어떻게 다른가?
4. Application Insights가 없어도 실습 가능한 이유는 무엇인가?
5. Trace에 prompt 본문을 저장할 때 어떤 위험이 있는가?

## 다음 장과의 연결

3장은 이 공통 client 위에 역할 지시문과 상태를 추가해 prompt-style agent를 만든다.
