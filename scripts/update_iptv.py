from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import shutil
from typing import Dict, List

import yaml

from m3u_parser import load_m3u_file, dump_m3u_file
from source_fetchers import fetch_source_records
from matcher import apply_matches, build_source_index
from git_sync import has_git_changes, commit_and_push


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="IPTV 地址自动更新工具")
    p.add_argument("--config", default="config.yaml", help="配置文件路径")
    p.add_argument("--local-ip-port", default="", help="覆盖配置中的 udpxy ip:port")
    p.add_argument("--dry-run", action="store_true", help="仅计算，不写文件")
    p.add_argument("--no-git", action="store_true", help="不执行 git 提交推送")
    return p.parse_args()


def setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def load_config(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    cfg_path = (root / args.config).resolve()
    cfg = load_config(cfg_path)

    runtime = cfg.get("runtime", {})
    setup_logging(root / runtime.get("log_file", ".logs/update.log"))

    template_file = root / cfg["template"]["file"]
    output_primary = root / cfg["output"]["primary_file"]
    output_copy = root / cfg["output"]["copy_file"]

    normalize_cfg = cfg.get("matching", {}).get("normalize", {})
    alias_map = cfg.get("matching", {}).get("alias_map", {})

    local_ip_port = (
        args.local_ip_port.strip()
        or cfg.get("udpxy", {}).get("default_local_ip_port", "192.168.100.2:4021")
    )
    udpxy_template = cfg.get("udpxy", {}).get("url_template", "http://{local_ip_port}/udp/{multicast}")

    parsed_template = load_m3u_file(str(template_file))
    sources = sorted(
        [s for s in cfg.get("sources", []) if s.get("enabled", True)],
        key=lambda x: int(x.get("priority", 100)),
    )

    all_records = []
    for s in sources:
        try:
            records = fetch_source_records(s)
            logging.info("source=%s records=%d", s.get("name", "unknown"), len(records))
            all_records.extend(records)
        except Exception as e:
            logging.exception("source failed: %s (%s)", s.get("name", "unknown"), e)

    if not all_records and cfg.get("runtime", {}).get("fail_if_no_source", True):
        raise RuntimeError("No source records fetched.")

    source_index = build_source_index(all_records, normalize_cfg=normalize_cfg, alias_map=alias_map)

    result = apply_matches(
        lines=parsed_template.lines,
        channels=parsed_template.channels,
        source_index=source_index,
        normalize_cfg=normalize_cfg,
        alias_map=alias_map,
        udpxy_template=udpxy_template,
        local_ip_port=local_ip_port,
    )

    report = {
        "total_channels": result.total_channels,
        "matched_channels": result.matched_channels,
        "replaced_urls": result.replaced_urls,
        "unchanged_urls": result.unchanged_urls,
        "unmatched_channels": result.unmatched_channels,
        "local_ip_port": local_ip_port,
        "sources": [s.get("name") for s in sources],
    }

    logging.info("report=%s", json.dumps(report, ensure_ascii=False))

    if not (args.dry_run or runtime.get("dry_run", False)):
        dump_m3u_file(str(output_primary), parsed_template)
        shutil.copyfile(output_primary, output_copy)

        report_file = root / runtime.get("report_file", ".logs/last-report.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        git_cfg = cfg.get("git", {})
        use_git = bool(git_cfg.get("enabled", False)) and not args.no_git
        if use_git:
            files = [
                str(output_primary.relative_to(root)),
                str(output_copy.relative_to(root)),
                str(report_file.relative_to(root)),
            ]
            if has_git_changes(root, files):
                commit_and_push(
                    cwd=root,
                    files=files,
                    message=git_cfg.get("commit_message", "chore: auto update IPTV urls"),
                    push=bool(git_cfg.get("push", True)),
                )
                logging.info("git commit/push done")
            else:
                logging.info("no git changes")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
