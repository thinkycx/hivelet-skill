#!/usr/bin/env python3
"""hivelet — Hivelet 平台客户端（init / login / push / check / asset / notes / get）。

职责最小（skill-spec v0.3）：登录拿 token + 把写好的笔记 push 上站 + 贡献/修改蜜源
+ 列笔记/拉取笔记（读 API，2026-10-18）。
生成环节（视频转写、写笔记）不在职责内——继续使用 media-summary 等现有 skill。

退出码：0 成功 ｜ 1 参数/文件错误 ｜ 2 网络不可达 ｜ 3 认证失败 ｜ 4 服务端校验拒绝
"""

from __future__ import annotations

import argparse
import datetime
import getpass
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

SKILL_NAME = "hivelet-skill"
SKILL_VERSION = "0.4.0"

CONFIG_PATH = Path(os.environ.get("HIVELET_CONFIG", "~/.config/hivelet/config.json")).expanduser()

DEFAULT_CONFIG = {
    "base_url": "https://hivelet.org",
    "api_token": "",
    "notes_dir": "~/Documents/Notes/hivelet-notes",
}

# ---------- 与服务端同规则的本地预检（服务端为准；消息保持一致便于对照） ----------

CATEGORY_REGISTRY = {"tech", "research", "life", "finance", "education", "career", "other"}
TITLE_DATE_RE = re.compile(r"（\d{4}-\d{2}(-\d{2})?）")

# refs URL -> (platform, external_id)；与服务端 platforms.py 注册表对齐
ASSET_URL_PATTERNS = [
    (re.compile(r"bilibili\.com/video/(BV[A-Za-z0-9]+)"), "bilibili"),
    (re.compile(r"bilibili\.com/read/(\d+)"), "bilibili_article"),
    (re.compile(r"youtube\.com/watch\?v=([A-Za-z0-9_\-]{6,})"), "youtube"),
    (re.compile(r"youtu\.be/([A-Za-z0-9_\-]{6,})"), "youtube"),
    (re.compile(r"zhihu\.com/people/([A-Za-z0-9_\-]+)"), "zhihu_user"),
    (re.compile(r"zhihu\.com/question/(\d+)"), "zhihu_question"),
    (re.compile(r"douban\.com/(?:subject|group/topic)/(\w+)/?"), "douban"),
    (re.compile(r"book\.douban\.com/subject/(\d+)"), "douban"),
]

# platform 注册表（与服务端 platforms.py 同步；asset 子命令校验用）
PLATFORM_REGISTRY = {
    "bilibili", "bilibili_article", "youtube", "zhihu_user",
    "zhihu_question", "douban", "isbn", "url", "self",
}

# 转写稿章节剥离：编号项「N. **原视频文字版**…」或标题「### 4.4 …文字版」（模板演化兼容两种形态）
TRANSCRIPT_SPLIT_RE = re.compile(
    r"^\d+\.\s*\*\*原视频文字版.*$|^#{2,4}\s*[\d.]*\s*.*文字版.*$|^<details[^>]*>.*$",
    re.MULTILINE,
)


def die(code: int, msg: str) -> "None":
    print(msg, file=sys.stderr)
    sys.exit(code)


# ---------- HTTP ----------

def request_json(method: str, url: str, token: str | None = None, payload: dict | None = None) -> tuple[int, dict | str]:
    req = urllib.request.Request(url, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as resp:
            body = resp.read().decode()
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except json.JSONDecodeError:
            return e.code, {}
    except (urllib.error.URLError, TimeoutError) as e:
        return -1, str(e)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return {**DEFAULT_CONFIG, **json.load(f)}


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ---------- 命令 ----------

def cmd_init(args) -> int:
    if CONFIG_PATH.exists():
        print(f"config 已存在：{CONFIG_PATH}（跳过创建）")
        cfg = load_config()
    else:
        cfg = dict(DEFAULT_CONFIG)
        if args.base_url:
            cfg["base_url"] = args.base_url
        save_config(cfg)
        print(f"config 已创建：{CONFIG_PATH}")
    status, _ = request_json("GET", f"{cfg['base_url']}/health")
    if status == -1:
        die(2, f"网络不可达：{cfg['base_url']}/health（检查 base_url 或网络）")
    print(f"服务可达：{cfg['base_url']} ✓")
    return 0


def cmd_login(args) -> int:
    cfg = load_config()
    base = cfg["base_url"]
    token = getattr(args, "token", None)
    if token:
        # --token 直传（一键贡献流程：agent 转述用户 token，免交互粘贴）
        token = token.strip()
        if not token:
            die(1, "token 为空")
    else:
        import sys as _sys
        for path, tip in [("/register", "没有账号：注册（用户名+密码）"),
                          ("/settings/tokens", "登录后生成 API Token 并复制")]:
            url = base + path
            print(f"{tip}\n  {url}")
        # 自动开浏览器仅限交互 TTY（agent/CI 环境打印 URL 即可，不弹窗）
        if _sys.stdout.isatty():
            try:
                subprocess.Popen(["open", url])  # macOS；Linux 可换 xdg-open
            except OSError:
                pass
        token = getpass.getpass("粘贴 token（输入隐藏）: ").strip()
        if not token:
            die(1, "token 为空")
    status, body = request_json("GET", f"{base}/api/v1/me", token=token)
    if status == -1:
        die(2, "网络不可达")
    if status != 200:
        die(3, f"token 无效（HTTP {status}）")
    cfg["api_token"] = token
    save_config(cfg)
    print(f"✓ 登录成功：{body.get('username')}（token 已写入 {CONFIG_PATH}）")
    return 0


# ---------- push 辅助 ----------

def _jsonable(value):
    """yaml 的 date/datetime -> ISO 字符串（JSON 可序列化，与服务端存储格式一致）。"""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def parse_frontmatter(content: str) -> tuple[dict, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    if not m:
        return {}, content
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        die(1, f"frontmatter yaml 解析失败：{e}")
    return _jsonable(fm), m.group(2)


def extract_asset(fm: dict) -> dict | None:
    """主 ref（第一个可识别的外部链接）-> asset；hivelet.asset 块补充 title/author/metadata。"""
    refs = fm.get("refs") or []
    if isinstance(refs, str):
        refs = [refs]
    platform = external_id = url = None
    for ref in refs:
        for pat, plat in ASSET_URL_PATTERNS:
            m = pat.search(str(ref))
            if m:
                platform, external_id, url = plat, m.group(1), str(ref)
                break
        if platform:
            break
    if not platform:
        return None
    extra = (fm.get("hivelet") or {}).get("asset") or {}
    return {
        "platform": platform,
        "external_id": external_id,
        "url": url,
        "title": extra.get("title") or fm.get("title") or external_id,
        "author": extra.get("author"),
        "published_at": extra.get("published_at"),
        "metadata": extra.get("metadata") or {},
    }


def strip_transcript(body: str) -> tuple[str, str | None]:
    """剥离转写稿章节（编号项或标题形式；模板规则：放文章最后）。返回 (正文, 转写稿)。"""
    for m in TRANSCRIPT_SPLIT_RE.finditer(body):
        head = body[: m.start()].rstrip()
        # 剥离点之前必须已出现"文字版"语境（避免误切普通 details 块）
        if "文字版" in m.group(0) or "转写" in m.group(0):
            transcript = body[m.start():].strip()
            return head, transcript
    return body, None


def local_check(fm: dict, style: str | None) -> None:
    """本地预检（服务端同规则；不通过直接退出码 4，打印同样的 field/rule/message）。"""
    errors = []
    title = fm.get("title")
    if not title or not str(title).strip():
        errors.append({"field": "title", "rule": "required", "message": "title 必填（笔记标题）"})
    elif style == "video-summary":
        t = str(title)
        if "｜" not in t or "：" not in t or not TITLE_DATE_RE.search(t):
            errors.append({
                "field": "title", "rule": "title-format",
                "message": "标题须为 <内容类型>｜<主体>（YYYY-MM-DD 或 YYYY-MM）：<主题概括>，"
                           f"当前值：{t!r}",
            })
    if not fm.get("description") or not str(fm.get("description")).strip():
        errors.append({"field": "description", "rule": "required",
                       "message": "description 必填（一句话摘要，列表页/SEO 必需）"})
    if fm.get("category") is not None and fm.get("category") not in CATEGORY_REGISTRY:
        errors.append({"field": "category", "rule": "registry",
                       "message": f"category 须为注册表值之一：{sorted(CATEGORY_REGISTRY)}，"
                                  f"当前值：{fm.get('category')!r}"})
    if style == "video-summary" and not fm.get("refs"):
        errors.append({"field": "refs", "rule": "required",
                       "message": "video-summary 必填 refs（原视频链接，聚合锚点来源）"})
    if errors:
        print("本地预检未通过（服务端同规则）：", file=sys.stderr)
        for e in errors:
            print(f"  - {e['field']} [{e['rule']}]: {e['message']}", file=sys.stderr)
        sys.exit(4)


class _FlowListDumper(yaml.SafeDumper):
    """dict 用 block、list 用行内 []（tags: [a, b]），与平台 raw 输出一致。"""

    pass


def _represent_flow_list(dumper, data):
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


_FlowListDumper.add_representer(list, _represent_flow_list)

# frontmatter 规范顺序（ai-notes 惯例，与服务端 order_frontmatter 一致）
_FM_ORDER = ["access", "create", "update", "author", "title",
             "description", "category", "tags", "keywords", "refs"]


def _order_fm(fm: dict) -> dict:
    ordered = {k: fm[k] for k in _FM_ORDER if k in fm}
    for k, v in fm.items():
        if k not in ordered and k != "hivelet":
            ordered[k] = v
    if "hivelet" in fm:
        ordered["hivelet"] = fm["hivelet"]
    return ordered


def _dump_fm(fm: dict) -> str:
    return yaml.dump(_order_fm(fm), Dumper=_FlowListDumper, allow_unicode=True, sort_keys=False)


def write_back_note_id(path: Path, fm: dict, body: str, note_id: int, transcript: str | None) -> None:
    """note_id 回写 frontmatter（hivelet.note_id，文件即真相）。

    本地文件保持完整：剥离出的转写稿章节拼回文末（push 时再次剥离）。
    """
    fm = dict(fm)
    hivelet_block = dict(fm.get("hivelet") or {})
    hivelet_block["note_id"] = note_id
    fm["hivelet"] = hivelet_block
    full_body = body.rstrip() + ("\n\n" + transcript if transcript else "")
    path.write_text(f"---\n{_dump_fm(fm)}---\n\n{full_body.lstrip()}\n", encoding="utf-8")


def cmd_push(args) -> int:
    path = Path(args.file).expanduser()
    if not path.exists():
        die(1, f"文件不存在：{path}")
    cfg = load_config()
    if not cfg.get("api_token"):
        die(3, "未登录（先 hivelet login）")
    base = cfg["base_url"]

    content = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(content)
    style = args.style or fm.get("style")
    local_check(fm, style)

    body, transcript = strip_transcript(body)

    hivelet_block = fm.get("hivelet") or {}
    note_id = hivelet_block.get("note_id")

    # push 的 file 剥离 hivelet 块（note_id 是 skill 本地机制，服务端不需要；
    # 本地文件保留完整）。frontmatter 按规范顺序重建。
    fm_push = {k: v for k, v in fm.items() if k != "hivelet"}
    # asset_id 直连（优先）：显式指定时不做 URL 提取（服务端二者互斥 422）
    asset_id = getattr(args, "asset_id", None)
    if asset_id is None:
        _warn_asset_exists(base, cfg.get("api_token") or None, fm)
    payload = {
        "note_id": note_id,
        "file": _rebuild(fm_push, body),
        "asset_id": asset_id,
        "asset": None if asset_id else extract_asset(fm),
        "style": style,
        "provenance": {
            "skill": SKILL_NAME,
            "skill_version": SKILL_VERSION,
            "agent": args.agent,
            **({"llm_model": args.model} if args.model else {}),
            **({"stt_model": args.stt_model or fm.get("stt_model")}
               if (args.stt_model or fm.get("stt_model")) else {}),
        },
        "transcript": transcript if args.with_transcript else None,
        "visibility": args.visibility,
    }

    status, resp = request_json("POST", f"{base}/api/v1/notes", token=cfg["api_token"], payload=payload)
    if status == -1:
        die(2, f"网络不可达：{base}")
    if status == 401:
        die(3, "token 失效（重新 hivelet login）")
    if status == 422:
        print("服务端校验拒绝：", file=sys.stderr)
        errors = resp.get("detail") or [resp]
        for e in errors:
            if isinstance(e, dict):
                print(f"  - {e.get('field')} [{e.get('rule')}]: {e.get('message')}", file=sys.stderr)
            else:
                print(f"  - {e}", file=sys.stderr)
        sys.exit(4)
    if status != 200:
        die(4, f"服务端错误 HTTP {status}: {resp}")

    new_note_id = resp["note_id"]
    if new_note_id != note_id:
        write_back_note_id(path, fm, body, new_note_id, transcript)
    url = resp.get("url") or f"{base}/notes/{new_note_id}"
    asset_part = f"，蜜源 asset {resp['asset_id']}" if resp.get("asset_id") else "，独立笔记"
    print(f"✓ push 成功：note {new_note_id}（rev {resp['revision_no']}）{asset_part}")
    print(url)
    # 自动开浏览器仅限交互 TTY（agent/CI 环境不弹窗；--no-open 显式关闭）
    import sys as _sys
    if _sys.stdout.isatty() and not getattr(args, "no_open", False):
        try:
            subprocess.Popen(["open", url])   # macOS；Linux 可换 xdg-open
        except OSError:
            pass
    return 0


def _rebuild(fm: dict, body: str) -> str:
    """剥离转写稿后的整份文件（frontmatter + 正文）。"""
    return f"---\n{_dump_fm(fm)}---\n\n{body.lstrip()}"


def _warn_asset_exists(base: str, token: str | None, fm: dict) -> None:
    """push 预检：refs 提取出的蜜源若已存在，提醒可 --asset-id 直连（2026-10-18）。

    不阻断——服务端 (platform, external_id) 幂等，直接 push 安全；
    提醒的价值：蜜源已有时用直连更明确，且提示已有几篇蜜可参考。
    """
    asset = extract_asset(fm)
    if not asset:
        return
    status, resp = request_json(
        "GET",
        f"{base}/api/v1/assets?"
        + urllib.parse.urlencode({"external_id": asset["external_id"],
                                  "platform": asset["platform"]}),
        token=token,
    )
    if status != 200:
        return                                   # 预检失败不挡 push
    items = resp.get("items") or []
    if items:
        a = items[0]
        print(f"ℹ 蜜源已存在：asset {a['id']}（{a['platform']}/{a['external_id']}）"
              f"已有 {a['note_count']} 篇蜜，最佳蜜 #{a.get('best_note_id')}", file=sys.stderr)
        print(f"  继续推送将关联到该蜜源；也可以直连：hivelet push <file> --asset-id {a['id']}",
              file=sys.stderr)


def cmd_check(args) -> int:
    """本地校验笔记格式（不 push）。"""
    path = Path(args.file).expanduser()
    if not path.exists():
        die(1, f"文件不存在：{path}")
    fm, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
    style = args.style or fm.get("style")
    local_check(fm, style)
    print(f"✓ 格式通过（style: {style or '未声明'}）")
    return 0


# ---------- 读命令（读 API 2026-10-18：Bearer = 登录视角，可见自己的私有） ----------

def _fmt_ts(iso: str | None) -> str:
    """iso -> 本地短格式（2026-10-18 14:30）。"""
    if not iso:
        return "-"
    try:
        dt = datetime.datetime.fromisoformat(iso)
        return dt.astimezone().strftime("%m-%d %H:%M")
    except ValueError:
        return iso[:16]


def cmd_notes(args) -> int:
    """列笔记（feed 端点）。--mine = 我的笔记（含自己的私有，需 token）。"""
    cfg = load_config()
    base = cfg["base_url"]
    token = cfg.get("api_token") or None
    if args.mine and not token:
        die(3, "未登录（先 hivelet login）")
    params = {"page": args.page, "page_size": args.limit}
    if args.mine:
        # 先拿 username（/me），再按 author 过滤——ACL 见自己的私有
        status, me = request_json("GET", f"{base}/api/v1/me", token=token)
        if status != 200:
            die(3, "token 失效（重新 hivelet login）")
        params["author"] = me["username"]
    for k in ("tag", "platform", "style", "category"):
        v = getattr(args, k)
        if v:
            params[k] = v
    if args.sort:
        params["sort"] = args.sort
    status, resp = request_json(
        "GET", f"{base}/api/v1/feed?{urllib.parse.urlencode(params)}",
        token=token,
    )
    if status == -1:
        die(2, f"网络不可达：{base}")
    if status != 200:
        die(4, f"服务端错误 HTTP {status}: {resp}")
    items = resp.get("items", [])
    if not items:
        print("没有匹配的笔记。")
        return 0
    print(f"共 {resp['total']} 篇（第 {resp['page']}/{max(1, -(-resp['total'] // resp['page_size']))} 页）")
    for i in items:
        vis = "" if i["visibility"] == "public" else " 🔒"
        asset_tag = f" [{i['asset']['platform']}]" if i.get("asset") else ""
        print(f"  {i['note_id']:>4}  {i['title'][:56]}{vis}{asset_tag}  "
              f"— {i['author']} · {_fmt_ts(i['updated_at'])}")
    print("拉取全文：hivelet get <note_id>；翻页：--page N")
    return 0


def cmd_get(args) -> int:
    """拉取笔记：元数据 + 整份 md（file = frontmatter + 正文，与 push 输入对称）。

    缺省打印元数据摘要 + file 到 stdout；-o 写入本地文件（编辑后带 note_id 重推 = 修改）。
    --rev N 取历史版本。
    """
    cfg = load_config()
    base = cfg["base_url"]
    token = cfg.get("api_token") or None
    url = f"{base}/api/v1/notes/{args.note_id}"
    if args.rev:
        url += f"?rev={args.rev}"
    status, resp = request_json("GET", url, token=token)
    if status == -1:
        die(2, f"网络不可达：{base}")
    if status == 404:
        die(1, f"note {args.note_id} 不存在或不可见（私有笔记需 owner 的 token）")
    if status != 200:
        die(4, f"服务端错误 HTTP {status}: {resp}")

    if args.output:
        path = Path(args.output).expanduser()
        if path.exists() and not args.force:
            die(1, f"文件已存在（--force 覆盖）：{path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(resp["file"], encoding="utf-8")
        # 回写 hivelet.note_id（文件即真相：编辑后 push 自动对准同一篇）
        fm, body = parse_frontmatter(resp["file"])
        if fm:
            write_back_note_id(path, fm, body, resp["note_id"], None)
        print(f"✓ 已保存：{path}（note {resp['note_id']} rev {resp['revision_no']}）")
        print(f"编辑后重推：hivelet push {path}")
        return 0

    # stdout：元数据 + 整份 md（管道友好： hivelet get 3 | tail -n +N 取正文）
    a = resp.get("asset") or {}
    meta = [
        f"note {resp['note_id']}  rev {resp['revision_no']}/{resp['current_revision_no']}",
        f"{resp['title']}",
        f"作者 {resp['author']}  可见性 {resp['visibility']}  更新 {resp['updated_at'][:16]}",
    ]
    if a:
        meta.append(f"蜜源 asset {a['id']}（{a['platform']}/{a.get('external_id')}）{a.get('title') or ''}")
    print("\n".join(meta))
    print()
    print(resp["file"], end="" if resp["file"].endswith("\n") else "\n")
    return 0


def cmd_assets_list(args) -> int:
    """列蜜源（assets 列表端点）。--q 模糊搜索（标题/原作者/资源id/登记人，如 BV 号）。"""
    cfg = load_config()
    base = cfg["base_url"]
    token = cfg.get("api_token") or None
    params = {"page": args.page, "page_size": args.limit}
    for k in ("source", "platform", "author", "q"):
        v = getattr(args, k)
        if v:
            params[k] = v
    if args.sort:
        params["sort"] = args.sort
    status, resp = request_json(
        "GET", f"{base}/api/v1/assets?{urllib.parse.urlencode(params)}",
        token=token,
    )
    if status == -1:
        die(2, f"网络不可达：{base}")
    if status != 200:
        die(4, f"服务端错误 HTTP {status}: {resp}")
    items = resp.get("items", [])
    if not items:
        print("没有匹配的蜜源。")
        return 0
    print(f"共 {resp['total']} 个蜜源")
    for i in items:
        best = f" 最佳蜜 #{i['best_note_id']}" if i.get("best_note_id") else ""
        print(f"  {i['id']:>4}  [{i['platform']}] {i['title'][:48]}  "
              f"蜜 {i['note_count']} 篇{best}  — {i.get('author') or '未知作者'}"
              f"（登记 {i.get('submitted_by') or '?'}）")
    print("蜜源详情：curl $BASE_URL/api/v1/assets/<id>；蜂蜜列表：…/assets/<id>/notes；"
          "push 直连：hivelet push note.md --asset-id <id>")
    return 0


# ---------- asset 子命令（贡献/修改蜜源） ----------

def parse_asset_url(url: str) -> tuple[str, str]:
    """URL -> (platform, external_id)；识别不了 die(1)。"""
    for pat, plat in ASSET_URL_PATTERNS:
        m = pat.search(url)
        if m:
            return plat, m.group(1)
    die(1, f"URL 无法识别平台（支持 B站视频/专栏、YouTube、知乎用户/问题、豆瓣条目）：{url}")


def _require_token(cfg: dict) -> str:
    if not cfg.get("api_token"):
        die(3, "未登录（先 hivelet login）")
    return cfg["api_token"]


def cmd_asset(args) -> int:
    """asset create <url> [--title --author --description --published-at --metadata]
    asset patch <id>  [--title --author --description --url --published-at --metadata]"""
    cfg = load_config()
    token = _require_token(cfg)
    base = cfg["base_url"]

    if args.asset_cmd == "create":
        platform, external_id = parse_asset_url(args.url)
        payload = {
            "platform": platform,
            "external_id": external_id,
            "title": args.title or external_id,
            "url": args.url,
            **({"author": args.author} if args.author else {}),
            **({"description": args.description} if args.description else {}),
            **({"published_at": args.published_at} if args.published_at else {}),
            **({"metadata": json.loads(args.metadata)} if args.metadata else {}),
        }
        status, resp = request_json("POST", f"{base}/api/v1/assets", token=token, payload=payload)
    else:  # patch
        updates = {}
        for k in ("title", "author", "description", "url", "published_at"):
            v = getattr(args, k)
            if v is not None:
                updates[k] = v
        if args.metadata:
            updates["metadata"] = json.loads(args.metadata)
        if not updates:
            die(1, "没有要修改的字段（--title/--author/--description/--url/--published-at/--metadata）")
        status, resp = request_json("PATCH", f"{base}/api/v1/assets/{args.asset_id}",
                                    token=token, payload=updates)

    if status == -1:
        die(2, f"网络不可达：{base}")
    if status == 401:
        die(3, "token 失效（重新 hivelet login）")
    if status == 403:
        die(4, "只有登记人或 admin 可修改蜜源")
    if status == 422:
        print("服务端校验拒绝：", file=sys.stderr)
        print(f"  {resp.get('detail')}", file=sys.stderr)
        sys.exit(4)
    if status not in (200, 201):
        die(4, f"服务端错误 HTTP {status}: {resp}")

    if args.asset_cmd == "create":
        if resp.get("created"):
            print(f"✓ 蜜源新登记：asset {resp['id']}（{resp['platform']}/{resp['external_id']}）")
        else:
            print(f"✓ 蜜源已存在（幂等命中）：asset {resp['id']}（{resp['platform']}/{resp['external_id']}）")
            print(f"  可直接上传关联笔记：hivelet push <file> --asset-id {resp['id']}")
    else:
        print(f"✓ 蜜源已更新：asset {resp['id']}")
    print(f"{base}{resp['url_path']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="hivelet", description="Hivelet 平台客户端")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="创建/校验 config，检测服务可达")
    p_init.add_argument("--base-url", default=None)
    p_init.set_defaults(func=cmd_init)

    p_login = sub.add_parser("login", help="浏览器注册/拿 token 并验证")
    p_login.add_argument("--token", default=None,
                         help="直接传 token（agent 场景免交互粘贴）；缺省走交互流程")
    p_login.set_defaults(func=cmd_login)

    p_push = sub.add_parser("push", help="推送笔记上站")
    p_push.add_argument("file")
    p_push.add_argument("--style", default=None, help="缺省用 frontmatter.style")
    p_push.add_argument("--model", default=None, help="llm_model（模型在会话层，由 agent 传入）")
    p_push.add_argument("--stt-model", default=None)
    p_push.add_argument("--agent", default="claude-code")
    p_push.add_argument("--with-transcript", action="store_true", help="携带转写稿（默认剥离且不传）")
    p_push.add_argument("--visibility", choices=["public", "private"], default=None)
    p_push.add_argument("--asset-id", type=int, default=None,
                        help="直连已有蜜源（asset id；指定时不做 URL 提取，服务端 asset/asset_id 互斥）")
    p_push.add_argument("--no-open", action="store_true", help="成功后不自动打开浏览器（默认仅 TTY 交互时开）")
    p_push.set_defaults(func=cmd_push)

    p_check = sub.add_parser("check", help="本地校验笔记格式（不 push）")
    p_check.add_argument("file")
    p_check.add_argument("--style", default=None)
    p_check.set_defaults(func=cmd_check)

    p_notes = sub.add_parser("notes", help="列笔记（feed；--mine 含自己的私有）")
    p_notes.add_argument("--mine", action="store_true", help="我的笔记（需登录，含私有）")
    p_notes.add_argument("--tag", default=None)
    p_notes.add_argument("--platform", default=None)
    p_notes.add_argument("--style", default=None)
    p_notes.add_argument("--category", default=None)
    p_notes.add_argument("--sort", default=None, choices=["new", "hot"])
    p_notes.add_argument("--page", type=int, default=1)
    p_notes.add_argument("--limit", type=int, default=20, help="每页条数（≤100）")
    p_notes.set_defaults(func=cmd_notes)

    p_get = sub.add_parser("get", help="拉取笔记（元数据 + 整份 md；-o 存本地可编辑重推）")
    p_get.add_argument("note_id", type=int)
    p_get.add_argument("--rev", type=int, default=None, help="历史版本号")
    p_get.add_argument("-o", "--output", default=None, help="写入本地文件（--force 覆盖）")
    p_get.add_argument("--force", action="store_true")
    p_get.set_defaults(func=cmd_get)

    p_alist = sub.add_parser("assets", help="列蜜源（--q 搜标题/作者/资源id/登记人）")
    p_alist.add_argument("--q", default=None, help="模糊搜索：标题/原作者/资源id（BV号等）/登记人")
    p_alist.add_argument("--source", default=None, help="分组：bilibili/youtube/douban/other")
    p_alist.add_argument("--platform", default=None)
    p_alist.add_argument("--author", default=None, help="原作者精确匹配")
    p_alist.add_argument("--sort", default=None, choices=["new", "honey"])
    p_alist.add_argument("--page", type=int, default=1)
    p_alist.add_argument("--limit", type=int, default=20, help="每页条数（≤100）")
    p_alist.set_defaults(func=cmd_assets_list)

    p_asset = sub.add_parser("asset", help="贡献/修改蜜源")
    p_asset_sub = p_asset.add_subparsers(dest="asset_cmd", required=True)

    p_ac = p_asset_sub.add_parser("create", help="登记蜜源（URL 自动解析 platform/external_id）")
    p_ac.add_argument("url", help="B站视频/专栏、YouTube、知乎用户/问题、豆瓣条目 URL")
    p_ac.add_argument("--title", default=None, help="蜜源标题（缺省用 external_id）")
    p_ac.add_argument("--author", default=None)
    p_ac.add_argument("--description", default=None, help="1-3 句介绍")
    p_ac.add_argument("--published-at", default=None, help="ISO 8601（如 2026-10-01 或 2026-10-01T08:00:00+08:00）")
    p_ac.add_argument("--metadata", default=None, help='JSON 字符串（如 \'{"duration": 600}\'）')
    p_ac.set_defaults(func=cmd_asset)

    p_ap = p_asset_sub.add_parser("patch", help="修改蜜源元数据（仅登记人/admin）")
    p_ap.add_argument("asset_id", type=int)
    p_ap.add_argument("--title", default=None)
    p_ap.add_argument("--author", default=None)
    p_ap.add_argument("--description", default=None)
    p_ap.add_argument("--url", default=None)
    p_ap.add_argument("--published-at", default=None)
    p_ap.add_argument("--metadata", default=None, help="JSON 字符串（null 值删键）")
    p_ap.set_defaults(func=cmd_asset)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
