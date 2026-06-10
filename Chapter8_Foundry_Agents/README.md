# 제8장: Microsoft Foundry Agent Service와 Knowledge 기반 Agent

> [!NOTE]
> 이 장의 명령 예시는 OS에 따라 문법이 다른 경우 **Windows (PowerShell)** 와 **macOS / Linux (bash·zsh)** 블록으로 나눠 표기합니다. 본인이 사용하는 OS의 블록을 따라 실행하세요. `uv run ...`처럼 양쪽이 동일한 명령은 그대로 사용하면 됩니다.

## 8.1 이 장의 목표

5장에서 prompt-style multi-agent 협업 구조를 확인했다면, 8장에서는 Microsoft Foundry 프로젝트 안에 실제 agent version을 생성하고 실행하는 흐름으로 넘어갑니다. 이 장은 Knowledge base, Azure AI Search, MCPTool, Application Insights monitoring을 하나의 Foundry Agent Service 흐름으로 묶어 확인합니다.

이 장을 마치면 다음을 수행할 수 있습니다.

- `FOUNDRY_PROJECT_ENDPOINT`와 Azure credential을 사용해 Foundry Agent Service를 호출합니다.
- 직접 Azure AI Search index를 만들고 Foundry Agent Search tool로 연결하는 구조를 이해합니다.
- Foundry IQ/Knowledge base를 만든 뒤 MCPTool로 agent에 연결합니다.
- 코드에서 원격 MCP 서버를 Foundry Agent tool로 연결하고 실행합니다.
- Application Insights와 Foundry monitoring 화면에서 agent 실행 흔적을 확인합니다.
- 실행 후 생성한 agent version을 정리하거나, `FOUNDRY_KEEP_AGENT=true`로 포털에 남깁니다.

## 8.2 핵심 파일

- `8.1_create_and_run_foundry_agent.py`: 회사 정책 문서를 chunk/embedding으로 나누고 Azure AI Search index와 Foundry Agent Search tool을 직접 연결하는 비교 실습
- `8.2_create_foundry_agent_with_knowledge_base.py`: 포털에서 만든 Knowledge base MCP endpoint를 Foundry Agent의 `MCPTool`로 연결하고 질의응답하는 실습
- `8.3_create_foundry_agent_with_mcp.py`: Microsoft Learn MCP 서버를 Foundry Agent의 `MCPTool`로 연결하고 질문을 실행하는 실습
- `8.4_foundry_agent_monitoring.py`: Foundry 포털의 agent 모니터링 화면에서 운영 메트릭과 App Insights 연결 상태를 읽는 안내 실습

## 8.3 API key 호출과 Project SDK 호출의 차이

1장부터 7장까지의 기본 실습은 `FOUNDRY_OPENAI_ENDPOINT`와 `FOUNDRY_API_KEY`를 사용해 OpenAI-compatible endpoint를 호출합니다. 반면 이 장은 Foundry 프로젝트 리소스에 agent version을 만들기 때문에 `FOUNDRY_PROJECT_ENDPOINT`와 Azure credential을 사용합니다.

로컬에서는 다음 중 하나가 필요합니다.

- Azure CLI `az login`
- VS Code Azure Account 로그인
- `DefaultAzureCredential`이 사용할 수 있는 관리 ID 또는 서비스 주체 환경

VS Code Azure Account 로그인을 `DefaultAzureCredential`에서 사용하려면 이 저장소의 `pyproject.toml`에 포함된 `azure-identity-broker` 패키지가 필요합니다. `uv sync`를 실행하면 함께 설치됩니다.

회사 네트워크에서 Zscaler 같은 TLS inspection/proxy를 사용하는 경우 `az login` 또는 Python SDK 호출이 `CERTIFICATE_VERIFY_FAILED`로 실패할 수 있습니다. 이때는 Zscaler Root CA를 OS 인증서 저장소(Windows 인증서 저장소 또는 macOS Keychain), Azure CLI, Python이 신뢰하도록 등록하거나 실습 중 프록시를 비활성화한 뒤 `az login`을 먼저 확인합니다.

Agent Service 예제인 8.1, 8.2, 8.3은 `FOUNDRY_REASONING_EFFORT`를 요청에 보내지 않습니다. 일반 Responses API 예제에서는 reasoning effort를 `low`로 유지하지만, Agent Service 경로에서는 일부 endpoint가 reasoning 옵션을 거절할 수 있어 초보자 실습에서는 생략합니다.

## 8.4 학습 전에 수동으로 준비할 것

8장은 앞 장과 달리 Foundry 프로젝트, Azure AI Search, Knowledge base, Application Insights 같은 Azure/Foundry 리소스를 함께 사용합니다. 아래 항목을 먼저 확인하면 실행 중 인증 오류나 리소스 없음 오류를 크게 줄일 수 있습니다.

| 구분 | 필요한 준비 | 사용하는 파일 | 필수 여부 |
| --- | --- | --- | --- |
| Foundry 프로젝트 | 모델 배포와 project endpoint 확인 | 8.1, 8.2, 8.3 | 필수 |
| Azure 로그인 | `DefaultAzureCredential`이 사용할 수 있도록 `az login` 또는 VS Code Azure Account 로그인 | 8.1, 8.2, 8.3 | 필수 |
| Azure AI Search 서비스 | Search endpoint와 key 확인 | 8.1, 8.2 | 필수 |
| Foundry Search connection | Foundry project에 Azure AI Search connection 추가 | 8.1 | 권장 |
| Knowledge base | Foundry 포털 또는 Azure Portal에서 Knowledge base 생성 | 8.2 | 필수 |
| Knowledge base MCP connection | 코드가 Knowledge base MCP endpoint를 가리키는 RemoteTool/MCP project connection 생성 | 8.2 | 필수 |
| 원격 MCP 서버 | Microsoft Learn MCP server URL을 `MCPTool`로 연결 | 8.3 | 필수 |
| Application Insights | 수동 생성 후 connection string 복사 | 8.4 | 모니터링 확인 시 권장 |

### 8.4.1 Foundry 프로젝트와 모델 배포 확인

Foundry 포털에서 실습에 사용할 프로젝트를 열고 다음 값을 확인합니다.

1. 프로젝트의 endpoint를 복사합니다.
2. `.env`의 `FOUNDRY_PROJECT_ENDPOINT`에 넣습니다.
3. 프로젝트의 ARM resource ID를 복사합니다.
4. `.env`의 `FOUNDRY_PROJECT_RESOURCE_ID`에 넣습니다.
5. 프로젝트에 `gpt-5.4` 배포가 있는지 확인합니다.
6. 다른 배포 이름을 쓰는 경우 `.env`의 `FOUNDRY_MODEL_DEPLOYMENT_NAME`을 실제 배포 이름으로 바꿉니다.
7. 로컬 터미널에서 `az login`을 실행하거나(Windows는 PowerShell, macOS/Linux는 zsh·bash) VS Code Azure Account에 로그인합니다.

```bash
FOUNDRY_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
FOUNDRY_PROJECT_RESOURCE_ID=/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.CognitiveServices/accounts/<account-name>/projects/<project-name>
FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-5.4
FOUNDRY_KEEP_AGENT=false
```

### 8.4.2 Azure AI Search 서비스 준비

8.1과 8.2 모두 Azure AI Search 서비스가 필요합니다. 8.1은 Search index를 만들고 문서를 업로드하는 데 사용하고, 8.2는 Knowledge base MCP endpoint를 구성하는 데 Search endpoint를 사용합니다.

Azure Portal에서 다음을 확인합니다.

1. Azure AI Search 서비스를 만듭니다. 이미 있으면 기존 서비스를 사용해도 됩니다.
2. Search service의 URL을 복사합니다. 형식은 `https://<search-service>.search.windows.net`입니다.
3. **Keys** 메뉴에서 admin key 또는 query key를 복사합니다.
4. `.env`에 `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_SERVICE_NAME`, `AZURE_SEARCH_API_KEY`를 넣습니다.

```bash
AZURE_SEARCH_ENDPOINT=https://<search-service>.search.windows.net
AZURE_SEARCH_SERVICE_NAME=<search-service>
AZURE_SEARCH_API_KEY=<search-admin-or-query-key>
```

`AZURE_SEARCH_ENDPOINT`에 Azure OpenAI endpoint나 Cognitive Services endpoint를 넣으면 안 됩니다. 반드시 `.search.windows.net`으로 끝나는 Search endpoint를 사용합니다.

### 8.4.3 8.1용 Foundry Search connection 준비

8.1은 코드가 직접 `foundry-agent-rag-index` index를 만들고, Foundry Agent의 `AzureAISearchTool`에 연결합니다. 따라서 Foundry project에 Azure AI Search connection이 있으면 가장 안정적으로 실행됩니다.

Foundry 포털에서 다음 순서로 확인합니다.

1. Foundry project를 엽니다.
2. **관리/Management** 또는 **Project settings**의 **Connections** 메뉴를 엽니다.
3. Azure AI Search 리소스 connection을 추가합니다.
4. connection 이름을 복사해 `.env`의 `FOUNDRY_AI_SEARCH_CONNECTION_NAME`에 넣습니다.
5. Search index 이름은 기본값 `foundry-agent-rag-index`를 그대로 사용합니다.

```bash
AZURE_SEARCH_INDEX_NAME=foundry-agent-rag-index
FOUNDRY_AI_SEARCH_CONNECTION_NAME=<foundry-search-connection-name>
FOUNDRY_AI_SEARCH_QUERY_TYPE=simple
```

8.1이 만드는 `foundry-agent-rag-index`에는 `semantic-config`라는 semantic configuration도 함께 추가됩니다. 나중에 이 index를 Knowledge base source로 선택할 때 semantic configuration 경고가 줄어듭니다.

### 8.4.4 8.2용 Knowledge base 수동 생성

8.2는 Knowledge base를 코드로 만들지 않습니다. 학습 전에 포털에서 Knowledge base를 직접 만든 뒤, 그 Knowledge base의 MCP endpoint를 Foundry Agent의 `MCPTool`로 연결합니다. 이렇게 하면 agent 설정 화면에서 Knowledge base 연결을 확인할 수 있고, agent가 필요할 때 `knowledge_base_retrieve` 도구를 호출해 답변합니다.

Knowledge base를 만들 때는 먼저 **Knowledge source**를 선택합니다. 포털 화면에서는 다음 종류를 사용할 수 있습니다.

| Knowledge source | 설명 | 이 hands-on에서의 사용 여부 |
| --- | --- | --- |
| Search index (Indexed) | 기존 Azure AI Search index에서 데이터를 가져옵니다. | 권장. 8.1이 만든 `foundry-agent-rag-index`를 선택합니다. |
| Azure blob (Indexed) | Azure Blob Storage 또는 Azure Data Lake Storage Gen2의 파일을 읽어 index/indexer/datasource를 만듭니다. | 선택. PDF, Word, txt 파일을 Storage에 올려 두는 교육에는 적합합니다. |
| Microsoft OneLake (Indexed) | Microsoft OneLake lakehouse 데이터를 수집해 Search index로 저장합니다. | 선택. Fabric/OneLake 기반 데이터가 있을 때 사용합니다. |
| Microsoft SharePoint (Indexed) | SharePoint 문서를 Azure AI Search로 index화합니다. | 선택. 사내 문서 포털을 검색 대상으로 삼을 때 사용합니다. |
| Microsoft SharePoint (Remote) | SharePoint 콘텐츠를 실시간으로 조회합니다. | 선택. 별도 governance와 권한 확인이 필요합니다. |
| Web (Remote) | Bing 기반 공개 웹 콘텐츠를 실시간으로 조회합니다. | 선택. 공개 웹 grounding이 필요한 경우에만 사용합니다. |

이 hands-on에서는 초보자 실행 안정성을 위해 **Search index (Indexed)**를 기준으로 설명합니다. 8.1이 로컬 회사 정책 파일을 Azure AI Search index로 올려 주고, 8.2에서는 그 index를 source로 만든 Knowledge base를 조회합니다.

현재 소스가 파일을 처리하는 방식은 다음과 같습니다.

1. 8.1이 [Chapter4_Agent_Patterns/company_policy.txt](../Chapter4_Agent_Patterns/company_policy.txt)를 직접 읽습니다.
2. 파일 내용을 작은 chunk로 나눕니다.
3. 각 chunk에 대해 embedding vector를 생성합니다.
4. Azure AI Search에 `foundry-agent-rag-index` index를 만들거나 업데이트합니다.
5. 각 chunk를 `content`, `source`, `chunk_index`, `content_vector` 필드가 있는 문서로 업로드합니다.
6. Knowledge base 생성 화면에서는 이 index를 **Search index (Indexed)** source로 선택합니다.

즉, 현재 소스는 포털의 “파일 업로드” 버튼으로 HR 파일을 올리는 방식이 아닙니다. Python 코드가 로컬 HR/회사 정책 파일을 읽어서 직접 Azure AI Search index로 만들어 주는 방식입니다. 포털에서 파일을 직접 올리는 흐름을 실습하고 싶다면, Knowledge source에서 **Azure blob (Indexed)**를 선택하고 Storage container에 파일을 올린 뒤 Knowledge base를 만들면 됩니다.

권장 흐름은 다음입니다.

1. 8.1을 먼저 실행해 `foundry-agent-rag-index`를 만들거나, 이미 준비된 Azure AI Search index를 사용합니다.
2. Foundry 포털에서 실습 project를 엽니다.
3. **Knowledge** 또는 **Foundry IQ** 메뉴를 엽니다.
4. **Knowledge bases**를 선택하고 새 Knowledge base를 만듭니다.
5. Knowledge base 이름을 정합니다. 예: `knowledgebase12`
6. Source로 Azure AI Search index를 선택합니다.
7. 8.1에서 만든 index를 쓰는 경우 `foundry-agent-rag-index`를 선택합니다.
8. content/text 필드로 문서 본문 필드를 선택합니다. 8.1 index 기준으로는 `content` 필드입니다.
9. title/source로 쓸 필드가 필요하면 `source` 필드를 선택합니다.
10. 생성이 끝난 뒤 상태가 active 또는 ready가 될 때까지 기다립니다.
11. Knowledge base 이름을 `.env`의 `FOUNDRY_KNOWLEDGE_BASE_NAME`에 넣습니다.
12. Knowledge base MCP endpoint를 확인합니다. 형식은 다음과 같습니다.

    ```text
    https://<search-service>.search.windows.net/knowledgebases/<knowledge-base-name>/mcp?api-version=2025-11-01-preview
    ```

13. connection 이름을 예를 들어 `chapter-8-2-kb-mcp-connection`으로 정하고 `.env`의 `FOUNDRY_KB_MCP_CONNECTION_NAME`에 넣습니다.
14. 포털에서 RemoteTool/MCP connection 메뉴가 보이지 않아도 괜찮습니다. 8.2 코드가 `FOUNDRY_PROJECT_RESOURCE_ID`를 사용해 ARM REST API로 connection을 생성하거나 업데이트합니다.
15. 인증은 project managed identity 기반 연결을 사용합니다. project managed identity가 Search service/Knowledge base를 조회할 권한이 있어야 합니다.

```bash
FOUNDRY_KNOWLEDGE_BASE_NAME=<knowledge-base-name>
FOUNDRY_KB_MCP_CONNECTION_NAME=chapter-8-2-kb-mcp-connection
FOUNDRY_KB_AGENT_NAME=chapter-8-2-knowledge-base-agent
FOUNDRY_KB_TEST_QUESTION=회사 정책에서 재택근무와 보안 관련 핵심 규칙을 요약해 주세요.
```

현재 실습 환경 예시처럼 Knowledge base 이름이 `knowledgebase12`이면 다음처럼 설정합니다.

```bash
FOUNDRY_KNOWLEDGE_BASE_NAME=knowledgebase12
```

8.2는 `AZURE_SEARCH_ENDPOINT`와 `FOUNDRY_KNOWLEDGE_BASE_NAME`으로 Knowledge base MCP endpoint를 만들고, `FOUNDRY_PROJECT_RESOURCE_ID`로 RemoteTool/MCP project connection을 생성하거나 업데이트한 뒤, `FOUNDRY_KB_MCP_CONNECTION_NAME`을 `MCPTool(project_connection_id=...)`에 넣어 agent definition에 연결합니다. 이 방식은 retrieve 결과를 user message에 직접 붙이는 방식이 아니라, agent가 연결된 Knowledge base 도구를 호출하는 방식입니다.

### 8.4.5 8.3용 MCP 서버 코드 연결

8.3은 Microsoft Learn MCP Server를 Foundry Agent의 `MCPTool`로 코드에서 연결합니다. 포털에서 수동으로 tool을 추가하는 흐름도 가능하지만, 이 hands-on의 8.3 파일은 Python 코드가 agent version을 만들 때 MCP server URL을 tool 정의에 포함합니다.

Microsoft Learn MCP Server는 공개 원격 MCP 서버입니다.

```text
https://learn.microsoft.com/api/mcp
```

이 endpoint는 브라우저에서 직접 여는 URL이 아니라, MCP client가 streaming HTTP로 호출하는 서버 endpoint입니다. 브라우저에서 열면 `405 Method Not Allowed`가 보일 수 있습니다.

코드 실행 흐름은 다음입니다.

1. `.env`에서 `FOUNDRY_DEMO_MCP_SERVER_URL`을 읽습니다.
2. `MCPTool(server_url=..., allowed_tools=..., require_approval="never")`를 만듭니다.
3. `PromptAgentDefinition`의 `tools`에 MCP tool을 넣습니다.
4. Foundry Agent Service에 agent version을 생성합니다.
5. `agent_reference`로 질문을 보내면 agent가 필요할 때 Microsoft Learn MCP 도구를 호출합니다.

포털에서 같은 내용을 수동으로 만들고 싶다면 다음 위치에서 확인합니다.

1. Foundry project를 엽니다.
2. **Build > Agents**에서 agent를 만들거나 기존 agent를 엽니다.
3. **Tools > Add > Add new tool**을 선택합니다.
4. **Custom**을 선택하고 **MCP**를 선택한 뒤 만듭니다.
5. 이름에는 예를 들어 `microsoft-learn-mcp`를 입력합니다.
6. endpoint에는 `https://learn.microsoft.com/api/mcp`를 입력합니다.
7. 인증 방식은 **Unauthenticated** 또는 인증 없음으로 선택합니다.
8. 연결 후 agent의 Tools 목록에 MCP 도구가 보이는지 확인합니다.

이렇게 연결하면 Foundry 포털의 해당 agent 설정 화면에서 MCP tool 연결이 보입니다. 저장한 뒤 agent를 다시 열어도 Tools 목록에서 확인할 수 있습니다. 다만 이것은 Azure AI Search 같은 리소스 connection과 성격이 다르므로, 모든 환경에서 Project settings의 일반 Connections 목록에 동일한 형태로 보인다고 기대하면 안 됩니다. 핵심 확인 위치는 agent의 Tools 영역입니다.

Microsoft Learn MCP Server가 제공하는 대표 도구는 다음과 같습니다.

- `microsoft_docs_search`: Microsoft 공식 문서 검색
- `microsoft_docs_fetch`: 문서 본문 가져오기
- `microsoft_code_sample_search`: 코드 샘플 검색

8.3 스크립트가 사용하는 값은 다음입니다.

```bash
FOUNDRY_DEMO_MCP_CONNECTION_NAME=microsoft-learn-mcp
FOUNDRY_DEMO_MCP_SERVER_URL=https://learn.microsoft.com/api/mcp
FOUNDRY_DEMO_MCP_AGENT_NAME=chapter-8-3-learn-mcp-agent
FOUNDRY_DEMO_MCP_ALLOWED_TOOLS=microsoft_docs_search,microsoft_docs_fetch,microsoft_code_sample_search
FOUNDRY_DEMO_MCP_TEST_QUESTION=How can I create a Microsoft Foundry project using Azure CLI?
```

### 8.4.6 8.4용 Application Insights 수동 생성

8.4에서 Foundry monitoring과 trace를 함께 보려면 Application Insights를 먼저 수동으로 만드는 방식을 권장합니다. connection string이 없으면 리소스를 만들지 않고 콘솔 trace로 계속 실행하므로, 포털 monitoring 화면에 자세한 telemetry가 보이지 않을 수 있습니다.

중요한 차이가 있습니다. `.env`의 `FOUNDRY_APPLICATIONINSIGHTS_CONNECTION_STRING`은 로컬 Python 코드가 OpenTelemetry span을 Azure Monitor로 보내는 데 사용합니다. Foundry 포털의 agent **추적** 탭에 서비스 실행 데이터가 보이려면, 포털에서 해당 project 또는 agent에 Application Insights 연결도 활성화되어 있어야 합니다. 화면에 “Application Insights가 활성화되면 생성되는 데이터입니다” 문구가 보이면 아직 포털 쪽 연결이 활성화되지 않았거나 데이터 반영 전입니다.

Azure Portal에서 다음 순서로 만듭니다.

1. **Application Insights** 리소스를 새로 만듭니다.
2. 같은 region과 resource group을 사용합니다. 예제에서는 `eastus2`, `foundry-hands-on-rg`를 사용합니다.
3. Workspace-based Application Insights를 선택하고, Log Analytics workspace를 새로 만들거나 기존 것을 연결합니다.
4. 생성 후 Application Insights 리소스의 **Connection String** 값을 복사합니다.
5. `.env`의 `FOUNDRY_APPLICATIONINSIGHTS_CONNECTION_STRING`에 붙여 넣습니다.
6. Foundry 포털에서 agent의 monitoring/trace 화면에 연결 배너가 보이면 같은 Application Insights 리소스를 선택해 활성화합니다.
7. 8.1, 8.2 또는 8.3을 다시 실행한 뒤 몇 분 기다리고 날짜 범위를 7일로 맞춥니다.

8.1은 실행 시 `FOUNDRY_APPLICATIONINSIGHTS_CONNECTION_STRING`의 InstrumentationKey와 일치하는 Application Insights 리소스를 현재 Azure CLI 구독에서 찾고, 연결된 Log Analytics workspace가 실제 존재하는지도 확인합니다. workspace가 삭제되었거나 다른 구독에 있으면 Foundry trace의 개별 응답은 보이더라도 monitoring 집계가 0으로 보일 수 있습니다.

```bash
FOUNDRY_APPLICATIONINSIGHTS_CONNECTION_STRING=<application-insights-connection-string>
FOUNDRY_APPLICATIONINSIGHTS_AUTO_CREATE=false
```

## 8.5 필요한 `.env` 값

공통 값은 다음과 같습니다.

```bash
FOUNDRY_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
FOUNDRY_PROJECT_RESOURCE_ID=/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.CognitiveServices/accounts/<account-name>/projects/<project-name>
FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-5.4
FOUNDRY_KEEP_AGENT=false
```

8.1과 8.2 모두 Azure AI Search 값을 사용합니다. 8.1은 index 생성/업로드에 사용하고, 8.2는 Knowledge base MCP endpoint 구성에 사용합니다.

```bash
AZURE_SEARCH_ENDPOINT=https://<search-service>.search.windows.net
AZURE_SEARCH_SERVICE_NAME=<search-service>
AZURE_SEARCH_API_KEY=<search-admin-or-query-key>
```

8.1에서 직접 만드는 Search index와 Foundry Search tool 연결 값입니다.

```bash
AZURE_SEARCH_INDEX_NAME=foundry-agent-rag-index
FOUNDRY_AI_SEARCH_CONNECTION_NAME=<foundry-search-connection-name>
FOUNDRY_AI_SEARCH_QUERY_TYPE=simple
```

8.1이 만드는 `foundry-agent-rag-index`에는 `semantic-config`라는 semantic configuration도 함께 추가됩니다. Search 서비스에서 semantic ranker가 활성화되어 있으면 `FOUNDRY_AI_SEARCH_QUERY_TYPE=semantic`으로 바꿔 semantic 검색 실습도 할 수 있습니다. 기본값은 초보자 실행 안정성을 위해 `simple`입니다.

8.2는 Foundry 포털 또는 Azure Portal에서 먼저 Knowledge base를 만든 뒤 실행합니다. 그 MCP endpoint를 가리키는 RemoteTool/MCP project connection은 코드가 생성하거나 업데이트합니다. 이 경로는 embedding 생성, vector field, index schema를 코드에서 직접 다루지 않습니다.

```bash
FOUNDRY_KNOWLEDGE_BASE_NAME=<knowledge-base-name>
FOUNDRY_KB_MCP_CONNECTION_NAME=chapter-8-2-kb-mcp-connection
FOUNDRY_KB_AGENT_NAME=chapter-8-2-knowledge-base-agent
FOUNDRY_KB_TEST_QUESTION=회사 정책에서 재택근무와 보안 관련 핵심 규칙을 요약해 주세요.
```

8.2 실행 흐름은 다음과 같습니다.

1. `AZURE_SEARCH_ENDPOINT`와 `FOUNDRY_KNOWLEDGE_BASE_NAME`으로 Knowledge base MCP endpoint를 구성합니다.
2. `FOUNDRY_PROJECT_RESOURCE_ID`와 `FOUNDRY_KB_MCP_CONNECTION_NAME`으로 RemoteTool/MCP project connection을 생성하거나 업데이트합니다.
3. `FOUNDRY_KB_MCP_CONNECTION_NAME`을 `MCPTool(project_connection_id=...)`에 넣습니다.
4. `allowed_tools=["knowledge_base_retrieve"]`인 MCP tool을 Foundry Agent definition에 추가합니다.
5. agent가 질문을 받으면 연결된 Knowledge base tool을 호출해 근거를 검색하고 답변합니다.

이 방식은 포털의 agent 설정에서 Knowledge/MCP tool 연결을 확인하기 위한 경로입니다. connection이 없거나 project managed identity 권한이 부족하면 agent 생성 또는 도구 호출 단계에서 오류가 납니다.

8.3은 Microsoft Learn MCP 서버를 `MCPTool`로 agent에 붙여 실제 질문을 실행합니다.

```bash
FOUNDRY_DEMO_MCP_CONNECTION_NAME=microsoft-learn-mcp
FOUNDRY_DEMO_MCP_SERVER_URL=https://learn.microsoft.com/api/mcp
FOUNDRY_DEMO_MCP_AGENT_NAME=chapter-8-3-learn-mcp-agent
FOUNDRY_DEMO_MCP_ALLOWED_TOOLS=microsoft_docs_search,microsoft_docs_fetch,microsoft_code_sample_search
FOUNDRY_DEMO_MCP_TEST_QUESTION=How can I create a Microsoft Foundry project using Azure CLI?
```

Knowledge base도 MCP endpoint를 제공합니다. 8.2는 이 endpoint를 사용합니다.

```text
https://<search-service>.search.windows.net/knowledgebases/<knowledge-base-name>/mcp?api-version=<api-version>
```

Foundry Agent Service에서 이 MCP endpoint를 agent tool로 붙이려면 project connection이 인증을 안전하게 처리해야 합니다. 8.2는 `.env`의 `FOUNDRY_KB_MCP_CONNECTION_NAME` 값을 `MCPTool(project_connection_id=...)`에 넣어 이 연결을 사용합니다.

## 8.6 Application Insights와 Monitoring

Application Insights 수동 생성 절차는 8.4.6의 사전 준비 항목을 따릅니다. connection string을 `.env`에 넣으면 8.1, 8.2, 8.3 실행 trace를 Azure Monitor로 보낼 수 있고, 8.4에서 Foundry 포털 monitoring 화면과 함께 확인할 수 있습니다.

connection string이 없으면 리소스를 만들지 않고 콘솔 trace로 계속 실행합니다. 이 경우 Python 실습은 진행되지만, Azure Portal의 Application Insights에는 자세한 telemetry가 보이지 않을 수 있습니다.

```bash
FOUNDRY_APPLICATIONINSIGHTS_CONNECTION_STRING=<application-insights-connection-string>
FOUNDRY_APPLICATIONINSIGHTS_AUTO_CREATE=false
```

교육 실습에서는 자동 생성 대신 포털에서 수동 생성한 뒤 connection string을 붙여 넣는 흐름을 사용합니다. `FOUNDRY_APPLICATIONINSIGHTS_AUTO_CREATE`는 기본값 `false`로 유지합니다.

### 8.6.1 Monitoring 데이터가 0으로 보일 때

8.1은 시작할 때 다음 항목을 출력합니다.

```text
[Application Insights workspace 확인]
- Application Insights: <name> (<resource-group>, <location>)
- Log Analytics workspace: <name> (<resource-group>, <location>)
```

다음과 같은 경고가 나오면 Application Insights는 있지만 연결된 Log Analytics workspace가 없거나 삭제된 상태입니다.

```text
Log Analytics workspace: 찾을 수 없음
App Insights가 삭제된 workspace를 바라보면 Foundry monitoring 데이터가 0으로 보일 수 있습니다.
```

이 경우 새 workspace를 만들고 Application Insights의 `WorkspaceResourceId`를 갱신합니다. 예시는 `ystest8` Application Insights와 `ys-kim-sg` 리소스 그룹 기준입니다.

Windows (PowerShell):

```powershell
$resourceGroup = "ys-kim-sg"
$location = "canadacentral"
$appInsightsName = "ystest8"
$workspaceName = "law-ystest8"

az monitor log-analytics workspace create `
  --resource-group $resourceGroup `
  --workspace-name $workspaceName `
  --location $location

$workspaceId = az monitor log-analytics workspace show `
  --resource-group $resourceGroup `
  --workspace-name $workspaceName `
  --query id `
  --output tsv

az resource update `
  --resource-group $resourceGroup `
  --name $appInsightsName `
  --resource-type microsoft.insights/components `
  --set properties.WorkspaceResourceId=$workspaceId
```

macOS / Linux (bash·zsh):

```bash
RESOURCE_GROUP="ys-kim-sg"
LOCATION="canadacentral"
APP_INSIGHTS_NAME="ystest8"
WORKSPACE_NAME="law-ystest8"

az monitor log-analytics workspace create \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$WORKSPACE_NAME" \
  --location "$LOCATION"

WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$WORKSPACE_NAME" \
  --query id \
  --output tsv)

az resource update \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_INSIGHTS_NAME" \
  --resource-type microsoft.insights/components \
  --set properties.WorkspaceResourceId="$WORKSPACE_ID"
```

재연결 후 8.1 또는 8.2를 다시 실행하고 몇 분 기다립니다. Azure Monitor에서 telemetry 유입을 직접 확인하려면 다음 쿼리를 사용할 수 있습니다.

Windows (PowerShell):

```powershell
$customerId = az monitor log-analytics workspace show `
  --resource-group $resourceGroup `
  --workspace-name $workspaceName `
  --query customerId `
  --output tsv

$query = 'union withsource=TableName isfuzzy=true AppTraces, AppRequests, AppDependencies, AppExceptions | where TimeGenerated > ago(30m) | summarize Count=count(), Latest=max(TimeGenerated) by TableName | order by Count desc'

az monitor log-analytics query `
  -w $customerId `
  --analytics-query $query `
  --output table
```

macOS / Linux (bash·zsh):

```bash
CUSTOMER_ID=$(az monitor log-analytics workspace show \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$WORKSPACE_NAME" \
  --query customerId \
  --output tsv)

QUERY='union withsource=TableName isfuzzy=true AppTraces, AppRequests, AppDependencies, AppExceptions | where TimeGenerated > ago(30m) | summarize Count=count(), Latest=max(TimeGenerated) by TableName | order by Count desc'

az monitor log-analytics query \
  -w "$CUSTOMER_ID" \
  --analytics-query "$QUERY" \
  --output table
```

## 8.7 실행

직접 Azure AI Search index와 Foundry Search tool을 연결합니다.

```bash
uv run Chapter8_Foundry_Agents/8.1_create_and_run_foundry_agent.py
```

Knowledge base MCPTool을 Foundry Agent에 연결해 질의응답합니다.

```bash
uv run Chapter8_Foundry_Agents/8.2_create_foundry_agent_with_knowledge_base.py
```

Microsoft Learn MCP 서버를 Foundry Agent tool로 코드 연결하고 질문을 실행합니다.

```bash
uv run Chapter8_Foundry_Agents/8.3_create_foundry_agent_with_mcp.py
```

Foundry 포털 monitoring 화면을 확인합니다.

```bash
uv run Chapter8_Foundry_Agents/8.4_foundry_agent_monitoring.py
```

기본값은 실행 후 agent version을 삭제합니다. 포털에서 생성된 agent version을 직접 확인하고 싶으면 `.env`에서 `FOUNDRY_KEEP_AGENT=true`로 바꾼 뒤 실행하고, 실습 후 포털에서 직접 정리합니다.

## 8.8 8.1 직접 Search tool과 8.2 Knowledge base MCPTool의 차이

| 구분 | 8.1 직접 Azure AI Search tool | 8.2 Knowledge base MCPTool |
| --- | --- | --- |
| 연결 방식 | `AzureAISearchTool`과 `AzureAISearchToolResource`를 agent에 직접 연결 | Knowledge base MCP endpoint를 `MCPTool`로 agent definition에 연결 |
| 지식 준비 | 스크립트가 chunk/vector를 만들고 Azure AI Search index에 업로드 | 포털에서 만든 Knowledge base 사용 |
| 좋은 용도 | RAG 내부 구조, index schema, embedding 흐름 이해 | 포털에서 agent의 Knowledge/MCP tool 연결 확인, embedding 코드 제거 |
| 실패 시 확인 | Search endpoint, key, project connection, query type | Knowledge base 이름, Search endpoint, RemoteTool/MCP connection 이름, managed identity 권한 |

## 8.9 6장 로컬 MCP 스타일 서버와 8장 Foundry MCP tool의 차이

| 구분 | 6장 로컬 MCP 스타일 서버 | 8장 Foundry MCP tool |
| --- | --- | --- |
| 실행 위치 | 내 PC의 FastAPI/Flask 서버와 로컬 client | Microsoft Foundry Agent Service runtime |
| 호출 주체 | 예제 client 코드가 HTTP endpoint를 직접 호출 | Foundry agent가 등록된 원격 MCP server를 필요할 때 호출 |
| 인증/연결 | 로컬 URL 중심, 포털 project connection 없음 | `FOUNDRY_PROJECT_ENDPOINT`, Azure credential, 필요 시 project connection 사용 |
| 학습 목적 | 도구 서버의 endpoint, payload, session/RAG 분리 개념 학습 | 실제 Foundry agent version에 원격 MCP 도구를 붙이는 운영 구조 학습 |

6장의 서버 파일을 실행했다고 해서 자동으로 Foundry 포털에 MCP connection이 등록되지는 않습니다. 8.3에서 포털의 원격 MCP 연결 위치를 확인한 뒤, 필요할 때 별도 MCP 서버나 Knowledge base MCP endpoint를 project connection으로 등록합니다.

## 8.10 실행 결과를 볼 때 확인할 점

터미널 출력에서 다음 순서를 확인합니다.

1. 8.1 실행 시 회사 정책 문서가 chunk로 나뉘고 Search index에 업로드되는지 확인합니다.
2. 8.1 실행 시 Foundry project connection에서 Azure AI Search connection을 찾는지 확인합니다.
3. 8.2 실행 시 Knowledge base 이름과 질문이 출력되는지 확인합니다.
4. 8.2 실행 시 retrieve context가 출력된 뒤 Foundry agent response가 생성되는지 확인합니다.
5. 8.3 실행 후 Foundry 포털의 원격 MCP 연결 메뉴와 입력값을 확인합니다.
6. 8.4 실행 후 Foundry 포털에서 agent monitoring 탭의 운영 메트릭, 실행 및 토큰 메트릭, 평가, App Insights 연결 배너를 확인합니다.
7. 추적 탭에 데이터가 없고 “Application Insights가 활성화되면 생성되는 데이터입니다” 문구가 보이면 포털에서 App Insights 연결을 활성화한 뒤 다시 실행합니다.
8. `FOUNDRY_KEEP_AGENT=false`이면 생성한 agent version이 정리되는지 확인합니다.

## 8.11 사전 준비 누락 점검표

실행 전 아래 항목을 빠르게 확인합니다.

- `FOUNDRY_OPENAI_ENDPOINT`, `FOUNDRY_API_KEY`, `FOUNDRY_MODEL_DEPLOYMENT_NAME`이 기본 모델 호출에 맞게 설정되어 있습니다.
- `FOUNDRY_REASONING_EFFORT=low`로 유지되어 있습니다.
- 8.1/8.2/8.3을 실행하기 전에 `FOUNDRY_PROJECT_ENDPOINT`가 설정되어 있습니다.
- 터미널에서 `az login`을 완료했거나(Windows는 PowerShell, macOS/Linux는 zsh·bash) VS Code Azure Account에 로그인되어 있습니다.
- `AZURE_SEARCH_ENDPOINT`가 `https://<search-service>.search.windows.net` 형식입니다.
- `AZURE_SEARCH_API_KEY`가 현재 Search 서비스의 유효한 key입니다.
- 8.1을 실행하려면 Foundry project에 Azure AI Search connection이 준비되어 있고, 이름이 `FOUNDRY_AI_SEARCH_CONNECTION_NAME`에 들어 있습니다.
- 8.2를 실행하려면 Knowledge base가 active/ready 상태이고, 이름이 `FOUNDRY_KNOWLEDGE_BASE_NAME`에 들어 있습니다.
- 8.4에서 monitoring을 보려면 Application Insights connection string이 `FOUNDRY_APPLICATIONINSIGHTS_CONNECTION_STRING`에 들어 있습니다.
- Foundry 포털의 agent 추적 탭을 보려면 포털에서도 같은 Application Insights 리소스를 연결/활성화합니다.
- agent version을 포털에서 확인하려면 `FOUNDRY_KEEP_AGENT=true`로 설정합니다.

## 8.12 마무리 점검

8장은 이 hands-on의 마지막 Foundry Agent Service 실습입니다. 여기까지 오면 Foundry project endpoint, project connection, agent version, tool resource, Knowledge base, MCPTool, Application Insights monitoring의 역할을 함께 설명할 수 있어야 합니다.
