# Run: uv run Chapter8_Foundry_Agents/8.3_create_foundry_agent_with_mcp.py
# 학습 포인트: Foundry Agent에 원격 MCP 서버를 코드로 연결하고 MCP 도구 기반 답변을 실행합니다.
# 초보자 읽기: Microsoft Learn MCP 서버를 agent tool로 붙여 공식 문서를 검색하는 흐름을 봅니다.
import os
import re
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPTool, PromptAgentDefinition
from dotenv import load_dotenv

import _bootstrap  # noqa: F401
from foundry_hands_on.client import _output_text
from foundry_hands_on.config import get_model_deployment_name, get_project_api_key, get_project_credential, get_project_endpoint, get_ssl_verify
from foundry_hands_on.tracing import foundry_span


DEFAULT_MCP_ENDPOINT = "https://learn.microsoft.com/api/mcp"
DEFAULT_ALLOWED_TOOLS = [
    "microsoft_docs_search",
    "microsoft_docs_fetch",
    "microsoft_code_sample_search",
]


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def server_label(value: str) -> str:
    label = re.sub(r"[^0-9A-Za-z_-]", "_", value.strip())
    return label or "microsoft_learn_mcp"


def _create_or_get_conversation(openai: Any) -> str | None:
    conversation_id = os.getenv("FOUNDRY_DEMO_MCP_AGENT_CONVERSATION_ID") or os.getenv("FOUNDRY_AGENT_CONVERSATION_ID")
    if conversation_id:
        print(f"Using configured conversation id: {conversation_id}")
        return conversation_id

    try:
        conversation = openai.conversations.create(
            metadata={
                "chapter": "8.3",
                "scenario": "foundry-mcp-agent",
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
        print("\n[에이전트 실행 대기 중] MCP 에이전트에 요청을 보냈습니다. 응답을 기다리는 중입니다... (MCP 도구 호출 포함 시 수십 초가 걸릴 수 있습니다)", flush=True)
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


def create_and_run_mcp_agent() -> str:
    load_dotenv(override=False)

    project_endpoint = get_project_endpoint()
    model_deployment_name = get_model_deployment_name()
    mcp_endpoint = os.getenv("FOUNDRY_DEMO_MCP_SERVER_URL", DEFAULT_MCP_ENDPOINT)
    mcp_name = os.getenv("FOUNDRY_DEMO_MCP_CONNECTION_NAME", "microsoft-learn-mcp")
    agent_name = os.getenv("FOUNDRY_DEMO_MCP_AGENT_NAME", "chapter-8-3-learn-mcp-agent")
    keep_agent = os.getenv("FOUNDRY_KEEP_AGENT", "false").lower() == "true"
    allowed_tools = split_csv(os.getenv("FOUNDRY_DEMO_MCP_ALLOWED_TOOLS")) or DEFAULT_ALLOWED_TOOLS
    question = os.getenv(
        "FOUNDRY_DEMO_MCP_TEST_QUESTION",
        "How can I create a Microsoft Foundry project using Azure CLI?",
    )

    mcp_tool = MCPTool(
        server_label=server_label(mcp_name),
        server_url=mcp_endpoint,
        server_description="Microsoft Learn documentation and code sample MCP server.",
        allowed_tools=allowed_tools,
        require_approval="never",
    )

    _credential = get_project_credential()
    _project_api_key = get_project_api_key()
    _ssl_verify = get_ssl_verify()
    _openai_kwargs: dict[str, Any] = {}
    # OBO 인증을 필요로 하는 도구(MCP 등)가 있는 에이전트는 Bearer API Key가 아닌
    # Microsoft Entra ID 토큰 인증이 필요하므로 api_key를 _openai_kwargs에 지정하지 않고
    # DefaultAzureCredential을 사용해 토큰 인증 방식으로 동작하게 유도합니다.
    # if _project_api_key:
    #     _openai_kwargs["api_key"] = _project_api_key
    if _ssl_verify is not True:
        import httpx
        _openai_kwargs["http_client"] = httpx.Client(verify=_ssl_verify)

    with foundry_span("chapter8.learn_mcp_agent.create_and_run"):
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
                        "You are a Microsoft technical learning assistant. "
                        "Use the connected Microsoft Learn MCP tools when the question asks about Microsoft products, "
                        "Azure, Foundry, SDKs, CLI commands, or official documentation. "
                        "Answer in Korean unless the user asks otherwise."
                    ),
                    tools=[mcp_tool],
                ),
            )

            print("\n[Foundry MCP agent 생성]")
            print(f"- project endpoint: {project_endpoint}")
            print(f"- model deployment: {model_deployment_name}")
            print(f"- MCP server label: {server_label(mcp_name)}")
            print(f"- MCP server URL: {mcp_endpoint}")
            print(f"- allowed tools: {', '.join(allowed_tools)}")
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
        answer = create_and_run_mcp_agent()
        print("\n[Agent response]")
        print(answer)
    except Exception as exc:
        print(f"오류가 발생했습니다: {exc}")
        print(
            "Microsoft Learn MCP 서버는 https://learn.microsoft.com/api/mcp 입니다. "
            "Foundry project endpoint, Azure 로그인 상태, 모델 배포명, MCP endpoint 값을 확인하세요. "
            "브라우저에서 MCP endpoint를 직접 열면 405 Method Not Allowed가 보일 수 있지만, MCP client 호출에는 정상일 수 있습니다."
        )