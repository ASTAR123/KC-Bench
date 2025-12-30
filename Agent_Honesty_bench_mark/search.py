from __future__ import annotations

import json
import os
import pickle
import string
import concurrent.futures  # 必须显式导入这个模块
from pathlib import Path
from typing import Any, Dict, List, Optional

from rank_bm25 import BM25Okapi
from smolagents import tool

try:
    import nltk
    from nltk.stem import PorterStemmer
    from nltk.corpus import stopwords
except ImportError:
    raise ImportError("nltk is required. Please run: pip install nltk")

# =========================================================
# Index configuration
# =========================================================
INDEX_ROOT = Path("Environment/browsecomp/academic_python_index")
NLTK_DATA_DIR = Path("Environment/browsecomp/nltk_data")

_STEMMER = PorterStemmer()
_STOPWORDS: Optional[set[str]] = None
_TRANSLATOR = str.maketrans("", "", string.punctuation)

# --- 优化后的全局缓存策略 ---
# _BM25_CACHE: 只存轻量的搜索模型 (占用内存小)
# _TEXT_CACHE: 存文档正文 (占用内存大，按需加载)
_BM25_CACHE: Dict[str, Any] = {}
_TEXT_CACHE: Dict[str, List[Any]] = {}


def _ensure_nltk_data() -> None:
    global _STOPWORDS
    if NLTK_DATA_DIR.exists():
        nltk.data.path.append(str(NLTK_DATA_DIR.resolve()))

    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        # 如果找不到，尝试在线下载（可选）或报错
        try:
            nltk.download('stopwords', quiet=True)
        except:
            pass # 忽略下载错误，后面抛出更具体的异常
            
    try:
        if _STOPWORDS is None:
            _STOPWORDS = set(stopwords.words("english"))
    except LookupError as exc:
        raise RuntimeError(
            f"NLTK stopwords not found. Place NLTK data under {NLTK_DATA_DIR} "
            "or run `nltk.download('stopwords')`."
        ) from exc


def _academic_tokenizer(text: str) -> List[str]:
    if not text:
        return []
    if _STOPWORDS is None:
        _ensure_nltk_data()
    text = text.lower()
    text = text.translate(_TRANSLATOR)
    tokens = text.split()
    return [_STEMMER.stem(t) for t in tokens if t not in _STOPWORDS]


def _load_bm25_only(shard_name: str, model_path: Path) -> None:
    """[优化] 只加载轻量的 BM25 模型，不加载正文"""
    if shard_name in _BM25_CACHE:
        return
    try:
        with open(model_path, "rb") as f:
            bm25 = pickle.load(f)
        _BM25_CACHE[shard_name] = bm25
    except Exception as e:
        print(f"Warning: Failed to load BM25 for {shard_name}: {e}")


def _get_shard_top_indices(shard_name: str, tokenized_query: List[str], top_n: int) -> List[Dict[str, Any]]:
    """在单个 Shard 中计算分数，返回索引而非全文"""
    bm25 = _BM25_CACHE.get(shard_name)
    if not bm25:
        return []
    
    scores = bm25.get_scores(tokenized_query)
    # 获取分数最高的 top_n 个 (index, score)
    top_indices = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_n]
    
    return [
        {"shard": shard_name, "idx": idx, "score": float(score)} 
        for idx, score in top_indices if score > 0
    ]


def _fetch_document_text(shard_name: str, doc_idx: int, root: Path) -> Dict[str, Any]:
    """[优化] 只有当文档确定入选 Top K 后，才加载其正文"""
    if shard_name not in _TEXT_CACHE:
        data_path = root / shard_name / "corpus_data.pkl"
        try:
            with open(data_path, "rb") as f:
                _TEXT_CACHE[shard_name] = pickle.load(f)
        except Exception as e:
            return {"docid": "error", "text": f"Error loading shard content: {e}"}
            
    try:
        doc = _TEXT_CACHE[shard_name][doc_idx]
        content = doc.get("text") or doc.get("contents") or doc.get("body") or doc.get("content") or ""
        url = doc.get("url") or doc.get("id") or "local"
        doc_id = doc.get("doc_id") or doc.get("id") or url
        return {
            "docid": doc_id,
            "text": content
        }
    except IndexError:
        return {"docid": "error", "text": "Document index out of range"}


@tool
def search(query: str) -> str:
    """
    Search the index and return top-5 hits.
    Optimized to reduce IO by loading models first, and content only on demand.
    
    Args:
        query: Search query string
    Returns:
        JSON string containing list of search results
    """
    top_k = 5
    try:
        _ensure_nltk_data()
        if not INDEX_ROOT.exists():
            # 这里可以根据实际情况改为返回空列表而不是报错
            return json.dumps({"status": "error", "result": f"Index root not found: {INDEX_ROOT}"})

        tokenized_query = _academic_tokenizer(query)
        if not tokenized_query:
            return json.dumps(
                {"status": "ok", "tool": "search", "args": {"query": query}, "result": []},
                ensure_ascii=False,
            )

        # 1. 扫描所有 Shard 目录
        shards_info = []
        for shard_dir in sorted(INDEX_ROOT.glob("shard_*")):
            if shard_dir.is_dir():
                model_path = shard_dir / "bm25_model.pkl"
                if model_path.exists():
                    shards_info.append((shard_dir.name, model_path))

        # 2. 并行加载 BM25 模型 (利用多线程加速 IO)
        # 注意：pickle加载主要受限于磁盘IO，多线程通常有效
        if shards_info:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(shards_info))) as executor:
                futures = [executor.submit(_load_bm25_only, name, path) for name, path in shards_info]
                concurrent.futures.wait(futures)

        # 3. 计算所有 Shard 的候选集
        all_candidates = []
        for name, _ in shards_info:
            all_candidates.extend(_get_shard_top_indices(name, tokenized_query, top_k))

        # 4. 全局排序，选出最终 Top K
        final_top_hits = sorted(all_candidates, key=lambda x: x['score'], reverse=True)[:top_k]

        # 5. 最后才去加载正文 (Lazy Loading)
        results = []
        for hit in final_top_hits:
            doc_info = _fetch_document_text(hit['shard'], hit['idx'], INDEX_ROOT)
            doc_info['score'] = hit['score']
            results.append(doc_info)

        return json.dumps(
            {
                "status": "ok",
                "tool": "search",
                "args": {"query": query, "top_k": top_k},
                "result": results,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        # 捕获所有异常以防止 Agent 崩溃
        return json.dumps(
            {
                "status": "error",
                "tool": "search",
                "args": {"query": query},
                "result": str(exc),
            },
            ensure_ascii=False,
        )


if __name__ == "__main__":
    # 测试代码
    import time
    print("Searching...")
    start_time = time.time()
    res = search("learning institution 2002 three-day event Thursday Saturday support group 2003 graduation ceremony fourth Sunday month 2022 article website trip students academic department plants 7 days after article ceremony tribute bank university official 2023 capital cit")
    end_time = time.time()
    print(f"Result: {res}")
    print(f"Time taken: {end_time - start_time:.4f} seconds")