---
name: hivelet
description: >
  Hivelet 平台客户端：登录拿 token、push 笔记上站、列/拉笔记、贡献/修改蜜源
  （init/login/push/check/notes/get/assets/asset）。触发词："hivelet"、"push 笔记"、
  "发布到小蜂巢"、"hivelet login"、"登记蜜源"、"贡献蜜源"、"拉笔记"、"列我的笔记"。
  注意：视频转写与笔记生成请用 media-summary 等现有 skill，本 skill 只负责推送与读取。
---

# Hivelet 小蜂巢客户端

把本地 AI 分析笔记推送到 Hivelet 平台（多作者、多版本、社区投票的笔记共享），
支持独立登记/修改蜜源（asset），以及列笔记/拉取笔记（读 API）。
契约：`docs/skill-spec.md`（hivelet-server 仓库）；服务端以 `docs/api.md` 为准。

## 快速开始

```bash
# 1. 初始化（首次使用，检测服务可达）
hivelet init --base-url https://hivelet.org

# 2. 登录（浏览器注册 + 生成 token，粘贴回终端；或 --token 直传）
hivelet login
hivelet login --token hvl_xxxxxxxx   # agent 转述场景，免交互

# 3. 推送笔记, md 必须遵循模板，格式参考 note-template.md
hivelet push note.md --model glm-5.3

# 4. 贡献蜜源（URL 自动解析 platform/external_id，幂等）
hivelet asset create "https://www.bilibili.com/video/BV1xxxxx" \
  --title "视频标题" --author "UP主" --description "1-3 句介绍"

# 修改蜜源元数据（仅登记人/admin）
hivelet asset patch 17 --description "更新后的介绍"

# 本地预检（不 push）
hivelet check my-note.md
```

## 一键贡献（蜜源页 CTA，2026-10-23）

蜜源详情页「一键贡献」按钮复制一段编排 prompt 给 agent，agent 按此流程执行：

1. **skill 自检**：`ls ~/.claude/skills/hivelet* ~/.agents/skills/hivelet* 2>/dev/null`；
   没有 -> `git clone https://github.com/thinkycx/hivelet-skill ~/.claude/skills/hivelet-skill`
   （media-summary 同理：`git clone https://github.com/thinkycx/media-summary ~/.claude/skills/media-summary`）
2. **初始化**：`hivelet init --base-url <站点>`（config 已存在则跳过；本地脚本路径
   `<skill目录>/scripts/hivelet.py`，可直接 `python3` 调用）
3. **转写总结**：用 media-summary 转写目标视频 -> 按 styles/video-summary.md 组织笔记
   （标题格式 `<类型>｜<主体>（YYYY-MM）：<主题>`，refs 必填源链接）
4. **推送**：`hivelet push <笔记.md> --asset-id <N> --model <当前模型>`
5. **未登录处理**：push 返回 401/退出码 3 -> 引导用户打开 `<站点>/register` 注册，
   再到 `<站点>/settings/tokens` 生成 token，用户转述后 `hivelet login --token hvl_xxx`
   写入配置，重推即可（不需要重新转写）

退出码语义见下节；422 校验拒绝时按 stderr 的 field/rule/message 修正 md 后重推。

脚本：`scripts/hivelet.py`（建议 symlink 或 alias 为 `hivelet`）。

## config

`~/.config/hivelet/config.json`：

```json
{
  "base_url": "https://hivelet.org",
  "api_token": "hvl_...",
  "notes_dir": "~/Documents/Notes/hivelet-notes"
}
```

## push 行为

1. **本地预检**（与服务端同规则）：title/description 必填、category 注册表、
   video-summary 标题格式 `<类型>｜<主体>（YYYY-MM）：<主题>`、refs 必填
2. **蜜源关联三姿势**：
   - `--asset-id N` 直连已有蜜源（显式指定，优先级最高，此时不做 URL 提取）
   - frontmatter refs 主链接（B站 BV号 / YouTube / 知乎主页）自动提取 → asset
     （`frontmatter.hivelet.asset` 块补充原视频 title/author/published_at/metadata）
   - 都没有 → 独立笔记（不关联蜜源，个人笔记）
3. **转写稿剥离**：「原视频文字版」章节（编号项或标题形式）剥离；
   `--with-transcript` 才作为私有字段携带（默认不传）
4. **note_id 回写**：push 返回后写回 `frontmatter.hivelet.note_id`（文件即真相，跟随笔记迁移）
5. 幂等（服务端四分支）：带 note_id → 追加 revision；带 asset_id → 直连已有蜜源；
   带 asset → (asset, user, style) 匹配则追加 revision；独立笔记必须带 note_id 才是同一篇
6. **去重键提醒**：同蜜源同人同 style 的笔记重推 = 追加 revision 而非新笔记。
   要在同蜜源下发**另一篇**笔记，务必声明不同 style（frontmatter `style:` 或 `--style`），
   否则会覆盖已有笔记的 title/description

## 读命令（2026-10-18 新增，0.3.0）

Bearer token = 登录视角：`--mine` / 私有笔记的 get 都可见自己的私有；不登录只读 public。
输出形态见 `read-template.md`（AI 按模板解析）。

- `notes [--mine] [--tag --platform --style --category --sort --page --limit]`：列笔记。
  `--mine` = 我的笔记（含私有）
- `get <note_id> [--rev N] [-o 文件]`：拉笔记 = 元数据 + **整份 md（file）**。
  `-o` 存本地并自动回写 `hivelet.note_id`——编辑后 `hivelet push` 即修改（追加 revision）。
  这是**修改闭环的下半段**：get → 编辑 → push
- `assets [--q --source --platform --author --sort --page --limit]`：列蜜源。
  `--q` 模糊搜索（标题/原作者/资源id/登记人——**B站 BV 号可直接搜**）；
  `sort=honey` 按蜂蜜数；输出含 best_note_id 最佳蜜与登记人

**重复蜜源提醒**：push 时 refs 提取出蜜源若站上已存在，stderr 提醒
「蜜源已存在 asset N，已有 X 篇蜜，可 --asset-id 直连」（不阻断，幂等安全）；
`asset create` 幂等命中同样提示直连。

常见流程（AI 决策参考）：

| 意图 | 命令链 |
|---|---|
| 修改我的笔记 | `notes --mine` → `get <id> -o f.md` → 编辑 → `push f.md` |
| 给已有蜜源写笔记 | `assets --q <BV号/标题/作者>` → `push note.md --asset-id <id>` |
| 读最佳总结 | `assets --sort honey`（拿 best_note_id）→ `get <best_id>` |
| 查某资源有没有笔记 | `assets --q <BV号>` → `curl …/assets/<id>/notes` |

## asset 子命令

- `create <url>`：URL 自动解析 platform/external_id（支持 B站视频/专栏、YouTube、
  知乎用户/问题、豆瓣条目）；(platform, external_id) 幂等，已存在返回 `created:false`；
  配额 20 个/天/用户
- `patch <id>`：改 title/author/description/url/published_at/metadata
  （platform/external_id 不可改；仅登记人或 admin）
- 平台注册表（与服务端 platforms.py 同步）：bilibili / bilibili_article / youtube /
  zhihu_user / zhihu_question / douban / isbn / url / self

## 退出码

`0` 成功 ｜ `1` 参数/文件错误 ｜ `2` 网络不可达 ｜ `3` 认证失败（重新 login）｜
`4` 校验拒绝/配额超限（打印 field/rule/message，AI 修正后可重推）

## styles

`styles/*.md` 从 ai-notes 复制同步（文件头标注来源版本），是笔记格式的标准模板；
video-summary 等风格的标题/章节/引用规范见对应模板。
