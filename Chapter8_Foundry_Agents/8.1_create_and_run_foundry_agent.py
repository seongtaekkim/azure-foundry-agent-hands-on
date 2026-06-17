# Run: uv run Chapter8_Foundry_Agents/8.1_create_and_run_foundry_agent.py
# 학습 포인트: Foundry Agent를 생성하고 RAG chunk/vector 인덱스를 연결해 질의응답합니다.
# 초보자 읽기: 정책 문서를 chunk와 vector로 준비하고 Foundry agent에 Search tool 또는 fallback context를 연결하는 end-to-end 흐름을 봅니다.
import os
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AISearchIndexResource,
    AzureAISearchQueryType,
    AzureAISearchTool,
    AzureAISearchToolResource,
    PromptAgentDefinition,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from dotenv import load_dotenv

import _bootstrap  # noqa: F401
from foundry_hands_on.client import _output_text
from foundry_hands_on.config import get_model_deployment_name, get_project_api_key, get_project_credential, get_project_endpoint, get_ssl_verify
from foundry_hands_on.rag import chunk_text, embed_texts
from foundry_hands_on.tracing import foundry_span

load_dotenv()


def _run_az(args: list[str]) -> str:
    az_command = shutil.which("az") or shutil.which("az.cmd") or "az"
    completed = subprocess.run(
        [az_command, *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _az_show(args: list[str]) -> str | None:
    try:
        return _run_az(args)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def _connection_string_value(connection_string: str, key: str) -> str | None:
    prefix = f"{key}="
    for part in connection_string.split(";"):
        if part.startswith(prefix):
            value = part[len(prefix) :].strip()
            return value or None
    return None


def check_application_insights_workspace() -> None:
    connection_string = (
        os.getenv("FOUNDRY_APPLICATIONINSIGHTS_CONNECTION_STRING")
        or os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    )
    if not connection_string:
        return

    instrumentation_key = _connection_string_value(connection_string, "InstrumentationKey")
    if not instrumentation_key:
        print("Application Insights connection string에서 InstrumentationKey를 찾지 못했습니다.")
        return

    try:
        raw_components = _run_az(
            [
                "resource",
                "list",
                "--resource-type",
                "microsoft.insights/components",
                "--query",
                "[].{name:name,resourceGroup:resourceGroup,id:id}",
                "--output",
                "json",
            ]
        )
    except FileNotFoundError:
        print("Azure CLI az를 찾지 못해 Application Insights workspace 확인을 건너뜁니다.")
        return
    except subprocess.CalledProcessError as exc:
        print("Application Insights 리소스 조회를 완료하지 못해 workspace 확인을 건너뜁니다.")
        if exc.stderr:
            print(exc.stderr.strip())
        return

    components = json.loads(raw_components or "[]")
    component = None
    for item in components:
        component_detail = _az_show(
            [
                "resource",
                "show",
                "--ids",
                item["id"],
                "--query",
                "{name:name,resourceGroup:resourceGroup,location:location,"
                "instrumentationKey:properties.InstrumentationKey,"
                "workspaceResourceId:properties.WorkspaceResourceId}",
                "--output",
                "json",
            ]
        )
        if not component_detail:
            continue
        candidate = json.loads(component_detail)
        if candidate.get("instrumentationKey") == instrumentation_key:
            component = candidate
            break
    if not component:
        print(
            "Application Insights connection string과 일치하는 리소스를 현재 Azure CLI 구독에서 찾지 못했습니다. "
            "az account show로 구독을 확인하세요."
        )
        return

    print("\n[Application Insights workspace 확인]")
    print(f"- Application Insights: {component['name']} ({component['resourceGroup']}, {component['location']})")
    workspace_resource_id = component.get("workspaceResourceId")
    if not workspace_resource_id:
        print("- Log Analytics workspace: 연결되지 않음")
        print("  Foundry monitoring 집계를 보려면 workspace-based Application Insights 연결이 필요합니다.")
        return

    workspace = _az_show(
        [
            "resource",
            "show",
            "--ids",
            workspace_resource_id,
            "--query",
            "{name:name,resourceGroup:resourceGroup,location:location}",
            "--output",
            "json",
        ]
    )
    if not workspace:
        print(f"- Log Analytics workspace: 찾을 수 없음 ({workspace_resource_id})")
        print("  App Insights가 삭제된 workspace를 바라보면 Foundry monitoring 데이터가 0으로 보일 수 있습니다.")
        print("  새 workspace를 만든 뒤 Application Insights의 WorkspaceResourceId를 갱신하세요.")
        return

    workspace_info = json.loads(workspace)
    print(
        "- Log Analytics workspace: "
        f"{workspace_info['name']} ({workspace_info['resourceGroup']}, {workspace_info['location']})"
    )


def ensure_application_insights() -> None:
    if os.getenv("FOUNDRY_APPLICATIONINSIGHTS_CONNECTION_STRING") or os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        print("Application Insights connection string이 이미 설정되어 있어 기존 연결을 사용합니다.")
        check_application_insights_workspace()
        return

    auto_create = os.getenv("FOUNDRY_APPLICATIONINSIGHTS_AUTO_CREATE", "false").lower() == "true"
    if not auto_create:
        print(
            "\nApplication Insights 자동 생성은 꺼져 있습니다. "
            "수동 생성한 리소스를 사용하려면 .env에 FOUNDRY_APPLICATIONINSIGHTS_CONNECTION_STRING을 설정하세요."
        )
        return

    resource_group = os.getenv("AZURE_RESOURCE_GROUP") or os.getenv("FOUNDRY_RESOURCE_GROUP")
    if not resource_group:
        print(
            "\nApplication Insights 자동 생성은 건너뜁니다. "
            "생성하려면 .env에 AZURE_RESOURCE_GROUP=<resource-group>을 설정하세요."
        )
        return

    location = os.getenv("AZURE_LOCATION", "eastus2")
    workspace_name = os.getenv("FOUNDRY_LOG_ANALYTICS_WORKSPACE_NAME", "log-foundry-hands-on")
    app_insights_name = os.getenv("FOUNDRY_APPLICATIONINSIGHTS_NAME", "appi-foundry-hands-on")

    print("\n[Application Insights 자동 준비]")
    print(f"- resource group: {resource_group}")
    print(f"- location: {location}")
    print(f"- Log Analytics workspace: {workspace_name} (SKU: PerGB2018, 사용량 기반)")
    print(f"- Application Insights: {app_insights_name}")

    try:
        workspace_id = _az_show(
            [
                "monitor",
                "log-analytics",
                "workspace",
                "show",
                "--resource-group",
                resource_group,
                "--workspace-name",
                workspace_name,
                "--query",
                "id",
                "--output",
                "tsv",
            ]
        )
        if not workspace_id:
            workspace_id = _run_az(
                [
                    "monitor",
                    "log-analytics",
                    "workspace",
                    "create",
                    "--resource-group",
                    resource_group,
                    "--workspace-name",
                    workspace_name,
                    "--location",
                    location,
                    "--sku",
                    "PerGB2018",
                    "--query",
                    "id",
                    "--output",
                    "tsv",
                ]
            )

        connection_string = _az_show(
            [
                "monitor",
                "app-insights",
                "component",
                "show",
                "--resource-group",
                resource_group,
                "--app",
                app_insights_name,
                "--query",
                "connectionString",
                "--output",
                "tsv",
            ]
        )
        if not connection_string:
            connection_string = _run_az(
                [
                    "monitor",
                    "app-insights",
                    "component",
                    "create",
                    "--resource-group",
                    resource_group,
                    "--app",
                    app_insights_name,
                    "--location",
                    location,
                    "--kind",
                    "web",
                    "--application-type",
                    "web",
                    "--workspace",
                    workspace_id,
                    "--query",
                    "connectionString",
                    "--output",
                    "tsv",
                ]
            )

        os.environ["FOUNDRY_APPLICATIONINSIGHTS_CONNECTION_STRING"] = connection_string
        os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = connection_string
        print("Application Insights connection string을 현재 실행에 연결했습니다.")
        check_application_insights_workspace()
    except FileNotFoundError:
        print("Azure CLI az를 찾지 못해 Application Insights 자동 생성을 건너뜁니다.")
    except subprocess.CalledProcessError as exc:
        print("Application Insights 자동 생성 또는 조회를 완료하지 못했습니다. 콘솔 trace로 계속 진행합니다.")
        if exc.stderr:
            print(exc.stderr.strip())


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required for this optional end-to-end Foundry Agent RAG scenario.")
    return value


def build_rag_documents() -> tuple[list[dict[str, object]], str]:
    document_path = Path("Chapter4_Agent_Patterns/company_policy.txt")
    chunks = chunk_text(document_path.read_text(encoding="utf-8"), chunk_size=500, overlap=80)
    vectors = embed_texts(chunks, scenario_name="chapter8.foundry_agent_rag.embeddings")

    documents: list[dict[str, object]] = []
    for index, (chunk, vector) in enumerate(zip(chunks, vectors), start=1):
        documents.append(
            {
                "id": f"company-policy-{index}",
                "source": str(document_path),
                "chunk_index": index,
                "content": chunk,
                "content_vector": vector,
            }
        )

    print(f"Prepared {len(documents)} RAG documents from {document_path}.")
    for document in documents:
        vector = document["content_vector"]
        print(f"\n--- upload document {document['id']} ---")
        print(document["content"])
        print(f"vector dimension={len(vector)}, first_8_values={vector[:8]}")

    fallback_context = "\n\n---\n\n".join(document["content"] for document in documents)
    return documents, fallback_context


def resolve_search_endpoint() -> str | None:
    raw_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    service_name = (
        os.getenv("AZURE_SEARCH_SERVICE_NAME")
        or os.getenv("FOUNDRY_AI_SEARCH_CONNECTION_NAME")
        or os.getenv("AZURE_SEARCH_CONNECTION_NAME")
    )

    if raw_endpoint:
        endpoint = raw_endpoint.rstrip("/")
        if endpoint.endswith(".search.windows.net"):
            return endpoint

        if "cognitiveservices.azure.com" in endpoint and service_name:
            corrected = f"https://{service_name}.search.windows.net"
            print(
                "\nAZURE_SEARCH_ENDPOINT가 Cognitive Services endpoint로 설정되어 있습니다. "
                "Azure AI Search SDK에는 https://<search-service>.search.windows.net 형식이 필요합니다."
            )
            print(f"Search endpoint를 {corrected} 로 보정합니다.")
            return corrected

        print(
            "\nAZURE_SEARCH_ENDPOINT 형식이 Azure AI Search endpoint처럼 보이지 않습니다. "
            "예: https://<search-service>.search.windows.net"
        )
        return endpoint

    if service_name:
        endpoint = f"https://{service_name}.search.windows.net"
        print(f"\nAZURE_SEARCH_SERVICE_NAME 또는 Foundry connection name으로 Search endpoint를 구성합니다: {endpoint}")
        return endpoint

    return None


def create_or_update_search_index(*, vector_dimension: int) -> tuple[str, str | None, bool]:
    search_endpoint = resolve_search_endpoint()
    search_api_key = os.getenv("AZURE_SEARCH_API_KEY")
    search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "foundry-agent-rag-index")

    if not search_endpoint or not search_api_key:
        print(
            "\nAZURE_SEARCH_ENDPOINT 또는 AZURE_SEARCH_API_KEY가 없어 Azure AI Search 업로드는 건너뜁니다. "
            "agent에는 fallback context를 직접 전달합니다."
        )
        return search_index_name, None, False

    credential = AzureKeyCredential(search_api_key)
    index_client = SearchIndexClient(
        endpoint=search_endpoint,
        credential=credential,
        connection_verify=get_ssl_verify(),
    )
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=vector_dimension,
            vector_search_profile_name="vector-profile",
        ),
    ]
    index = SearchIndex(
        name=search_index_name,
        fields=fields,
        semantic_search=SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="semantic-config",
                    prioritized_fields=SemanticPrioritizedFields(
                        content_fields=[SemanticField(field_name="content")],
                        keywords_fields=[SemanticField(field_name="source")],
                    ),
                )
            ],
            default_configuration_name="semantic-config",
        ),
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
            profiles=[VectorSearchProfile(name="vector-profile", algorithm_configuration_name="hnsw-config")],
        ),
    )
    try:
        index_client.create_or_update_index(index)
    except AzureError as exc:
        message = str(exc)
        if "api key" in message.lower() or "authorization" in message.lower() or "forbidden" in message.lower():
            print(
                "\nAzure AI Search 인덱스 생성/업데이트 권한이 없어 업로드는 건너뜁니다. "
                "AZURE_SEARCH_API_KEY가 해당 Search 서비스의 admin key 또는 index 쓰기 권한인지 확인하세요."
            )
            print(f"Search 인증 오류: {exc}")
            print("인덱스가 이미 존재하고 Foundry project connection이 있으면 Search tool 연결은 계속 시도합니다.")
            return search_index_name, search_endpoint, False

        print(
            "\nAzure AI Search 인덱스 생성/업데이트를 건너뜁니다. "
            "AZURE_SEARCH_ENDPOINT 또는 AZURE_SEARCH_API_KEY가 현재 환경의 Search 리소스와 맞지 않을 수 있습니다."
        )
        print(f"Search 오류: {exc}")
        print("이 실습은 계속 진행하며, agent에는 fallback context를 직접 전달합니다.")
        return search_index_name, None, False

    print(f"\nCreated or updated Azure AI Search index: {search_index_name}")
    print("Semantic configuration: semantic-config (content=content, keywords=source)")
    return search_index_name, search_endpoint, True


def upload_rag_documents(*, search_endpoint: str, search_index_name: str, documents: list[dict[str, object]]) -> None:
    search_api_key = _required_env("AZURE_SEARCH_API_KEY")
    search_client = SearchClient(
        endpoint=search_endpoint,
        index_name=search_index_name,
        credential=AzureKeyCredential(search_api_key),
        connection_verify=get_ssl_verify(),
    )
    try:
        result = search_client.upload_documents(documents=documents)
    except AzureError as exc:
        print("\nAzure AI Search 문서 업로드를 건너뜁니다. fallback context로 계속 진행합니다.")
        print(f"Upload 오류: {exc}")
        return

    succeeded = sum(1 for item in result if item.succeeded)
    print(f"Uploaded {succeeded}/{len(documents)} RAG documents to Azure AI Search index: {search_index_name}")


def connection_value(connection: object, *names: str) -> str | None:
    for name in names:
        value = getattr(connection, name, None)
        if value:
            return str(value)
    return None


def is_ai_search_connection(connection: object) -> bool:
    name = connection_value(connection, "name") or ""
    connection_id = connection_value(connection, "id") or ""
    connection_type = connection_value(connection, "type", "connection_type", "category") or ""
    target = connection_value(connection, "target", "endpoint", "resource_id") or ""
    connection_type_text = connection_type.lower()

    if connection_type_text and connection_type_text != "(unknown type)":
        return "azure_ai_search" in connection_type_text or "azure ai search" in connection_type_text

    haystack = f"{name} {connection_id} {target}".lower()
    return ".search.windows.net" in haystack


def find_ai_search_connection_id(project: AIProjectClient) -> str | None:
    project_connection_id = os.getenv("FOUNDRY_AI_SEARCH_CONNECTION_ID")
    if project_connection_id:
        print("Foundry AI Search connection id: configured from FOUNDRY_AI_SEARCH_CONNECTION_ID")
        return project_connection_id

    preferred_name = os.getenv("FOUNDRY_AI_SEARCH_CONNECTION_NAME") or os.getenv("AZURE_SEARCH_CONNECTION_NAME")
    connections = list(project.connections.list())
    print("\n[Foundry project connections]")
    for connection in connections:
        name = connection_value(connection, "name") or "(unknown)"
        connection_id = connection_value(connection, "id") or "(no id)"
        connection_type = connection_value(connection, "type", "connection_type", "category") or "(unknown type)"
        print(f"- name={name}, type={connection_type}, id={connection_id}")

    if preferred_name:
        for connection in connections:
            name = connection_value(connection, "name")
            connection_id = connection_value(connection, "id")
            if preferred_name in {name, connection_id} and is_ai_search_connection(connection):
                print(f"Selected Foundry AI Search connection by name: {preferred_name}")
                return connection_id or name
        print(f"FOUNDRY_AI_SEARCH_CONNECTION_NAME={preferred_name} 연결을 찾지 못했습니다.")

    for connection in connections:
        name = connection_value(connection, "name") or ""
        connection_id = connection_value(connection, "id") or ""
        if is_ai_search_connection(connection):
            print(f"Auto-selected Foundry AI Search connection: {name or connection_id}")
            return connection_id or name

    print(
        "\nFoundry project에서 Azure AI Search connection을 자동으로 찾지 못했습니다. "
        "포털에서 Search 연결을 만든 뒤 FOUNDRY_AI_SEARCH_CONNECTION_NAME에 연결 이름을 넣으면 됩니다."
    )
    return None


def get_search_query_type() -> str:
    raw_value = os.getenv("FOUNDRY_AI_SEARCH_QUERY_TYPE", "simple").strip().lower()
    query_types = {
        "simple": AzureAISearchQueryType.SIMPLE,
        "semantic": AzureAISearchQueryType.SEMANTIC,
        "vector": AzureAISearchQueryType.VECTOR,
        "vector_simple_hybrid": AzureAISearchQueryType.VECTOR_SIMPLE_HYBRID,
        "vector_semantic_hybrid": AzureAISearchQueryType.VECTOR_SEMANTIC_HYBRID,
    }
    if raw_value not in query_types:
        print(
            "FOUNDRY_AI_SEARCH_QUERY_TYPE 값이 올바르지 않아 simple 검색을 사용합니다. "
            "가능한 값: simple, semantic, vector, vector_simple_hybrid, vector_semantic_hybrid"
        )
        return AzureAISearchQueryType.SIMPLE

    return query_types[raw_value]


def _create_or_get_conversation(openai: Any) -> str | None:
    conversation_id = os.getenv("FOUNDRY_AGENT_CONVERSATION_ID")
    if conversation_id:
        print(f"Using configured conversation id: {conversation_id}")
        return conversation_id

    try:
        conversation = openai.conversations.create(
            metadata={
                "chapter": "8.1",
                "scenario": "foundry-agent-rag",
            }
        )
    except Exception as exc:
        print("Conversation 생성이 지원되지 않아 응답 ID 단위 추적으로 계속합니다.")
        print(f"Conversation 생성 오류: {exc}")
        return None

    created_conversation_id = getattr(conversation, "id", None)
    if created_conversation_id:
        print(f"Created conversation id: {created_conversation_id}")
    return created_conversation_id


def create_agent_response(
    openai: Any,
    *,
    agent_name: str,
    user_input: str,
    fallback_user_input: str | None = None,
) -> object:
    conversation_id = _create_or_get_conversation(openai)
    request_kwargs: dict[str, Any] = {
        "input": user_input,
        "extra_body": {
            "agent_reference": {
                "name": agent_name,
                "type": "agent_reference",
            }
        },
    }
    if conversation_id:
        request_kwargs["conversation"] = conversation_id

    try:
        print("\n[에이전트 실행 대기 중] Foundry 에이전트에 요청을 보냈습니다. 응답을 기다리는 중입니다... (도구 호출이 포함되면 수십 초가 걸릴 수 있습니다)", flush=True)
        response = openai.responses.create(**request_kwargs)
    except Exception as exc:
        if not conversation_id:
            raise
        print("Conversation 연결 응답 호출이 실패해 응답 ID 단위 추적으로 재시도합니다.")
        print(f"Conversation 응답 오류: {exc}")
        request_kwargs.pop("conversation", None)
        response = openai.responses.create(**request_kwargs)

    response_id = getattr(response, "id", None)
    response_conversation = getattr(response, "conversation", None)
    response_conversation_id = getattr(response_conversation, "id", None) if response_conversation else None
    if response_conversation_id or conversation_id:
        print(f"Trace conversation id: {response_conversation_id or conversation_id}")
    if response_id:
        print(f"Trace response id: {response_id}")

    if conversation_id and fallback_user_input:
        answer_text = _output_text(response)
        if "진단서 또는 소견서" not in answer_text:
            print("Conversation 응답이 검색 근거를 충분히 반영하지 않아 같은 대화 ID로 fallback context를 재질의합니다.")
            retry_kwargs = dict(request_kwargs)
            retry_kwargs["input"] = fallback_user_input
            response = openai.responses.create(**retry_kwargs)
            retry_response_id = getattr(response, "id", None)
            if retry_response_id:
                print(f"Trace fallback response id: {retry_response_id}")
    return response


def build_search_tool(project: AIProjectClient, search_index_name: str) -> AzureAISearchTool | None:
    project_connection_id = find_ai_search_connection_id(project)
    if not project_connection_id:
        return None

    query_type = get_search_query_type()
    print(f"Foundry AI Search connection id: {project_connection_id}")
    print(f"Agent tool index name: {search_index_name}")
    print(f"Agent tool query type: {query_type}")
    return AzureAISearchTool(
        azure_ai_search=AzureAISearchToolResource(
            indexes=[
                AISearchIndexResource(
                    project_connection_id=project_connection_id,
                    index_name=search_index_name,
                    query_type=query_type,
                )
            ]
        )
    )


def create_and_run_foundry_agent() -> str:
    project_endpoint = get_project_endpoint()
    model_deployment_name = get_model_deployment_name()
    agent_name = "chapter-8-1-rag-agent"
    keep_agent = os.getenv("FOUNDRY_KEEP_AGENT", "false").lower() == "true"
    ensure_application_insights()
    documents, fallback_context = build_rag_documents()
    search_index_name, search_endpoint, can_upload_documents = create_or_update_search_index(
        vector_dimension=len(documents[0]["content_vector"]),
    )
    if search_endpoint and can_upload_documents:
        upload_rag_documents(search_endpoint=search_endpoint, search_index_name=search_index_name, documents=documents)
    elif search_endpoint:
        print(
            "\n[Existing Search mode] 문서 업로드는 건너뛰고, "
            "기존 Azure AI Search 인덱스와 Foundry project connection으로 tool 연결을 시도합니다."
        )
    else:
        print("\n[Fallback mode] Azure AI Search tool 없이 policy context를 user message에 직접 넣어 실행합니다.")

    _credential = get_project_credential()
    _project_api_key = get_project_api_key()
    _ssl_verify = get_ssl_verify()
    _openai_kwargs: dict[str, Any] = {}
    if _project_api_key:
        _openai_kwargs["api_key"] = _project_api_key
    if _ssl_verify is not True:
        import httpx
        _openai_kwargs["http_client"] = httpx.Client(verify=_ssl_verify)

    with foundry_span("chapter8.foundry_agent.create_and_run"):
        with AIProjectClient(
            endpoint=project_endpoint,
            credential=_credential,
            connection_verify=_ssl_verify,
        ) as project:
            search_tool = build_search_tool(project, search_index_name) if search_endpoint else None
            tools = [search_tool] if search_tool else None

            definition_kwargs = {
                "model": model_deployment_name,
                "instructions": (
                    "You are a Microsoft Foundry RAG agent. Answer in Korean. "
                    "Use the connected Azure AI Search index when it is available. "
                    "If context is provided directly in the user message, answer only from that context. "
                    "Cite the policy section or retrieved chunk you used."
                ),
            }
            if tools:
                definition_kwargs["tools"] = tools

            agent = project.agents.create_version(
                agent_name=agent_name,
                definition=PromptAgentDefinition(**definition_kwargs),
            )
            print(f"Created Foundry agent version: {agent.name} v{agent.version}")
            print(f"Project endpoint: {project_endpoint}")
            print(
                "Agent reference for Responses API: "
                f"{{'type': 'agent_reference', 'name': '{agent.name}'}}"
            )

            try:
                search_user_input = "정규 직원의 연차 규정과 병가 5일 연속 사용 시 필요한 증빙 서류를 알려줘."
                fallback_user_input = (
                    "아래 RAG context만 근거로 답하세요.\n\n"
                    f"Context:\n{fallback_context}\n\n"
                    "Question: 정규 직원의 연차 규정과 병가 5일 연속 사용 시 필요한 증빙 서류를 알려줘."
                )
                user_input = search_user_input if search_tool else fallback_user_input

                with project.get_openai_client(**_openai_kwargs) as openai:
                    try:
                        response = create_agent_response(
                            openai,
                            agent_name=agent.name,
                            user_input=user_input,
                            fallback_user_input=fallback_user_input if search_tool else None,
                        )
                    except Exception as exc:
                        if not search_tool:
                            raise
                        print("\nSearch tool 호출이 실패해 fallback context로 한 번 더 질의합니다.")
                        print(f"Search tool 오류: {exc}")
                        response = create_agent_response(
                            openai,
                            agent_name=agent.name,
                            user_input=fallback_user_input,
                        )
                return _output_text(response)
            finally:
                if keep_agent:
                    print(
                        "FOUNDRY_KEEP_AGENT=true 이므로 agent version을 삭제하지 않습니다. "
                        "실습 후 포털에서 직접 정리하세요."
                    )
                else:
                    project.agents.delete_version(
                        agent_name=agent.name,
                        agent_version=agent.version,
                    )
                    print(f"Deleted Foundry agent version: {agent.name} v{agent.version}")


if __name__ == "__main__":
    print("Foundry 프로젝트에 RAG agent를 생성하고, chunk/vector 인덱스를 연결한 뒤 질의응답합니다.\n")
    try:
        answer = create_and_run_foundry_agent()
        print("\n## Foundry RAG Agent 응답\n")
        print(answer)
    except Exception as exc:
        print(f"오류가 발생했습니다: {exc}")
        print(
            "FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_MODEL_DEPLOYMENT_NAME, Azure 로그인/권한을 확인하세요. "
            "Azure AI Search 업로드까지 실행하려면 AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, "
            "AZURE_SEARCH_INDEX_NAME을 설정하세요. Foundry agent tool 연결은 project connections에서 자동 탐색하며, "
            "필요하면 FOUNDRY_AI_SEARCH_CONNECTION_NAME으로 연결 이름을 지정하세요."
        )
