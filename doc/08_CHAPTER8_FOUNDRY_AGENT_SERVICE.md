# 8장 설명: Microsoft Foundry Agent Service

## 이 장의 목적

8장은 일반 Responses API를 역할별로 호출하던 로컬 예제에서 벗어나 Foundry 프로젝트에 실제 agent version을 만들고 관리형 도구를 연결한다.

## 전체 구조

```text
Python SDK
  -> Foundry project에 agent version 생성
  -> 모델과 tool 정의 연결
  -> agent_reference로 Responses API 호출
  -> trace/monitoring 확인
  -> agent version 정리
```

## 핵심 파일

| 파일 | 역할 |
| --- | --- |
| `8.1_create_and_run_foundry_agent.py` | Azure AI Search RAG agent 생성 |
| `8.2_create_foundry_agent_with_knowledge_base.py` | Knowledge Base MCPTool agent |
| `8.3_create_foundry_agent_with_mcp.py` | Microsoft Learn MCP agent |
| `8.4_foundry_agent_monitoring.py` | 포털 monitoring 확인 안내 |

## 8.1 Search tool agent

1. 회사 정책을 chunk한다.
2. `text-embedding-3-small`로 vector를 만든다.
3. Azure AI Search index를 생성·갱신한다.
4. 문서와 vector를 업로드한다.
5. Foundry project의 Search connection을 찾는다.
6. `AzureAISearchTool`이 연결된 agent version을 만든다.
7. 질문 후 기본값에서는 agent version을 삭제한다.

Search 연결이 실패하면 context를 user message에 직접 넣는 fallback이 있다. 실행 성공만 확인하지 말고 로그에서 Search tool이 실제 연결됐는지 봐야 한다.

## 8.2 Knowledge Base agent

Knowledge Base는 포털에서 먼저 만든다. 코드는 Knowledge Base MCP endpoint를 `MCPTool`로 agent에 연결하고 `knowledge_base_retrieve`를 호출하게 한다.

8.1은 코드가 chunk와 embedding, index를 직접 다룬다. 8.2는 준비된 Knowledge Base가 검색을 담당한다.

## 8.3 Microsoft Learn MCP agent

공식 Microsoft Learn MCP 서버의 문서 검색·가져오기·코드 샘플 검색 도구를 연결한다. `allowed_tools`는 agent가 호출할 수 있는 기능을 제한한다.

예제의 `require_approval="never"`는 읽기 전용 공개 문서 실습에는 편리하지만, 데이터 변경이나 결제가 발생하는 tool에는 사람 승인 정책이 필요하다.

## 인증 구분

| 작업 | 주요 인증 |
| --- | --- |
| 일반 모델 호출 | API key |
| Agent version 생성·삭제 | Microsoft Entra ID |
| Knowledge Base/OBO tool | Entra ID 사용자 토큰과 권한 |
| Azure AI Search 직접 업로드 | Search key 또는 적절한 Entra 권한 |

Entra ID는 RBAC와 주체별 권한을 제공한다. OBO는 agent가 사용자를 대신해 보호된 도구에 접근하도록 사용자 권한을 전달하는 방식이다.

## Monitoring

`8.4_foundry_agent_monitoring.py` 자체는 새 모델 호출을 하지 않는다. 포털에서 실행 수, 토큰, 평가, Application Insights 연결 상태를 확인하는 절차를 출력한다.

Agent를 포털에서 보려면 `FOUNDRY_KEEP_AGENT=true`로 남기고, 확인 후 직접 삭제한다.

## 자동 삭제 범위를 오해하지 말 것

`FOUNDRY_KEEP_AGENT=false`는 생성한 agent version을 삭제하지만 다음 리소스는 삭제하지 않는다.

- Foundry 프로젝트와 모델 배포
- Azure AI Search service/index
- Knowledge Base와 project connection
- Application Insights와 Log Analytics

실습용 리소스를 한 resource group에 만들고 끝난 뒤 resource group 전체를 삭제하는 것이 안전하다.

## 비용과 보안 주의

- 종량제 Standard/Global Standard 모델 배포 사용
- Provisioned Throughput을 실수로 선택하지 않기
- Azure AI Search는 사용하지 않아도 SKU별 시간 과금 가능
- API key와 connection string을 Git에 저장하지 않기
- managed identity와 최소 권한 RBAC 사용
- trace 본문에 개인정보가 기록되지 않는지 확인

## 이 장을 읽고 답할 수 있어야 하는 질문

1. 3장의 prompt-style agent와 8장의 agent version은 어떻게 다른가?
2. 8.1과 8.2의 RAG 책임 범위는 어떻게 다른가?
3. Agent 생성·삭제에 Entra ID가 필요한 이유는 무엇인가?
4. `allowed_tools`와 approval 정책은 왜 필요한가?
5. `FOUNDRY_KEEP_AGENT=false`가 삭제하지 않는 것은 무엇인가?
6. Monitoring에서 어떤 품질·비용 신호를 확인해야 하는가?

## 전체 과정의 결론

8장까지의 핵심은 “모델 하나”가 아니라 모델, 검색, 도구, 상태, 인증, 안전장치, trace를 하나의 운영 가능한 시스템으로 연결하는 것이다.
