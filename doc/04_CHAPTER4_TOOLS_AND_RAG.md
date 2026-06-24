# 4장 설명: Tool Use와 RAG

## 이 장의 목적

4장은 모델이 잘하지 못하는 정확한 계산과 비공개 문서 조회를 외부 기능으로 보완한다. 이 저장소의 기술적 중심 장이다.

## Tool Use

Tool은 모델 밖에서 실제 작업을 수행하는 함수나 서비스다. 모델은 도구 선택과 입력 생성을 도울 수 있지만, 프로그램이 허용된 도구와 인자를 검증한 뒤 실행해야 한다.

`4.2.1_multi_tool_agent.py`는 로컬 계산기와 정책 조회 결과를 모델이 종합하게 한다. 정확한 연산은 계산기가 담당하고 자연어 설명은 모델이 담당한다.

## RAG의 목적

RAG는 모델에게 질문과 관련된 외부 문서를 찾아 함께 제공한다. 모델을 재학습하지 않고 최신 사내 지식을 답변에 사용할 수 있다.

```text
준비: 문서 -> chunk -> embedding -> 저장
질문: 질문 embedding -> 유사 chunk 검색 -> prompt에 추가 -> 답변
```

## 핵심 파일

| 파일 | 역할 |
| --- | --- |
| `4.2.1_multi_tool_agent.py` | 로컬 다중 도구 결과 종합 |
| `4.3.2_rag_agent.py` | 텍스트 문서 기반 로컬 RAG |
| `4.3.3_advanced_rag_mistral.py` | PDF 추출 결과를 context로 사용 |
| `4.4.4.2_advanced_rag_index.py` | chunk embedding과 색인 개념 |
| `4.4.4.3_advanced_rag_agent.py` | 검색 문맥 기반 답변 |
| `4.4.4.5_advanced_rag_multiQueryRetriever.py` | 질문을 여러 검색 질의로 확장 |
| `4.4.4.6_multi_tool_agent.py` | 모델이 JSON 도구 계획 생성 |

## `rag.py`의 실제 흐름

1. `chunk_text()`가 문서를 겹치는 조각으로 나눈다.
2. `embed_texts()`가 질문과 chunk를 vector로 바꾼다.
3. cosine similarity가 의미상 가까운 chunk를 정렬한다.
4. 상위 chunk만 context로 선택한다.
5. `run_single_turn_prompt()`가 context에 근거해 답하게 한다.

Chunk가 너무 크면 불필요한 내용이 늘고, 너무 작으면 의미가 잘린다. Overlap은 경계에서 중요한 문장이 끊기는 문제를 줄인다.

## Embedding을 답변 모델과 혼동하지 말 것

Embedding 모델은 텍스트를 숫자 vector로 바꾼다. 답변을 작성하지 않는다. 생성 모델은 검색된 텍스트를 읽고 자연어 답변을 만든다.

## PDF 처리

PDF에서 글자를 추출했다고 문서 이해가 끝난 것은 아니다. 표, 이미지, 다단 레이아웃은 손실될 수 있다. 복잡한 문서는 OCR이나 Document Intelligence, 구조 보존, 페이지·출처 metadata가 필요하다.

## AI router

`4.4.4.6_multi_tool_agent.py`에서는 모델이 사용할 도구 목록을 보고 JSON plan을 만든다. Python이 plan을 parse하고 허용된 로컬 도구만 실행한 뒤 결과를 다시 모델에 전달한다.

모델이 만든 JSON은 신뢰할 수 없는 외부 입력과 같다. Schema, 도구 이름, 인자, 권한, 최대 실행 횟수를 반드시 검증해야 한다.

## RAG의 한계

RAG도 다음 이유로 틀릴 수 있다.

- 관련 문서를 검색하지 못함
- 권한 없는 문서를 잘못 검색함
- 오래된 문서가 상위에 노출됨
- 모델이 검색 문맥을 잘못 해석함
- 출처와 답변이 일치하지 않음

따라서 검색 적중률, 근거성, 출처 정확성, 접근 제어를 별도로 평가해야 한다.

## 이 장을 읽고 답할 수 있어야 하는 질문

1. RAG와 fine-tuning은 어떻게 다른가?
2. Chunk와 overlap은 왜 필요한가?
3. Embedding과 생성 모델의 역할은 무엇인가?
4. 모델이 만든 tool plan을 그대로 실행하면 왜 위험한가?
5. RAG가 환각을 완전히 없애지 못하는 이유는 무엇인가?

## 다음 장과의 연결

4장에서 만든 전문 기능을 5장에서는 여러 역할로 분업시키고 Streamlit 웹 화면으로 제공한다.
