import math
from pathlib import Path
from typing import Iterable

from .client import get_openai_client, run_single_turn_prompt
from .config import get_settings
from .tracing import foundry_span


def chunk_text(text: str, *, chunk_size: int = 700, overlap: int = 120) -> list[str]:
    # 긴 문서를 한 번에 넣지 않고 검색 가능한 작은 조각으로 나눕니다.
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _cosine(left: list[float], right: list[float]) -> float:
    # 두 embedding vector가 얼마나 비슷한지 계산해 관련 문서를 고릅니다.
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0
    return dot / (left_norm * right_norm)


def embed_texts(texts: Iterable[str], *, scenario_name: str) -> list[list[float]]:
    # 질문과 문서 chunk를 숫자 벡터로 바꿔 서로 비교할 수 있게 합니다.
    settings = get_settings()
    if not settings.embedding_deployment_name:
        raise RuntimeError("FOUNDRY_EMBEDDING_DEPLOYMENT_NAME is required for RAG samples.")

    text_list = list(texts)
    with foundry_span(scenario_name):
        with get_openai_client() as openai:
            print(
                f"\n[임베딩 생성 대기 중] 텍스트 {len(text_list)}개를 벡터로 변환하는 중입니다...",
                flush=True,
            )
            response = openai.embeddings.create(
                model=settings.embedding_deployment_name,
                input=text_list,
            )
    return [item.embedding for item in response.data]


def retrieve_local_context(
    *,
    document_path: str,
    query: str,
    top_k: int = 3,
    scenario_name: str,
) -> list[str]:
    # 질문과 가장 가까운 문서 chunk만 골라 모델 입력 context로 넘깁니다.
    text = Path(document_path).read_text(encoding="utf-8")
    chunks = chunk_text(text)
    vectors = embed_texts([query, *chunks], scenario_name=f"{scenario_name}.embed")
    query_vector = vectors[0]
    chunk_vectors = vectors[1:]
    scored = sorted(
        zip(chunks, chunk_vectors),
        key=lambda item: _cosine(query_vector, item[1]),
        reverse=True,
    )
    return [chunk for chunk, _ in scored[:top_k]]


def answer_with_local_rag(
    *,
    document_path: str,
    query: str,
    scenario_name: str,
) -> str:
    # 검색된 context만 근거로 답하도록 prompt를 구성하는 RAG의 마지막 단계입니다.
    contexts = retrieve_local_context(
        document_path=document_path,
        query=query,
        scenario_name=scenario_name,
    )
    context_block = "\n\n---\n\n".join(contexts)
    return run_single_turn_prompt(
        "You answer only from the provided context. If the context is insufficient, say so clearly.",
        f"Context:\n{context_block}\n\nQuestion: {query}",
        scenario_name=f"{scenario_name}.answer",
    )
