# Run: uv run Chapter8_Foundry_Agents/8.2_create_foundry_agent_with_knowledge_base.py
# 학습 포인트: Foundry IQ/Knowledge base를 MCPTool로 Foundry Agent에 연결해 질의응답합니다.
# 초보자 읽기: 포털에서 Knowledge base와 MCP project connection을 만든 뒤, agent의 도구/지식 연결로 사용합니다.
import os
import re
from typing import Any

import requests
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

import _bootstrap  # noqa: F401
from foundry_hands_on.client import _output_text
from foundry_hands_on.config import get_model_deployment_name, get_project_api_key, get_project_credential, get_project_endpoint, get_ssl_verify
from foundry_hands_on.tracing import foundry_span


KNOWLEDGE_BASE_MCP_API_VERSION = "2025-11-01-preview"
PROJECT_CONNECTION_API_VERSION = "2025-10-01-preview"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required for this Knowledge base example.")
    return value


def server_label(value: str) -> str:
    label = re.sub(r"[^0-9A-Za-z_-]", "_", value.strip())
    return label or "knowledge_base"


def knowledge_base_mcp_endpoint(search_endpoint: str, knowledge_base_name: str) -> str:
    return (
        f"{search_endpoint.rstrip('/')}/knowledgebases/{knowledge_base_name}/mcp"
        f"?api-version={KNOWLEDGE_BASE_MCP_API_VERSION}"
    )


def ensure_kb_mcp_project_connection(
    credential: DefaultAzureCredential,
    *,
    project_resource_id: str,
    connection_name: str,
    mcp_endpoint: str,
) -> None:
    token_provider = get_bearer_token_provider(credential, "https://management.azure.com/.default")
    response = requests.put(
        f"https://management.azure.com{project_resource_id}/connections/{connection_name}"
        f"?api-version={PROJECT_CONNECTION_API_VERSION}",
        headers={"Authorization": f"Bearer {token_provider()}"},
        json={
            "name": connection_name,
            "type": "Microsoft.MachineLearningServices/workspaces/connections",
            "properties": {
                "authType": "ProjectManagedIdentity",
                "category": "RemoteTool",
                "target": mcp_endpoint,
                "isSharedToAll": True,
                "audience": "https://search.azure.com/",
                "metadata": {"ApiType": "Azure"},
            },
        },
        timeout=60,
        verify=get_ssl_verify(),
    )
    response.raise_for_status()
    print(f"- MCP project connection created/updated: {connection_name}")


def _create_or_get_conversation(openai: Any) -> str | None:
    conversation_id = os.getenv("FOUNDRY_KB_AGENT_CONVERSATION_ID") or os.getenv("FOUNDRY_AGENT_CONVERSATION_ID")
    if conversation_id:
        print(f"Using configured conversation id: {conversation_id}")
        return conversation_id

    try:
        conversation = openai.conversations.create(
            metadata={
                "chapter": "8.2",
                "scenario": "foundry-knowledge-base-agent",
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


def create_agent_response(openai: Any, *, agent_name: str, user_input: str) -> object:
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
        print("\n[에이전트 실행 대기 중] Knowledge base 에이전트에 요청을 보냈습니다. 응답을 기다리는 중입니다... (검색/도구 호출 포함 시 수십 초가 걸릴 수 있습니다)", flush=True)
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
    return response


def create_and_run_knowledge_base_agent() -> str:
    load_dotenv(override=False)

    project_endpoint = get_project_endpoint()
    model_deployment_name = get_model_deployment_name()
    search_endpoint = require_env("AZURE_SEARCH_ENDPOINT")
    knowledge_base_name = require_env("FOUNDRY_KNOWLEDGE_BASE_NAME")
    kb_mcp_connection_name = require_env("FOUNDRY_KB_MCP_CONNECTION_NAME")
    project_resource_id = require_env("FOUNDRY_PROJECT_RESOURCE_ID")
    agent_name = os.getenv("FOUNDRY_KB_AGENT_NAME", "chapter-8-2-knowledge-base-agent")
    keep_agent = os.getenv("FOUNDRY_KEEP_AGENT", "false").lower() == "true"
    question = os.getenv(
        "FOUNDRY_KB_TEST_QUESTION",
        "회사 정책에서 재택근무와 보안 관련 핵심 규칙을 요약해 주세요.",
    )
    mcp_endpoint = knowledge_base_mcp_endpoint(search_endpoint, knowledge_base_name)
    _credential = get_project_credential()
    _project_api_key = get_project_api_key()
    _ssl_verify = get_ssl_verify()
    _openai_kwargs: dict[str, Any] = {}
    # OBO 인증을 필요로 하는 도구(Knowledge Base 등)가 있는 에이전트는 Bearer API Key가 아닌
    # Microsoft Entra ID 토큰 인증이 필요하므로 api_key를 _openai_kwargs에 지정하지 않고
    # DefaultAzureCredential을 사용해 토큰 인증 방식으로 동작하게 유도합니다.
    # if _project_api_key:
    #     _openai_kwargs["api_key"] = _project_api_key
    if _ssl_verify is not True:
        import httpx
        _openai_kwargs["http_client"] = httpx.Client(verify=_ssl_verify)

    print("\n[Knowledge base MCP project connection 준비]")
    print(f"- knowledge base: {knowledge_base_name}")
    print(f"- MCP server URL: {mcp_endpoint}")
    print(f"- MCP project connection: {kb_mcp_connection_name}")
    # ARM API는 Azure AD 토큰이 필요합니다. API 키 모드에서는 실패할 수 있습니다.
    # connection이 이미 존재하면 실패해도 agent 실행에는 문제 없습니다.
    try:
        ensure_kb_mcp_project_connection(
            _credential,
            project_resource_id=project_resource_id,
            connection_name=kb_mcp_connection_name,
            mcp_endpoint=mcp_endpoint,
        )
    except Exception as exc:
        print(f"\n[경고] Knowledge base MCP project connection 생성/업데이트 실패: {exc}")
        print(f"  connection({kb_mcp_connection_name})이 이미 존재하면 아래 agent 실행은 계속됩니다.")

    kb_tool = MCPTool(
        server_label=server_label(knowledge_base_name),
        server_url=mcp_endpoint,
        server_description="Foundry IQ knowledge base MCP endpoint.",
        allowed_tools=["knowledge_base_retrieve"],
        require_approval="never",
        project_connection_id=kb_mcp_connection_name,
    )

    with foundry_span("chapter8.knowledge_base_agent.create_and_run"):
        with AIProjectClient(
            endpoint=project_endpoint,
            credential=_credential,
            connection_verify=_ssl_verify,
        ) as project:
            agent = project.agents.create_version(
                agent_name=agent_name,
                definition=PromptAgentDefinition(
                    model=model_deployment_name,
                    instructions=(
                        "You are a company policy assistant. Answer in Korean. "
                        "Use the connected knowledge base tool to answer every user question. "
                        "Do not answer from your own knowledge. "
                        "If the knowledge base does not contain enough information, say that you do not know. "
                        "When you use knowledge base information, include source citations when the tool returns them."
                    ),
                    tools=[kb_tool],
                ),
            )
            print("\n[Foundry Knowledge base agent 생성]")
            print(f"- project endpoint: {project_endpoint}")
            print(f"- model deployment: {model_deployment_name}")
            print(f"- knowledge base: {knowledge_base_name}")
            print(f"- MCP server URL: {mcp_endpoint}")
            print(f"- MCP project connection: {kb_mcp_connection_name}")
            print(f"- agent: {agent.name} v{agent.version}")
            print(f"- question: {question}")

            try:
                with project.get_openai_client(**_openai_kwargs) as openai:
                    response = create_agent_response(
                        openai,
                        agent_name=agent.name,
                        user_input=question,
                    )
                return _output_text(response)
            finally:
                if keep_agent:
                    print("\nFOUNDRY_KEEP_AGENT=true 이므로 agent version을 삭제하지 않습니다.")
                else:
                    project.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
                    print("\nAgent version deleted.")


if __name__ == "__main__":
    try:
        answer = create_and_run_knowledge_base_agent()
        print("\n[Agent response]")
        print(answer)
    except Exception as exc:
        print(f"오류가 발생했습니다: {exc}")
        print(
            "Foundry 포털 또는 Azure Portal에서 Knowledge base를 먼저 만들고, "
            ".env의 FOUNDRY_PROJECT_RESOURCE_ID, FOUNDRY_KNOWLEDGE_BASE_NAME, "
            "AZURE_SEARCH_ENDPOINT, FOUNDRY_KB_MCP_CONNECTION_NAME을 확인하세요. "
            "현재 코드는 Foundry project RemoteTool/MCP connection을 자동 생성/업데이트합니다."
        )
