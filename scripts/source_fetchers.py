from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, List, Optional

import requests

from m3u_parser import parse_m3u_text, normalized_channel_name

UDP_PATH_RE = re.compile(r"/udp/(\d{1,3}(?:\.\d{1,3}){3}:\d{2,5})", re.IGNORECASE)
RTP_RE = re.compile(r"^rtp://(\d{1,3}(?:\.\d{1,3}){3}:\d{2,5})$", re.IGNORECASE)
UDP_RE = re.compile(r"^udp://@?(\d{1,3}(?:\.\d{1,3}){3}:\d{2,5})$", re.IGNORECASE)


@dataclass
class SourceRecord:
    source_name: str
    tvg_id: str
    tvg_name: str
    title: str
    group: str
    raw_url: str
    multicast: Optional[str]


def apply_string_replacements(text: str, replacements: Dict[str, str]) -> str:
    out = text
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out


def extract_multicast(url: str) -> Optional[str]:
    m = UDP_PATH_RE.search(url)
    if m:
        return m.group(1)

    m = RTP_RE.match(url.strip())
    if m:
        return m.group(1)

    m = UDP_RE.match(url.strip())
    if m:
        return m.group(1)

    return None


def fetch_text(url: str, timeout_sec: int, headers: Dict[str, str]) -> str:
    resp = requests.get(url, timeout=timeout_sec, headers=headers)
    resp.raise_for_status()
    return resp.text


def fetch_source_records(source_cfg: Dict) -> List[SourceRecord]:
    url = source_cfg["url"]
    timeout_sec = int(source_cfg.get("request", {}).get("timeout_sec", 20))
    headers = source_cfg.get("request", {}).get("headers", {}) or {}

    raw = fetch_text(url, timeout_sec=timeout_sec, headers=headers)

    rules = source_cfg.get("rules", {}) or {}
    replacements = rules.get("string_replacements", {}) or {}
    if replacements:
        raw = apply_string_replacements(raw, replacements)

    parsed = parse_m3u_text(raw)
    include_keywords = [x.lower() for x in (rules.get("include_keywords", []) or [])]
    exclude_keywords = [x.lower() for x in (rules.get("exclude_keywords", []) or [])]

    records: List[SourceRecord] = []
    for ch in parsed.channels:
        title = ch.title or ""
        group = ch.attributes.get("group-title", "")
        tvg_id = ch.attributes.get("tvg-id", "")
        tvg_name = ch.attributes.get("tvg-name", "")
        url_line = ch.raw_url.strip()

        haystack = f"{title} {group} {tvg_id} {tvg_name} {url_line}".lower()
        if include_keywords and not any(k in haystack for k in include_keywords):
            continue
        if exclude_keywords and any(k in haystack for k in exclude_keywords):
            continue

        records.append(
            SourceRecord(
                source_name=source_cfg.get("name", "unknown"),
                tvg_id=tvg_id,
                tvg_name=tvg_name,
                title=title,
                group=group,
                raw_url=url_line,
                multicast=extract_multicast(url_line),
            )
        )

    return records


def build_key(record: SourceRecord, normalize_cfg: Dict[str, bool], alias_map: Dict[str, str]) -> List[str]:
    candidates = [record.tvg_id, record.tvg_name, record.title]
    keys: List[str] = []
    for raw in candidates:
        if not raw:
            continue
        n = normalized_channel_name(
            raw,
            remove_spaces=bool(normalize_cfg.get("remove_spaces", True)),
            remove_dash=bool(normalize_cfg.get("remove_dash", True)),
            lower=bool(normalize_cfg.get("lower", True)),
        )
        n = alias_map.get(n, n)
        if n and n not in keys:
            keys.append(n)
    return keys
