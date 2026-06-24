# 1장 설명: 모델 호출과 Prompt의 기초

## 이 장의 목적

1장은 Python 프로그램이 Microsoft Foundry에 배포된 언어 모델에 요청을 보내고 응답을 받는 가장 작은 단위를 설명한다. 이후의 agent, RAG, multi-agent도 결국 이 모델 호출을 조합한 것이다.

## 먼저 잡아야 할 그림

```text
Python 코드
  -> endpoint로 HTTPS 요청
  -> 배포된 gpt-5.2가 prompt 처리
  -> 응답과 token usage 반환
```

- endpoint는 요청을 받을 Azure 주소다.
- API key는 호출 권한을 증명하는 비밀 값이다.
- 모델 배포명은 Azure 안에서 실제 배포를 식별하는 이름이다.
- prompt는 모델에 보내는 지시, 질문, 이전 대화 전체다.

## LLM을 이해하는 올바른 관점

LLM은 질문에 해당하는 행을 찾는 데이터베이스가 아니다. 주어진 문맥 다음에 올 토큰을 확률적으로 생성한다. 그래서 자연스럽게 말하면서도 틀릴 수 있다.

모델의 응답은 다음 요소에 영향을 받는다.

- system prompt의 역할과 규칙
- user prompt의 구체성
- 제공된 예시
- 이전 대화 기록
- 모델과 reasoning 설정

## 핵심 파일

| 파일 | 의미 |
| --- | --- |
| `1.5_first_openai_call.py` | 첫 system/user prompt 호출 |
| `1.6.4.4_mulit_turn.py` | 이전 대화를 포함한 2턴 호출 |
| `1.6.3.1_role_assignment.py` | 모델에 역할 부여 |
| `1.6.4.2_few_shot_code.py` | 예시를 주고 같은 규칙 유도 |
| `1.6.4.3_cot_example.py` | 최종 답변을 단계적으로 구성하도록 요청 |
| `1.6.4.5_category_classifier.py` | 텍스트 분류 prompt |
| `1.6.4.6_prompt_engineering_1.py` | 출력 형식 제어 |
| `1.6.4.7_story_generator.py` | 창의적 텍스트 생성 |
| `1.6.4.8_prompt_engineering_2.py` | 여러 제약을 포함한 생성 |

## 단일 호출의 실제 흐름

`1.5_first_openai_call.py`는 공통 함수 `run_single_turn_prompt()`를 부른다.

```text
system prompt + user prompt
  -> run_single_turn_prompt()
  -> run_chat_prompt()
  -> Azure/OpenAI 호환 client
  -> responses.create()
  -> 텍스트 출력
```

System prompt는 애플리케이션이 정한 역할과 규칙이고, user prompt는 사용자의 작업 요청이다. 보안 경계는 아니므로 “system prompt에 금지라고 썼다”만으로 안전이 보장되지는 않는다.

## Multi-turn은 어떻게 기억하는가

`1.6.4.4_mulit_turn.py`는 이전 내용을 `messages` 리스트에 넣고 다음 호출 때 전체를 다시 보낸다.

```text
1차 질문 -> 1차 답변
                |
                v
system + 1차 질문 + 1차 답변 + 2차 질문을 다시 전송
```

모델이 로컬 프로그램 밖에서 영구 기억하는 것이 아니다. 프로그램을 종료하면 리스트가 사라진다. 기록이 길어질수록 입력 토큰, 비용, 응답 시간이 증가한다.

## Prompt 패턴의 의미

- Zero-shot: 정답 예시 없이 지시만 제공
- Few-shot: 입력과 정답 예시를 몇 개 제공
- Role assignment: 전문가 역할과 관점을 지정
- Classification: 허용된 라벨과 출력 형식을 제한
- Constraint: 길이, 언어, 형식, 포함/제외 조건 정의

Few-shot은 모델을 다시 학습시키는 것이 아니다. 그 호출의 context에 예시를 넣는 것이다.

## 초보자가 자주 오해하는 부분

1. 자연스러운 답변이 사실이라는 보장은 없다.
2. 대화 기억은 대부분 이전 메시지를 재전송한 결과다.
3. Prompt 개선만으로 최신 정보나 사내 비공개 지식이 생기지 않는다.
4. 단계적 설명을 요청하는 것과 모델의 비공개 내부 사고를 열람하는 것은 다르다.
5. API key를 코드에 직접 쓰거나 Git에 올리면 안 된다.

## 이 장을 읽고 답할 수 있어야 하는 질문

1. endpoint, API key, 모델 배포명은 각각 무엇인가?
2. system prompt와 user prompt는 어떻게 다른가?
3. Multi-turn에서 이전 답변이 다음 호출에 어떻게 전달되는가?
4. Few-shot과 fine-tuning은 왜 다른가?
5. 대화가 길어질수록 비용이 증가하는 이유는 무엇인가?

## 다음 장과의 연결

1장에서 호출 자체를 배웠지만 각 파일이 연결과 오류 처리를 반복하면 유지보수가 어렵다. 2장에서는 설정, client, trace를 공통 실행 계층으로 정리한다.
