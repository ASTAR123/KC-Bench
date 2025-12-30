"""
Enrich doc_records.jsonl by crawling URLs and producing cleaned text/corpus entries.

Input  (default: Environment/browsecomp/doc_records.jsonl):
    {"docid": "...", "url": "...", "text": "<snippet>"}

Output (default: Environment/browsecomp/corp.jsonl):
    {"docid": "...", "url": "...", "text": "<cleaned or summarized text>"}

Summary is optional; if OPENAI_API_KEY (and optionally OPENAI_API_BASE, SUMMARY_MODEL_ID)
are set, the script will try to summarize the fetched content to reduce redundancy.
Otherwise it will store cleaned raw text (snippet + page content).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup


DEFAULT_INPUT = "Environment/browsecomp/doc_records.jsonl"
DEFAULT_OUTPUT = "Environment/browsecomp/corp.jsonl"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def clean_text(text: str) -> str:
    if not text:
        return ""
    import re

    # Remove obvious binary links / images
    text = re.sub(r"https?://\\S+\\.(?:png|jpg|jpeg|gif|webp|svg)(\\?\\S*)?", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"!\\[[^\\]]*\\]\\([^)]+\\)", " ", text)  # Markdown images
    # Strip generic URLs
    text = re.sub(r"https?://\\S+", " ", text)
    text = re.sub(r"\\bwww\\.[^\\s]+\\b", " ", text)
    # Remove boilerplate/common junk tokens
    boilerplate_keywords = [
        "cookie", "privacy", "subscribe", "sign up", "newsletter", "accept all",
        "terms of service", "enable javascript", "advertisement", "promo",
    ]
    for kw in boilerplate_keywords:
        text = re.sub(kw, " ", text, flags=re.IGNORECASE)
    # Collapse whitespace
    text = " ".join(text.split())
    return text.strip()


def link_crawl(url: str, timeout: int = 60) -> Optional[str]:
    try:
        resp = requests.get(f"https://r.jina.ai/{url}", headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and resp.text:
            return resp.text.strip()
    except Exception:
        return None
    return None


def fetch_page(url: str, timeout: int = 60) -> Optional[str]:
    crawled = link_crawl(url, timeout)
    if crawled:
        return crawled
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        ct = resp.headers.get("Content-Type", "").lower()
        if "pdf" in ct:
            return f"[pdf content omitted: {url}]"
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "meta", "link", "noscript"]):
            tag.decompose()
        for br in soup.find_all(["br", "p", "div", "li", "section", "article"]):
            br.append("\\n")
        raw_text = soup.get_text(separator="\\n", strip=True)
        lines = [ln.strip() for ln in raw_text.split("\\n") if ln.strip()]
        # Filter out very short boilerplate lines
        filtered = [ln for ln in lines if len(ln.split()) >= 3]
        # Deduplicate consecutive identical lines
        deduped: List[str] = []
        for ln in filtered:
            if not deduped or deduped[-1] != ln:
                deduped.append(ln)
        return "\\n".join(deduped)
    except Exception:
        return None


def summarize_text(text: str, model_id: str, api_base: str, api_key: str) -> Optional[str]:
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "You are a concise summarizer. Produce a clear, self-contained summary."},
            {"role": "user", "content": text[:]},
        ],
        "temperature": 0.2,
        "max_tokens": 400,
    }
    try:
        resp = requests.post(
            f"{api_base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        return message.get("content")
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl doc_records.jsonl and emit corp.jsonl with cleaned/summarized text.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to doc_records.jsonl")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Path to corp.jsonl")
    parser.add_argument("--no-summarize", action="store_true", help="Skip summarization even if API keys are set.")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N records (for testing).")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    model_id = os.getenv("SUMMARY_MODEL_ID", "gpt-4o-mini")
    do_summarize = bool(api_key) and not args.no_summarize

    written = 0
    with output_path.open("w", encoding="utf-8") as fout:
        for idx, record in enumerate(read_jsonl(input_path), start=1):
            if args.limit and idx > args.limit:
                break
            url = record.get("url") or ""
            docid = record.get("docid") or url or f"doc_{idx}"
            snippet = record.get("text") or ""

            page_text = fetch_page(url) if url else ""
            combined = "\\n\\n".join([snippet, page_text]).strip()
            cleaned = clean_text(combined)

            final_text = cleaned
            if do_summarize and cleaned:
                summary = summarize_text(cleaned, model_id=model_id, api_base=api_base, api_key=api_key)
                if summary:
                    final_text = summary

            corp_entry = {"docid": docid, "url": url, "text": final_text}
            fout.write(json.dumps(corp_entry, ensure_ascii=False) + "\\n")
            written += 1

    print(f"Wrote {written} records to {output_path}")


if __name__ == "__main__":
    main()
