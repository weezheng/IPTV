from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from m3u_parser import ChannelBlock, channel_keys
from source_fetchers import SourceRecord, build_key


@dataclass
class MatchResult:
    total_channels: int
    matched_channels: int
    replaced_urls: int
    unchanged_urls: int
    unmatched_channels: int


def build_source_index(
    records: List[SourceRecord],
    normalize_cfg: Dict,
    alias_map: Dict[str, str],
) -> Dict[str, SourceRecord]:
    index: Dict[str, SourceRecord] = {}
    for record in records:
        keys = build_key(record, normalize_cfg=normalize_cfg, alias_map=alias_map)
        for key in keys:
            if key not in index:
                index[key] = record
    return index


def pick_record_for_block(
    block: ChannelBlock,
    source_index: Dict[str, SourceRecord],
    normalize_cfg: Dict,
    alias_map: Dict[str, str],
) -> Optional[SourceRecord]:
    keys = channel_keys(block, normalize_cfg=normalize_cfg, alias_map=alias_map)
    for k in keys:
        if k in source_index:
            return source_index[k]
    return None


def render_udpxy_url(template: str, local_ip_port: str, multicast: Optional[str], raw_url: str) -> str:
    if multicast:
        return template.format(local_ip_port=local_ip_port, multicast=multicast)
    return raw_url


def apply_matches(
    lines: List[str],
    channels: List[ChannelBlock],
    source_index: Dict[str, SourceRecord],
    normalize_cfg: Dict,
    alias_map: Dict[str, str],
    udpxy_template: str,
    local_ip_port: str,
) -> MatchResult:
    matched = 0
    replaced = 0
    unchanged = 0

    for block in channels:
        record = pick_record_for_block(
            block,
            source_index,
            normalize_cfg=normalize_cfg,
            alias_map=alias_map,
        )
        if not record:
            unchanged += 1
            continue

        matched += 1
        new_url = render_udpxy_url(
            template=udpxy_template,
            local_ip_port=local_ip_port,
            multicast=record.multicast,
            raw_url=record.raw_url,
        )
        old_url = lines[block.url_index].strip()
        if new_url != old_url:
            lines[block.url_index] = new_url
            replaced += 1
        else:
            unchanged += 1

    total = len(channels)
    return MatchResult(
        total_channels=total,
        matched_channels=matched,
        replaced_urls=replaced,
        unchanged_urls=unchanged,
        unmatched_channels=total - matched,
    )
