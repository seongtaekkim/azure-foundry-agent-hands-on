# 6장 설명: HTTP 도구 서버와 MCP

## 이 장의 목적

6장은 모델과 RAG 기능을 애플리케이션 내부 함수에서 독립 서버 endpoint로 분리한다. 이를 통해 MCP와 원격 도구의 기본 구조를 이해한다.

## 왜 서버로 분리하는가

- 여러 앱이 같은 도구를 재사용할 수 있다.
- 모델 앱과 검색 서비스를 독립 배포할 수 있다.
- 권한, 버전, 로깅을 서비스 경계에서 관리할 수 있다.
- 부하가 큰 기능만 별도로 확장할 수 있다.

## 핵심 파일

| 파일 | 역할 |
| --- | --- |
| `6.4.2_mcp_flask_server.py` | session별 채팅 상태를 가진 Flask 서버 |
| `6.4.3_mcp_client.py` | session 생성과 채팅 요청 |
| `6.6.1_mcp_server_ai_search.py` | 회사 정책 RAG HTTP 서버 |
| `6.6.2_mcp_client_ai_search.py` | RAG 도구 endpoint 호출 |

## Client와 server

Client는 JSON 요청을 보내고 server는 endpoint에서 요청을 처리해 JSON 응답을 반환한다. 서버 터미널과 클라이언트 터미널을 함께 봐야 요청이 네트워크 경계를 통과하는 과정을 이해할 수 있다.

## Session

6.4 서버는 session ID마다 대화 기록을 나눈다. 그러나 기록은 서버 프로세스 메모리에만 있다.

- 서버 재시작 시 소멸
- 서버가 여러 대면 상태가 서로 다름
- 사용자 인증과 session 탈취 방어가 없음

운영 환경에서는 외부 DB/캐시, 만료 시간, 사용자 소유권 확인이 필요하다.

## MCP와 이 예제의 관계

MCP는 agent가 외부 도구의 목록, 입력, 결과를 일관된 방식으로 다루게 하는 프로토콜이다. 6장 코드는 MCP 표준 전체를 구현한 것이 아니라 HTTP endpoint, payload, 도구 서버 분리라는 기초 감각을 익히는 “MCP 스타일” 예제다.

실제 Foundry `MCPTool` 연결은 8장에서 Microsoft Learn MCP와 Knowledge Base MCP endpoint를 이용해 확인한다.

## 운영 서버에 추가할 것

- TLS와 인증
- 도구별 권한
- 입력 schema 검증
- timeout, retry, circuit breaker
- rate limit
- 감사 log와 trace propagation
- API versioning
- health check

## 이 장을 읽고 답할 수 있어야 하는 질문

1. 내부 함수를 HTTP 서버로 분리하면 무엇이 좋아지는가?
2. Session ID와 사용자 인증은 왜 별개의 문제인가?
3. 서버 메모리 상태의 한계는 무엇인가?
4. 6장 코드가 완전한 MCP 구현이 아닌 이유는 무엇인가?
5. 원격 도구를 자동 호출할 때 어떤 통제가 필요한가?

## 다음 장과의 연결

기능을 외부로 확장할수록 위험과 장애 지점도 늘어난다. 7장은 사람 승인, reflection, guardrail로 실행을 통제한다.
