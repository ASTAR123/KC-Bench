from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from smolagents import tool

BRIGHTDATA_ENDPOINT = "https://api.brightdata.com/request"
DEFAULT_ZONE = "agent"
WEB_UNLOCKER_ZONE = "web_unlocker"  # 用于获取完整网页内容的zone（如果可用）
API_KEY_ENV = "0bb96517032bdd27286742085fd8594f0ff996ab374b66944bdc1916955c0677"  # fallback key, 优先读取环境变量
BRIGHTDATA_ENV_VAR = "BRIGHTDATA_API_KEY"
Time_Out = 60
Top_Results = 5
MAX_CONTENT_CHARS: int | None = None  # None 表示不截断
CORPUS_PATH = "Environment/browsecomp/down_corp.jsonl"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def _pack_query(query: str) -> str:
    return f"q={requests.utils.quote(query)}"


def _make_request(query: str, *, zone: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
    api_key = os.getenv(BRIGHTDATA_ENV_VAR) or API_KEY_ENV
    if not api_key:
        raise RuntimeError(f"Missing API key. Set env {BRIGHTDATA_ENV_VAR}.")

    encoded_query = _pack_query(query)
    target_url = f"https://www.google.com/search?{encoded_query}&brd_json=1&gl=us"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"zone": zone, "url": target_url, "format": "raw"}

    resp = requests.post(BRIGHTDATA_ENDPOINT, headers=headers, json=payload, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

    try:
        return resp.json()
    except Exception:
        return None


def _format_results(snippets: List[str], max_results: int = 5) -> str:
    if not snippets:
        return "No valid search results found."
    formatted = []
    for idx, snippet in enumerate(snippets[: max_results], 1):
        formatted.append(f"Page {idx}: {snippet[:]}")
    return "\n".join(formatted)


def _fetch_page_content(url: str, zone: str = None, timeout: int = 60) -> Optional[str]:
    """使用Bright Data API获取网页的完整文本内容"""
    api_key = os.getenv(BRIGHTDATA_ENV_VAR) or API_KEY_ENV
    if not api_key:
        return None
    
    # 如果没有指定zone，尝试使用Web Unlocker zone
    if zone is None:
        zone = WEB_UNLOCKER_ZONE
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"zone": zone, "url": url, "format": "raw"}
    
    try:
        resp = requests.post(BRIGHTDATA_ENDPOINT, headers=headers, json=payload, timeout=timeout)
        
        # 检查是否是SERP API不支持的错误
        if resp.status_code >= 400:
            error_text = resp.text.lower()
            if "serp api" in error_text or "web unlocker" in error_text:
                # SERP zone不支持访问实际网页，返回None
                return None
            return None
        
        html_content = resp.text
        
        # 检查响应是否是错误消息
        if "isn't supported" in html_content.lower() or "web unlocker" in html_content.lower():
            return None
        return _parse_html_to_text(html_content)
    except Exception as e:
        print(f"Error fetching page content from {url}: {e}")
        return None


def _parse_html_to_text(html_content: str) -> str:
    """将HTML解析为纯文本，尽量保留正文块和换行，避免过度压缩。"""
    soup = BeautifulSoup(html_content, "lxml")
    for tag in soup(["script", "style", "meta", "link", "noscript"]):
        tag.decompose()
    # 为常见块级元素插入换行，方便分段
    for br in soup.find_all(["br", "p", "div", "li", "section", "article"]):
        br.append("\n")
    text = soup.get_text(separator=" ", strip=True)
    # 归一化空白但保留段落感
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    normalized = "\n".join(lines)
    return normalized


def _clean_content(text: str) -> str:
    """
    清洗正文，去掉明显无用的图片/URL碎片，保留可读文本。
    """
    if not text:
        return ""
    import re

    # 去掉图片/资源链接段
    text = re.sub(r"https?://\S+\.(?:png|jpg|jpeg|gif|webp|svg)(\?\S*)?", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)  # Markdown 图片
    # 去掉一般 URL 片段
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\bwww\.[^\s]+\b", " ", text)
    # 压缩多余空白
    text = " ".join(text.split())
    return text.strip()


def _link_crawl(url: str, timeout: int = Time_Out) -> Optional[str]:
    """Use a lightweight link-crawl (Jina reader) to pull main text."""
    try:
        resp = requests.get(f"https://r.jina.ai/{url}", headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and resp.text:
            text = resp.text.strip()
            return text if text else None
    except Exception:
        return None
    return None


def _fetch_full_text(url: str, timeout: int = Time_Out) -> Optional[str]:
    """
    尝试抓取网页并解析为文本：
      1) Link crawl (Jina Reader: r.jina.ai)
      2) Bright Data Web Unlocker
      3) 直连请求
    """
    crawled = _link_crawl(url, timeout)
    if crawled:
        return crawled

    # 2) Web Unlocker
    content = _fetch_page_content(url, WEB_UNLOCKER_ZONE, timeout)
    if content:
        return content

    # 3) 直连
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "").lower()
        if "pdf" in content_type:
            return f"[pdf content omitted: {url}]"
        return _parse_html_to_text(resp.text)
    except Exception:
        return _fetch_page_content(url, WEB_UNLOCKER_ZONE, timeout)


def _extract_snippets(data: Dict[str, Any], fetch_full_content: bool = True) -> tuple[List[str], List[Dict[str, Any]]]:
    """
    提取搜索结果，附带完整网页内容，返回 (snippets, documents)。
    """
    chunk_content_list: List[str] = []
    documents: List[Dict[str, Any]] = []
    seen_urls = set()

    for result_idx, result_item in enumerate(data.get("organic", []), start=1):
        if result_idx > Top_Results:
            break
        url = result_item.get("link") or ""
        title = result_item.get("title") or ""
        source = result_item.get("source") or result_item.get("display_link") or ""
        description = result_item.get("description") or result_item.get("snippet") or ""
        extensions = result_item.get("extensions", [])
        date = result_item.get("date", "") or result_item.get("datePublished", "")
        
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        
        # 获取完整正文
        full_content = ""
        if fetch_full_content:
            full_content = _clean_content(_fetch_full_text(url, Time_Out) or "")
            if MAX_CONTENT_CHARS and len(full_content) > MAX_CONTENT_CHARS:
                full_content = full_content[:MAX_CONTENT_CHARS] + " ..."
        combined_text = _clean_content((description + "\n\n" + full_content).strip() if full_content else description)
        docid = url or title or f"result_{result_idx}"

        doc = {
            "docid": docid,
            "title": title,
            "source": source,
            "url": url,
            "snippet": description,
            "extensions": extensions,
            "date": date,
            "content": full_content,
            "text": combined_text,
        }
        documents.append(doc)

        parts = []
        if title:
            parts.append(f"标题: {title}")
        if source:
            parts.append(f"来源: {source}")
        if description:
            parts.append(f"摘要: {description}")
        if full_content:
            parts.append(f"完整内容: {full_content}")
        else:
            parts.append(f"链接: {url}")

        if parts:
            # 为 Agent 生成更直接可用的片段：标题 + URL + 正文摘要
            snippet_text = "\n".join(parts)
            chunk_content_list.append(snippet_text)
    
    return chunk_content_list, documents


def _append_corpus(documents: List[Dict[str, Any]], path: str = CORPUS_PATH) -> None:
    """将抓取的正文追加保存为 JSONL，便于后续复用。"""
    if not documents:
        return
    try:
        from pathlib import Path

        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "a", encoding="utf-8") as f:
            for doc in documents:
                snippet = doc.get("snippet", "") or ""
                content = doc.get("content", "") or ""
                if not (content or snippet):
                    continue
                # 再次去掉残余 URL 碎片
                cleaned_snippet = _clean_content(snippet)
                cleaned_content = _clean_content(content)
                combined_text = (cleaned_snippet + "\n\n" + cleaned_content).strip() if cleaned_snippet else cleaned_content
                if not combined_text:
                    combined_text = doc.get("text", "")
                record = {
                    "docid": doc.get("docid") or doc.get("url", "") or doc.get("title", ""),
                    "url": doc.get("url", ""),
                    "text": combined_text,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"Warning: failed to append corpus to {path}: {exc}")


@tool
def browsecomp_web_search(query: str ) -> str:
    """
    Google SERP search via Bright Data (returns extracted snippets).

    Args:
        query: Search query string.
    """
    used_zone =  DEFAULT_ZONE
    try:
        response = _make_request(query, zone=used_zone, timeout=Time_Out)
        if response is None:
            raise RuntimeError("Empty or non-JSON response from Bright Data.")
        # 获取完整内容，提取全部有用信息
        snippets, documents = _extract_snippets(response, fetch_full_content=True)
        # 仅保留 docid/url/text 用于保存或上层使用
        doc_records = [
            {"docid": doc.get("docid"), "url": doc.get("url"), "text": doc.get("text", "")}
            for doc in documents
        ]
        _append_corpus(documents, CORPUS_PATH)
        formatted = _format_results(snippets, max_results=Top_Results)
        #将doc_records追加保存到本地
        with open("doc_records.jsonl", "a", encoding="utf-8") as f:
            for doc in doc_records:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n") 
        return json.dumps(
            {
                "status": "ok",
                "tool": "browsecomp_web_search",
                "args": {"query": query, "zone": used_zone, "max_results": Top_Results},
                # "snippets": snippets,
                "documents": doc_records,
                "result": formatted,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "tool": "browsecomp_web_search",
                "args": {"query": query, "zone": used_zone, "max_results": Top_Results},
                "result": str(exc),
            },
            ensure_ascii=False,
        )


if __name__ == "__main__":
    #保存到本地
    with open("response.json", "w", encoding="utf-8") as f:
        json.dump(json.loads(browsecomp_web_search("pizza")), f, ensure_ascii=False, indent=4)
    print("保存成功")
