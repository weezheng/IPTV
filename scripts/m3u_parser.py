from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, List, Optional

EXTINF_RE = re.compile(r"^#EXTINF", re.IGNORECASE)
URL_RE = re.compile(r"^(https?|rtsp|rtp|udp)://", re.IGNORECASE)
ATTR_RE = re.compile(r"([A-Za-z0-9\-]+)=\"([^\"]*)\"")


@dataclass
class ChannelBlock:
    extinf_index: int
    url_index: int
    title: str
    attributes: Dict[str, str]
    raw_extinf: str
    raw_url: str


@dataclass
class ParsedM3U:
    lines: List[str]
    channels: List[ChannelBlock]


def parse_extinf(extinf_line: str) -> tuple[Dict[str, str], str]:
    attrs = {k.strip().lower(): v for k, v in ATTR_RE.findall(extinf_line)}
    title = ""
    if "," in extinf_line:
        title = extinf_line.rsplit(",", 1)[1].strip()
    return attrs, title


def parse_m3u_text(content: str) -> ParsedM3U:
    lines = content.splitlines()
    channels: List[ChannelBlock] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if EXTINF_RE.match(line):
            attrs, title = parse_extinf(lines[i])

            j = i + 1
            while j < len(lines):
                candidate = lines[j].strip()
                if not candidate:
                    j += 1
                    continue
                if candidate.startswith("#"):
                    j += 1
                    continue
                if URL_RE.match(candidate):
                    channels.append(
                        ChannelBlock(
                            extinf_index=i,
                            url_index=j,
                            title=title,
                            attributes=attrs,
                            raw_extinf=lines[i],
                            raw_url=lines[j],
                        )
                    )
                    break
                j += 1
        i += 1

    return ParsedM3U(lines=lines, channels=channels)


def load_m3u_file(path: str, encoding: str = "utf-8") -> ParsedM3U:
    with open(path, "r", encoding=encoding) as f:
        return parse_m3u_text(f.read())


def dump_m3u_file(path: str, parsed: ParsedM3U, encoding: str = "utf-8") -> None:
    with open(path, "w", encoding=encoding, newline="\n") as f:
        f.write("\n".join(parsed.lines) + "\n")


def normalized_channel_name(name: str, *, remove_spaces: bool, remove_dash: bool, lower: bool) -> str:
    s = name.strip()
    if remove_spaces:
        s = re.sub(r"\s+", "", s)
    if remove_dash:
        s = s.replace("-", "")
    if lower:
        s = s.lower()
    return s


def channel_keys(block: ChannelBlock, normalize_cfg: Dict[str, bool], alias_map: Dict[str, str]) -> List[str]:
    keys: List[str] = []
    candidates = [
        block.attributes.get("tvg-id", ""),
        block.attributes.get("tvg-name", ""),
        block.title,
    ]

    for raw in candidates:
        if not raw:
            continue
        n = normalized_channel_name(
            raw,
            remove_spaces=bool(normalize_cfg.get("remove_spaces", True)),
            remove_dash=bool(normalize_cfg.get("remove_dash", True)),
            lower=bool(normalize_cfg.get("lower", True)),
        )
        mapped = alias_map.get(n, n)
        if mapped and mapped not in keys:
            keys.append(mapped)

    return keys
