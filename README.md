# IPTV 地址自动更新工具

基于当前仓库的 `M3U.m3u` 作为模板（顺序和分组不变），自动从配置的直播源更新频道 URL，并输出：

- `M3U.m3u`（主文件）
- `my IPTV.m3u`（同步副本）

## 核心能力

- 只更新地址行，不改频道顺序、分组、`#EXTINF` 元数据
- 多源抓取（按优先级）
- 匹配回退链：`tvg-id -> tvg-name -> 频道名`
- 支持将组播地址统一重写为本地 udpxy：
	`http://{本地ip:端口}/udp/{组播IP:端口}`
- 记录更新报告：`.logs/last-report.json`

## 目录结构

- `config.yaml`：配置文件（源地址、优先级、udpxy、本地输出）
- `scripts/update_iptv.py`：主脚本
- `scripts/m3u_parser.py`：M3U 解析与序列化
- `scripts/source_fetchers.py`：多源抓取与标准化
- `scripts/matcher.py`：匹配与替换
- `scripts/git_sync.py`：可选 git 自动提交
- `web/`：GitHub Pages 纯前端本地地址生成器
- `deploy/systemd/`：Ubuntu 定时任务示例

## 快速开始

1) 安装依赖

- `pip install -r requirements.txt`

2) 修改配置

- 编辑 `config.yaml`：
	- `sources`：可配置多个来源（`priority` 数字越小优先级越高）
	- `udpxy.default_local_ip_port`：你的本地 `ip:port`

3) 执行更新

- `python scripts/update_iptv.py --config config.yaml`

可临时覆盖本地 udpxy 地址：

- `python scripts/update_iptv.py --local-ip-port 192.168.2.11:4000`

仅试跑不落盘：

- `python scripts/update_iptv.py --dry-run`

## Ubuntu 每日定时（systemd）

将项目放到 Ubuntu（例如 `~/IPTV`）后：

1) 拷贝服务文件

- `deploy/systemd/iptv-update.service`
- `deploy/systemd/iptv-update.timer`

2) 安装并启用

- 复制到 `~/.config/systemd/user/`（按需改 WorkingDirectory）
- `systemctl --user daemon-reload`
- `systemctl --user enable --now iptv-update.timer`
- `systemctl --user list-timers | grep iptv-update`

默认每天 `03:10` 执行一次，可修改 `deploy/systemd/iptv-update.timer` 的 `OnCalendar`。

## GitHub Pages 前端生成

`web/` 目录是纯静态页面，支持用户输入本地 `ip:port`，把 M3U 中的 `/udp/组播地址` 重写并下载。

说明：GitHub Pages 是静态托管，不能运行后端定时更新脚本；动态逻辑要么放本地任务，要么用 Worker/Serverless。

## 注意

- 若某频道在源中未匹配到，会保留原地址（避免误改）
- 本仓库默认关闭 git 自动提交，若需自动 push，请在 `config.yaml -> git.enabled` 设为 `true`
