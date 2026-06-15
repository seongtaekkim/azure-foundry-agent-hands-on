# 트러블슈팅 가이드: 회사 보안 환경(인증서, 안티바이러스)과 Windows 설정

이 문서는 실습 코드 자체보다 **실행 환경** 때문에 막히는 경우를 모았습니다. 특히 회사 노트북처럼 **TLS 검사 프록시(Zscaler 등), 기업 안티바이러스, 관리형 Windows 정책**이 걸린 환경에서 `uv sync`, `uv run`, `az login`, 모델 호출이 실패할 때 순서대로 확인하세요.

> [!NOTE]
> 명령 예시는 OS에 따라 **Windows (PowerShell)** 와 **macOS / Linux (bash, zsh)** 블록으로 나눠 표기합니다. 본인 OS 블록을 따르세요. 회사가 관리하는(Intune/GPO) 기기는 일부 설정이 잠겨 있을 수 있으니, 막히면 **사내 IT/보안 담당자에게 요청**하는 것이 정석입니다.

## 0. 증상으로 빠르게 찾기

| 증상(메시지/현상) | 가장 흔한 원인 | 바로가기 |
| --- | --- | --- |
| `uv sync`/`uv run`이 `SSL: CERTIFICATE_VERIFY_FAILED`, `self-signed certificate in certificate chain`, `unable to get local issuer certificate`로 실패 | TLS 검사 프록시(Zscaler 등)가 인증서를 바꿔치기 | [1장](#1-tls-검사-프록시zscaler-등와-사설-인증서) |
| `az login` 또는 모델 호출이 `CERTIFICATE_VERIFY_FAILED`로 실패 | 같은 원인(런타임 HTTPS 호출) | [1장 → 1.5](#1-tls-검사-프록시zscaler-등와-사설-인증서) |
| `uv sync`가 `Connection reset by peer`, 타임아웃, 매우 느림 | 프록시 경유 / 타임아웃 | [1장 → 1.6](#1-tls-검사-프록시zscaler-등와-사설-인증서) |
| `uv sync`가 비정상적으로 느리거나 "파일이 사용 중", 다운로드한 파일이 사라짐 | 안티바이러스 실시간 검사 | [2장](#2-windows-안티바이러스--microsoft-defender) |
| `path too long`, 설치 중 경로 길이 오류 (Windows) | MAX_PATH(260자) 제한 | [3.2](#32-긴-경로long-path-활성화-windows에서-더-자주-필요) |
| "개발자 모드를 켜야 하나요?" | 대부분 불필요 | [3.1](#31-windows-개발자-모드-대부분-불필요) |

빠른 자가 점검(환경 준비가 됐는지):

```bash
uv run python check_env.py
```

---

## 1. TLS 검사 프록시(Zscaler 등)와 사설 인증서

### 1.1 무슨 일이 일어나는가

Zscaler, Netskope, 사내 SSL/TLS inspection 프록시 등은 HTTPS 트래픽을 중간에서 풀어 검사한 뒤 **회사 자체 root CA로 다시 서명**해 전달합니다. 그런데 `uv`, `pip`, Python, Azure SDK는 기본적으로 자체 번들 인증서(또는 표준 신뢰 저장소)만 신뢰하므로, **회사 root CA를 모르면 "신뢰할 수 없는 인증서"로 보고 연결을 끊습니다.** 그래서 인터넷은 브라우저로 잘 되는데 `uv sync`만 실패하는 상황이 생깁니다.

근본 해결은 하나입니다: **회사 root CA를 도구들이 신뢰하도록 등록**하는 것. 아래 순서대로 진행하세요.

### 1.2 1단계 — 회사 root CA 인증서 확보

- 가장 확실한 방법은 **사내 IT/보안팀에 "개발 도구용 root CA 인증서(.pem 또는 .crt)"를 요청**하는 것입니다.
- 직접 추출하려면 브라우저에서 `https://pypi.org` 접속 → 자물쇠 아이콘 → 인증서 보기 → 인증 경로 최상위(Root)를 Base-64(PEM)로 내보내기.
- 받은 파일은 PEM 형식(텍스트, `-----BEGIN CERTIFICATE-----`로 시작)이어야 합니다. DER(바이너리)면 PEM으로 변환하세요: `openssl x509 -inform der -in corp.cer -out corp.pem`.

이후 예시는 인증서 파일을 `corp-root.pem`(원하는 경로)로 둔다고 가정합니다.

### 1.3 2단계 — OS 신뢰 저장소에 등록 (가장 권장)

OS 신뢰 저장소에 한 번 등록해 두면 `--system-certs`를 쓰는 uv는 물론 브라우저, az CLI 등 OS 저장소를 참조하는 도구가 모두 신뢰하게 됩니다.

Windows (관리자 PowerShell):

```powershell
Import-Certificate -FilePath "C:\certs\corp-root.pem" -CertStoreLocation Cert:\LocalMachine\Root
```

macOS:

```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ~/Downloads/corp-root.pem
```

Linux (Debian/Ubuntu):

```bash
sudo cp corp-root.pem /usr/local/share/ca-certificates/corp-root.crt
sudo update-ca-certificates
```

Linux (RHEL/Fedora):

```bash
sudo cp corp-root.pem /etc/pki/ca-trust/source/anchors/corp-root.pem
sudo update-ca-trust
```

### 1.4 3단계 — uv가 인증서를 신뢰하게

uv는 기본적으로 번들된 Mozilla 루트 인증서만 신뢰합니다. 위에서 OS 저장소에 등록했다면, **uv가 OS 저장소를 쓰도록** 켜 주는 것이 가장 깔끔합니다.

**방법 A (권장): 시스템 인증서 저장소 사용** — `--system-certs` 플래그 또는 `UV_SYSTEM_CERTS=true` 환경 변수.

Windows (PowerShell):

```powershell
$env:UV_SYSTEM_CERTS = "true"   # 현재 세션
uv sync
# 새 터미널에도 적용하려면: setx UV_SYSTEM_CERTS true  (이후 새 터미널부터)
```

macOS / Linux (bash, zsh):

```bash
export UV_SYSTEM_CERTS=true     # 현재 세션 (영구 적용은 ~/.zshrc 또는 ~/.bashrc에 추가)
uv sync
```

> 예전 자료에 보이는 `UV_NATIVE_TLS=true` / `--native-tls`는 같은 기능의 **구(舊) 이름이며 현재는 deprecated**입니다. 새로 설정한다면 `UV_SYSTEM_CERTS` / `--system-certs`를 쓰세요.

**방법 B: 인증서 번들 파일을 직접 지정** — OS 저장소에 등록하기 어려울 때 `SSL_CERT_FILE`로 PEM 번들을 가리킵니다.

Windows (PowerShell):

```powershell
$env:SSL_CERT_FILE = "C:\certs\corp-root.pem"
uv sync
```

macOS / Linux (bash, zsh):

```bash
export SSL_CERT_FILE=/path/to/corp-root.pem
uv sync
```

> [!IMPORTANT]
> `SSL_CERT_FILE`(및 `SSL_CERT_DIR`)은 **기본 인증서를 완전히 대체**합니다. 즉 그 파일에 들어 있는 인증서만 신뢰합니다. 그래서 회사 root CA 한 장만 넣으면 일반 공개 사이트(pypi 등) 검증이 깨질 수 있습니다. 안전하게 하려면 **표준 루트 번들 + 회사 root CA를 합친 PEM**을 만들어 지정하세요. 이런 번거로움이 없는 **방법 A(`UV_SYSTEM_CERTS`)를 먼저 시도**하는 것을 권장합니다.

표준 번들과 합치는 예 (회사 CA를 certifi 번들 뒤에 이어붙임):

```bash
# macOS / Linux 예시
cat "$(uv run python -c 'import certifi; print(certifi.where())')" corp-root.pem > corp-bundle.pem
export SSL_CERT_FILE=$PWD/corp-bundle.pem
```

### 1.5 실행 런타임: az login과 모델 호출 인증서

`uv sync`(설치)가 성공해도, **실습 실행 중 실제 HTTPS 호출**(`az login`, Foundry 모델 호출)이 같은 이유로 다시 막힐 수 있습니다. 1.3에서 **OS 신뢰 저장소에 등록했다면 대부분 함께 해결**됩니다. 그래도 남으면 라이브러리별로 아래를 설정하세요.

- **Azure CLI / Azure SDK(`az login`, `azure-identity`)**: `requests` 기반이라 `REQUESTS_CA_BUNDLE`을 따릅니다.

  Windows (PowerShell):

  ```powershell
  $env:REQUESTS_CA_BUNDLE = "C:\certs\corp-root.pem"
  az login
  ```

  macOS / Linux:

  ```bash
  export REQUESTS_CA_BUNDLE=/path/to/corp-root.pem
  az login
  ```

- **모델 호출(`openai` SDK → 내부적으로 `httpx`)**: 환경에 따라 `SSL_CERT_FILE`만으로 안 잡힐 수 있습니다. 이때 가장 확실한 방법은 **OS 신뢰 저장소를 그대로 쓰는 `truststore` 패키지**입니다. 이 저장소는 코드를 고치지 않아도 되도록, 실행 전에 한 번 주입하는 방식을 쓸 수 있습니다.

  ```bash
  uv add truststore
  ```

  실행 시 truststore를 먼저 주입(코드 변경 없이):

  ```bash
  uv run python -c "import truststore; truststore.inject_into_ssl(); import runpy; runpy.run_path('Chapter2_Foundry_Fundamentals/2.1_check_foundry_settings.py', run_name='__main__')"
  ```

  > truststore는 Python의 TLS 검증을 **OS 신뢰 저장소**로 라우팅하므로, 1.3에서 회사 root CA를 등록해 두기만 하면 별도 번들 파일 없이 동작합니다. 상시로 쓰려면 각 실습 진입점에서 `import truststore; truststore.inject_into_ssl()`을 가장 먼저 호출하도록 두는 방법도 있습니다(원하면 공통 부트스트랩에 넣어 드릴 수 있습니다).

### 1.6 프록시와 타임아웃

프록시를 강제하는 환경이면 표준 프록시 변수를 설정합니다(uv, pip, Azure SDK 공통).

macOS / Linux:

```bash
export HTTPS_PROXY=http://proxy.company.com:8080
export HTTP_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1,.company.local
```

Windows (PowerShell): `$env:HTTPS_PROXY = "http://proxy.company.com:8080"` 형태로 동일하게 설정합니다.

`uv sync`가 느리거나 `Connection reset by peer`로 중단되면 HTTP 타임아웃을 늘립니다(기본 30초).

```bash
export UV_HTTP_TIMEOUT=120
```

### 1.7 최후의 수단 (보안 약화 — 비권장)

위 방법으로 안 되고 **임시로** 설치만 통과시켜야 한다면 특정 호스트의 검증을 끌 수 있습니다. **인증서를 신뢰하는 게 아니라 검증을 끄는 것**이라 중간자 위험에 노출되니, 사내 정책을 확인하고 임시로만 쓰세요.

```bash
uv sync --allow-insecure-host pypi.org --allow-insecure-host files.pythonhosted.org
# 환경 변수로는 UV_INSECURE_HOST
```

---

## 2. Windows 안티바이러스 / Microsoft Defender

### 2.1 증상

- `uv sync`가 유난히 느림(수 분), 가끔 "다른 프로세스가 파일을 사용 중"으로 실패.
- uv가 내려받은 Python 실행 파일이나 패키지가 **격리/삭제**되거나 간헐적 권한 오류.

이는 실시간 검사가 수천 개의 작은 파일(가상환경/캐시)을 매번 스캔하면서 생깁니다.

### 2.2 해결 순서

1. **먼저 IT 정책 확인.** 회사가 관리(Intune/GPO)하는 Defender나 타사 백신은 로컬에서 바꿔도 무시되거나 되돌려집니다. 이 경우 IT에 **개발 폴더 예외**를 요청하세요. Microsoft도 일반적으로는 "예외를 둘 필요가 없다"고 안내하므로, 예외는 실제로 성능/오작동 문제가 있을 때만 최소 범위로 둡니다.
2. **(권장 대안) Windows 11이면 Dev Drive 고려.** Microsoft는 광범위한 폴더 예외보다 **Dev Drive + 성능 모드**를 권장합니다. 성능 모드는 검사를 끄지 않고 비동기로 미뤄, 예외(검사 자체 차단)보다 보호 수준이 높으면서 빠릅니다.
3. **필요 시 폴더 예외 추가.** 아래 세 경로만 최소로 제외합니다.

### 2.3 제외할 경로

uv가 실제로 쓰는 경로를 명령으로 확인하세요(기본값은 사용자/버전에 따라 다를 수 있음).

```bash
uv cache dir      # 패키지 캐시 (기본 예: %LOCALAPPDATA%\uv\cache)
uv python dir     # uv가 관리하는 Python 설치 위치
```

- uv 캐시 디렉터리 (`uv cache dir`)
- uv 관리 Python 디렉터리 (`uv python dir`)
- 프로젝트의 `.venv` 폴더

GUI로 추가: **Windows 보안 → 바이러스 및 위협 방지 → 설정 관리 → 제외 → 제외 추가/제거 → 폴더**.

PowerShell(관리자, 로컬 Defender 한정):

```powershell
Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\uv\cache"
Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\uv\python"
Add-MpPreference -ExclusionPath "C:\path\to\repo\.venv"
```

> [!CAUTION]
> 시스템 temp 폴더(`%Temp%` 등)나 사용자 프로파일 전체를 통째로 제외하지 마세요. 악성코드가 자주 쓰는 경로라 보안 구멍이 됩니다. 제외는 **개발 도구 전용 경로만 최소로**.

---

## 3. Windows 개발자 모드와 긴 경로

### 3.1 Windows 개발자 모드: 대부분 불필요

결론부터: **이 실습(uv, Python CLI 개발)에는 개발자 모드가 필요 없습니다.** Microsoft 공식 문서도 "일상적인 사용(게임, 웹, 메일, Office)에는 개발자 모드를 켤 필요가 없다"고 안내합니다. 개발자 모드는 주로 **UWP/.NET MAUI 같은 패키지 앱을 배포, 사이드로드**할 때 필요합니다.

uv 관점에서도 불필요합니다. uv의 기본 패키지 설치 방식(link-mode)은 **Windows에서 hardlink**라 심볼릭 링크 권한이 필요 없습니다. (개발자 모드는 관리자 없이 심볼릭 링크 생성을 허용하는 용도인데, uv는 그 경로를 기본으로 쓰지 않습니다.)

그래도 켜야 한다면: **설정 → 시스템 → 개발자용**(Windows 11 25H2 이상은 **설정 → 시스템 → 고급**의 "개발자용" 섹션) → **개발자 모드** 토글 → 경고 확인 후 "예". **관리자 권한이 필요**하고, 회사 관리 기기는 비활성화돼 있을 수 있습니다.

만약 어떤 패키지가 심볼릭 링크 때문에 설치에 실패한다면, 개발자 모드 대신 link-mode를 바꾸는 편이 간단합니다.

```bash
uv sync --link-mode=copy
# 환경 변수로는 UV_LINK_MODE=copy
```

### 3.2 긴 경로(Long Path) 활성화 (Windows에서 더 자주 필요)

개발자 모드보다 **실제로 더 자주 필요한 것은 "긴 경로" 허용**입니다. Windows 기본 경로 길이 제한(MAX_PATH, 260자) 때문에, 깊은 가상환경/패키지 경로에서 `path too long`류 오류가 날 수 있습니다.

활성화 방법 중 하나:

- **설정 → 시스템 → 고급(이전 "개발자용") → "긴 경로 사용(Enable long paths)"** 토글, 또는
- 관리자 PowerShell에서 레지스트리 설정 후 재부팅:

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

설정 후 터미널(가능하면 PC)을 재시작하고 `uv sync`를 다시 실행하세요.

---

## 4. 그 밖에 자주 겪는 것

- **명령을 바꿨는데 안 먹힘**: 환경 변수(PATH, `UV_*`)를 바꾼 뒤에는 **새 터미널**을 여세요. VS Code 통합 터미널도 새로 열어야 반영됩니다.
- **`uv`를 못 찾음**: 설치 직후면 터미널을 새로 열고 `uv --version` 확인. 자세한 설치는 [최상위 README](./README.md#2-uv-설치와-python-3119-python은-uv가-자동-관리)를 참고하세요.
- **Streamlit 앱이 경고만 쏟아지고 화면이 안 뜸**: `uv run <파일>`이 아니라 `uv run streamlit run <파일>`로 실행해야 합니다(5장).
- **`.env` 값 점검**: `uv run python check_env.py`로 필수/선택 항목이 채워졌는지 한 번에 확인하세요.

---

## 참고 문서

- uv — TLS certificates: <https://docs.astral.sh/uv/concepts/authentication/certificates/>
- uv — Environment variables(`UV_SYSTEM_CERTS`, `SSL_CERT_FILE`, `UV_INSECURE_HOST`, 프록시, `UV_HTTP_TIMEOUT`, `UV_LINK_MODE` 등): <https://docs.astral.sh/uv/reference/environment/>
- Microsoft Learn — Windows 개발자 모드: <https://learn.microsoft.com/windows/advanced-settings/developer-mode>
- Microsoft Learn — Defender 안티바이러스 제외 구성: <https://learn.microsoft.com/defender-endpoint/configure-extension-file-exclusions-microsoft-defender-antivirus>
- Microsoft Learn — Dev Drive 성능 모드: <https://learn.microsoft.com/defender-endpoint/microsoft-defender-endpoint-antivirus-performance-mode>
