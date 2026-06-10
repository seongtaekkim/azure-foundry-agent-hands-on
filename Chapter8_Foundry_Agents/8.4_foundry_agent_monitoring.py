# Run: uv run Chapter8_Foundry_Agents/8.4_foundry_agent_monitoring.py
# 학습 포인트: Foundry 포털의 Agent Monitoring 화면에서 실행, 토큰, 평가, App Insights 연결 상태를 확인합니다.
# 초보자 읽기: 8.1 또는 8.2에서 만든 Foundry Agent를 포털에서 열고 모니터링 탭의 운영 메트릭과 평가 영역을 확인합니다.
import os

import _bootstrap  # noqa: F401


AGENT_NAMES = ["chapter-8-1-rag-agent", "chapter-8-2-knowledge-base-agent", "chapter-8-3-learn-mcp-agent"]


if __name__ == "__main__":
    app_insights_name = os.getenv("FOUNDRY_APPLICATIONINSIGHTS_NAME", "appi-foundry-hands-on")
    print("Foundry Agent Monitoring 읽기 실습")
    print("=" * 60)
    print("이 파일은 모델을 새로 호출하지 않고, Foundry 포털의 에이전트 모니터링 화면을 읽는 순서를 안내합니다.\n")

    print("1. 먼저 8.1, 8.2 또는 8.3 실습에서 agent version을 남겨 둡니다.")
    print('   환경 변수 설정 (Windows PowerShell): $env:FOUNDRY_KEEP_AGENT="true"')
    print("   환경 변수 설정 (macOS/Linux bash·zsh): export FOUNDRY_KEEP_AGENT=true")
    print("   실행 예: python ./Chapter8_Foundry_Agents/8.1_create_and_run_foundry_agent.py")
    print("   실행 예: python ./Chapter8_Foundry_Agents/8.2_create_foundry_agent_with_knowledge_base.py")
    print("   실행 예: python ./Chapter8_Foundry_Agents/8.3_create_foundry_agent_with_mcp.py")
    print("   (Windows에서는 경로 구분자로 역슬래시 \\ 를 사용해도 됩니다.)")
    print(f"   포털에서 확인할 agent 이름 후보: {', '.join(AGENT_NAMES)}\n")

    print("2. Microsoft Foundry 포털에서 해당 agent를 엽니다.")
    print("   경로: Foundry project > 에이전트 > agent 이름 선택 > 모니터링 탭\n")

    print("3. 상단 날짜 범위를 7일 또는 1개월로 맞춘 뒤 아래 항목을 확인합니다.")
    print("   - 운영 메트릭: 총 토큰 사용량, 에이전트 실행 횟수")
    print("   - 실행 및 토큰 메트릭: 시간대별 호출 수와 토큰 사용량")
    print("   - 평가: 자동화된 평가가 구성되어 있는지")
    print("   - 예약된 평가 / 레드 팀 실행: 안전성 점검 자동화가 설정되어 있는지")
    print("   - App Insights 연결 배너: 더 자세한 telemetry를 보려면 연결이 필요한지")
    print(f"   - 연결할 App Insights 후보: {app_insights_name}\n")

    print("4. 데이터가 보이지 않으면 다음을 점검합니다.")
    print("   - 8.1, 8.2 또는 8.3을 FOUNDRY_KEEP_AGENT=true로 실행했는지")
    print("   - 포털의 AI에게 질문 영역에서 테스트 질문을 몇 번 실행했는지")
    print("   - 날짜 범위가 오늘 또는 최근 7일을 포함하는지")
    print("   - 메트릭 반영까지 몇 분 정도 기다렸는지")
    print(f"   - 연결 배너가 보이면 Application Insights 리소스({app_insights_name})를 선택했는지")
    print("   - 상단에 'Application Insights가 활성화되면 생성되는 데이터입니다' 문구가 보이면")
    print("     Foundry 포털에서 해당 agent 또는 project에 Application Insights 연결을 먼저 활성화해야 합니다.")
    print("   - 8.2/8.3 코드는 OpenTelemetry span을 Azure Monitor로 보내지만,")
    print("     Foundry 포털의 agent 추적 탭은 포털에서 App Insights가 연결된 뒤 몇 분 후 표시될 수 있습니다.")

    print("\n학습 목표: 코드를 더 작성하는 것이 아니라, 운영자가 Foundry 안에서 agent 사용량과 품질 신호를 어디서 보는지 익히는 것입니다.")