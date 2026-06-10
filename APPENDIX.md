# 부록: 환경과 구성 파일 정리

이 부록은 hands-on 실습 전에 확인해야 하는 환경 파일과 공통 설정의 의미를 짧게 정리합니다.

## .env 필수 값

`.env.example`을 복사해 `.env`를 만들고 아래 값을 채웁니다.

```bash
FOUNDRY_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
FOUNDRY_API_KEY=<your-api-key>
FOUNDRY_OPENAI_API_VERSION=2025-04-01-preview
FOUNDRY_OPENAI_ENDPOINT_TYPE=azure_openai
FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-5.4
FOUNDRY_EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-small
```

1장부터 7장까지의 기본 Foundry 호출, RAG, MCP 도구 서버, Guardrails 실습은 endpoint, API key, 모델 배포명이 핵심입니다. 8장의 Foundry Agent Service 실습은 여기에 project endpoint, Azure 로그인, Azure AI Search, Knowledge base, Application Insights 설정이 추가됩니다.

## .env.example 관리 원칙

`.env.example`은 실제 `.env`와 같은 변수 이름만 갖도록 관리합니다. 예시 파일에는 secret 값을 넣지 않고, endpoint나 connection string은 placeholder로 둡니다.

변수 목록을 확인하려면 아래처럼 두 파일의 변수 이름을 비교합니다.

Windows (PowerShell):

```powershell
$envKeys = Get-Content .env | ForEach-Object { if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') { $matches[1] } }
$exampleKeys = Get-Content .env.example | ForEach-Object { if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') { $matches[1] } }
Compare-Object $envKeys $exampleKeys
```

macOS / Linux (bash·zsh):

```bash
diff <(grep -oE '^[A-Za-z_][A-Za-z0-9_]*' .env | sort) \
     <(grep -oE '^[A-Za-z_][A-Za-z0-9_]*' .env.example | sort)
```

아무 출력이 없으면(차이가 없으면) 두 파일이 같은 변수 집합을 가진 것입니다.

## 인증

이 저장소는 Azure CLI 로그인 대신 API key를 사용합니다. `.env`에 `FOUNDRY_OPENAI_ENDPOINT`와 `FOUNDRY_API_KEY`를 입력하면 공통 client가 OpenAI-compatible endpoint를 직접 호출합니다.

## Trace

Trace는 `FOUNDRY_APPLICATIONINSIGHTS_CONNECTION_STRING` 또는 `APPLICATIONINSIGHTS_CONNECTION_STRING`이 있으면 Azure Monitor로 내보내고, 없으면 콘솔 OpenTelemetry 출력으로 확인합니다. Application Insights 리소스 연결은 필수는 아니지만, 8.4 monitoring 실습에서 포털 trace와 운영 메트릭을 확인하려면 강의 전에 수동으로 만들어 두는 것을 권장합니다.

## 선택 또는 확장 설정

Azure AI Search와 Knowledge base는 8장 Foundry Agent Service 실습에 필요합니다. Document Intelligence 같은 추가 관리형 서비스는 현재 기본 실습의 필수 환경 변수가 아니며, 4장의 고급 RAG 설명에서 프로덕션 확장 방향으로만 다룹니다.
