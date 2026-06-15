from collections.abc import Sequence
from typing import Any

from openai import AzureOpenAI, BadRequestError, OpenAI

from .config import FoundrySettings, get_reasoning_kwargs, get_settings
from .tracing import foundry_span

Message = dict[str, str]


def _azure_endpoint(endpoint: str) -> str:
    # AzureOpenAI 클라이언트는 /openai/v1 같은 path가 빠진 리소스 endpoint를 기대합니다.
    normalized = endpoint.rstrip("/")
    for suffix in ("/openai/v1", "/openai"):
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
    return normalized


def get_openai_client() -> AzureOpenAI | OpenAI:
    # FOUNDRY_OPENAI_ENDPOINT_TYPE에 따라 Foundry-style 또는 Azure OpenAI 클라이언트를 고릅니다.
    settings = get_settings()
    if settings.openai_endpoint_type == "foundry":
        return OpenAI(
            base_url=settings.openai_endpoint.rstrip("/"),
            api_key=settings.api_key,
        )
    return AzureOpenAI(
        azure_endpoint=_azure_endpoint(settings.openai_endpoint),
        api_key=settings.api_key,
        api_version=settings.openai_api_version,
    )


def get_project_client() -> None:
    # 기본 hands-on은 API key 모드라 Project SDK 클라이언트를 공통 경로에서 열지 않습니다.
    raise RuntimeError(
        "AIProjectClient uses Entra ID credentials and is not available in API-key mode. "
        "Use get_openai_client() for model and embedding calls."
    )


def _output_text(response: Any) -> str:
    # SDK 버전에 따라 응답 텍스트 위치가 다를 수 있어 흔한 형태를 모두 확인합니다.
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)
    return "\n".join(chunks).strip()


def _print_usage(response: Any) -> None:
    usage = getattr(response, "usage", None)
    if usage:
        print(f"\nToken usage: {usage}")


def _create_response_with_reasoning_fallback(openai: Any, **request_kwargs: Any) -> Any:
    # 모델 호출은 네트워크 왕복이라 수 초~수십 초가 걸립니다. 멈춘 것처럼 보이지 않도록
    # 블로킹 호출 직전에 대기 상태를 알리고, flush=True로 즉시 출력되게 합니다.
    print("\n[모델 응답 대기 중] 요청을 보냈습니다. 응답을 기다리는 중입니다... (모델에 따라 수십 초가 걸릴 수 있습니다)", flush=True)
    try:
        return openai.responses.create(**request_kwargs)
    except BadRequestError as exc:
        if "reasoning" not in request_kwargs or "reasoning" not in str(exc).lower():
            raise
        print("\n[안내] 현재 모델 또는 endpoint가 reasoning 옵션을 지원하지 않아 reasoning 없이 재시도합니다. 응답을 다시 기다리는 중입니다...", flush=True)
        retry_kwargs = dict(request_kwargs)
        retry_kwargs.pop("reasoning", None)
        return openai.responses.create(**retry_kwargs)


def reasoning_request_kwargs(settings: FoundrySettings | None = None) -> dict[str, dict[str, str]]:
    if settings is None:
        return get_reasoning_kwargs()
    if not settings.reasoning_effort:
        return {}
    return {"reasoning": {"effort": settings.reasoning_effort}}


def create_response(openai: Any, **request_kwargs: Any) -> Any:
    request_kwargs.update(reasoning_request_kwargs())
    return _create_response_with_reasoning_fallback(openai, **request_kwargs)


def _response_input(messages: Sequence[Message]) -> list[dict[str, str]]:
    # Responses API가 요구하는 message input 형태로 챕터 예제의 단순 dict를 변환합니다.
    return [
        {
            "type": "message",
            "role": message["role"],
            "content": message["content"],
        }
        for message in messages
    ]


def run_chat_prompt(
    messages: Sequence[Message],
    *,
    scenario_name: str,
    print_usage: bool = True,
) -> str:
    # 여러 턴의 system/user/assistant 메시지를 그대로 모델에 전달하는 공통 실행 함수입니다.
    settings = get_settings()
    with foundry_span(scenario_name):
        with get_openai_client() as openai:
            response = _create_response_with_reasoning_fallback(
                openai,
                model=settings.model_deployment_name,
                input=_response_input(messages),
                **reasoning_request_kwargs(settings),
            )
    if print_usage:
        _print_usage(response)
    return _output_text(response)


def run_single_turn_prompt(
    system_prompt: str,
    user_prompt: str,
    *,
    scenario_name: str,
    print_usage: bool = True,
) -> str:
    # 초보자가 prompt 구성을 볼 수 있도록 모델에 보내는 system/user prompt를 먼저 출력합니다.
    print(f"\n[run_single_turn_prompt: {scenario_name}]")
    print("[모델에게 전달한 system prompt]")
    print(system_prompt)
    print("\n[모델에게 전달한 user prompt]")
    print(user_prompt)

    return run_chat_prompt(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        scenario_name=scenario_name,
        print_usage=print_usage,
    )


def run_threaded_prompt(
    messages: list[Message],
    user_prompt: str,
    *,
    scenario_name: str,
) -> str:
    # 같은 messages 리스트에 대화를 누적해 stateful agent처럼 보이게 만듭니다.
    messages.append({"role": "user", "content": user_prompt})
    answer = run_chat_prompt(
        messages,
        scenario_name=scenario_name,
        print_usage=False,
    )
    messages.append({"role": "assistant", "content": answer})
    return answer
