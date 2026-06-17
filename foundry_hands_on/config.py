import os
import time
from dataclasses import dataclass

from azure.core.credentials import AccessToken
from dotenv import load_dotenv

# Load .env first before checking environment variables
load_dotenv(override=False)

# Early SSL bypass patching: default to True (bypass) for hands-on proxy environment
_disable_ssl = os.getenv("FOUNDRY_DISABLE_SSL_VERIFY", "true").lower() in {"true", "1", "yes"}
if _disable_ssl:
    import ssl
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
    except Exception:
        pass
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        pass
    os.environ["AZURE_CLI_DISABLE_CONNECTION_VERIFICATION"] = "1"


def get_model_deployment_name() -> str:
    # 여러 실습 환경에서 쓰는 배포명 변수 이름을 같은 의미로 받아들입니다.
    load_dotenv(override=False)
    model_deployment_name = (
        os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME")
        or os.getenv("MODEL_DEPLOYMENT_NAME")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    )
    if not model_deployment_name:
        raise RuntimeError(
            "FOUNDRY_MODEL_DEPLOYMENT_NAME is required. See README.md for the .env template."
        )
    return model_deployment_name


@dataclass(frozen=True)
class FoundrySettings:
    # 각 챕터가 직접 os.getenv를 반복하지 않도록 Foundry 연결 정보를 한 곳에 모읍니다.
    openai_endpoint: str
    api_key: str
    openai_api_version: str
    openai_endpoint_type: str
    project_endpoint: str | None
    model_deployment_name: str
    embedding_deployment_name: str | None
    reasoning_effort: str | None


def get_reasoning_effort() -> str | None:
    load_dotenv(override=False)
    value = os.getenv("FOUNDRY_REASONING_EFFORT", "low").strip().lower()
    if value in {"", "0", "false", "none", "off"}:
        return None
    allowed = {"minimal", "low", "medium", "high"}
    if value not in allowed:
        raise RuntimeError(
            "FOUNDRY_REASONING_EFFORT must be one of: "
            + ", ".join(sorted(allowed))
            + ", or none/off to disable."
        )
    return value


def get_reasoning_kwargs() -> dict[str, dict[str, str]]:
    reasoning_effort = get_reasoning_effort()
    if not reasoning_effort:
        return {}
    return {"reasoning": {"effort": reasoning_effort}}


def get_settings() -> FoundrySettings:
    # 기본 실습은 API key 기반 OpenAI-compatible endpoint 호출을 사용합니다.
    load_dotenv(override=False)

    openai_endpoint = (
        os.getenv("FOUNDRY_OPENAI_ENDPOINT")
        or os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    project_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    api_key = (
        os.getenv("FOUNDRY_API_KEY")
        or os.getenv("AZURE_OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    openai_api_version = (
        os.getenv("FOUNDRY_OPENAI_API_VERSION")
        or os.getenv("AZURE_OPENAI_API_VERSION")
        or "2025-04-01-preview"
    )
    openai_endpoint_type = (
        os.getenv("FOUNDRY_OPENAI_ENDPOINT_TYPE")
        or os.getenv("AZURE_OPENAI_ENDPOINT_TYPE")
        or "azure_openai"
    ).lower()
    model_deployment_name = get_model_deployment_name()
    embedding_deployment_name = (
        os.getenv("FOUNDRY_EMBEDDING_DEPLOYMENT_NAME")
        or os.getenv("AZURE_TEXT_EMBEDDING_MODEL")
    )

    missing = []
    if not openai_endpoint:
        missing.append("FOUNDRY_OPENAI_ENDPOINT")
    if not api_key:
        missing.append("FOUNDRY_API_KEY")
    if not model_deployment_name:
        missing.append("FOUNDRY_MODEL_DEPLOYMENT_NAME")

    if missing:
        raise RuntimeError(
            "Missing required Foundry environment variables: "
            + ", ".join(missing)
            + ". See README.md for the .env template."
        )

    # 위 missing 검사를 통과했으므로 endpoint와 api_key는 None이 아닙니다(타입 좁히기).
    assert openai_endpoint is not None and api_key is not None
    return FoundrySettings(
        openai_endpoint=openai_endpoint,
        api_key=api_key,
        openai_api_version=openai_api_version,
        openai_endpoint_type=openai_endpoint_type,
        project_endpoint=project_endpoint,
        model_deployment_name=model_deployment_name,
        embedding_deployment_name=embedding_deployment_name,
        reasoning_effort=get_reasoning_effort(),
    )


def get_project_endpoint() -> str:
    # 8장처럼 실제 Foundry 프로젝트 리소스를 다루는 선택 실습에서만 필요합니다.
    load_dotenv(override=False)
    project_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    if not project_endpoint:
        raise RuntimeError(
            "FOUNDRY_PROJECT_ENDPOINT is required for Foundry Agent Service examples. "
            "Use the project endpoint in the form https://<resource>.services.ai.azure.com/api/projects/<project>."
        )
    return project_endpoint


class _ApiKeyCredential:
    """FOUNDRY_API_KEY를 TokenCredential로 감싸 AIProjectClient에 전달합니다.

    AIProjectClient 생성자는 TokenCredential만 수락합니다.
    Azure AI Services 프로젝트 엔드포인트는 API 키를 Bearer 토큰으로 수락하므로
    get_token() 호출 시 API 키를 그대로 반환합니다. az login 없이 실행 가능합니다.
    """

    def __init__(self, key: str) -> None:
        self._key = key

    def get_token(self, *scopes: str, **kwargs: object) -> AccessToken:
        return AccessToken(self._key, int(time.time()) + 3600)


def get_project_api_key() -> str | None:
    """FOUNDRY_API_KEY가 설정된 경우 반환합니다.

    project.get_openai_client(api_key=get_project_api_key())처럼
    OpenAI 클라이언트에 API 키를 명시적으로 전달할 때 사용합니다.
    """
    load_dotenv(override=False)
    return (
        os.getenv("FOUNDRY_API_KEY")
        or os.getenv("AZURE_OPENAI_API_KEY")
        or None
    )


def get_project_credential() -> object:
    """Foundry Agent Service용 credential을 반환합니다.

    Agent 생성/삭제 등 컨트롤 플레인 API는 반드시 Entra ID 인증(DefaultAzureCredential)이 필요하며,
    일반 모델용 api_key는 권한 오류를 일으킵니다.
    SSL 검증 설정(connection_verify)을 주입하여 사내 프록시 등 SSL 차단 환경에서도 토큰 획득이 가능하게 합니다.
    """
    load_dotenv(override=False)
    from azure.identity import DefaultAzureCredential  # noqa: PLC0415
    return DefaultAzureCredential(connection_verify=get_ssl_verify())


def get_ssl_verify() -> bool | str:
    """SSL 검증 설정을 반환합니다.

    환경 변수로 제어:
      FOUNDRY_DISABLE_SSL_VERIFY=true  → False (검증 비활성화, 보안 주의, 기본값)
      REQUESTS_CA_BUNDLE=<경로>        → 해당 경로 (커스텀 CA bundle)
      SSL_CERT_FILE=<경로>             → 해당 경로 (REQUESTS_CA_BUNDLE 없을 때)
    """
    load_dotenv(override=False)
    if os.getenv("FOUNDRY_DISABLE_SSL_VERIFY", "true").lower() in {"true", "1", "yes"}:
        return False
    ca_bundle = os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("SSL_CERT_FILE")
    if ca_bundle and os.path.exists(ca_bundle):
        return ca_bundle
    return True
