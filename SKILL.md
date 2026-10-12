---
name: hivelet
description: >
  Hivelet 平台客户端：登录拿 token、把写好的笔记 push 上站（init/login/push/check）。
  触发词："hivelet"、"push 笔记"、"发布到小蜂巢"、"hivelet login"。
  注意：视频转写与笔记生成请用 media-summary 等现有 skill，本 skill 只负责推送。
---

# Hivelet 小蜂巢客户端

把本地 AI 分析笔记推送到 Hivelet 平台（多作者、多版本、社区投票的笔记共享）。
契约：`docs/skill-spec.md`（hivelet-server 仓库）；服务端以 `docs/api.md` 为准。

## 快速开始

```bash
# 1. 初始化（首次使用，检测服务可达）
hivelet init --base-url https://hivelet.org

# 2. 登录（浏览器注册 + 生成 token，粘贴回终端）
hivelet login

# 3. 推送笔记（任意 skill 生成的、带 frontmatter 的 md）
hivelet push ~/Documents/Notes/my-note.md --model glm-5.3

# 本地预检（不 push）
hivelet check my-note.md
```

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
2. **asset 提取**：refs 主链接（B站 BV号 / YouTube / 知乎主页）→ platform+external_id；
   `frontmatter.hivelet.asset` 块补充原视频 title/author/published_at/metadata（aid/cid/duration）
3. **转写稿剥离**：「原视频文字版」章节（编号项或标题形式）剥离；
   `--with-transcript` 才作为私有字段携带（默认不传）
4. **note_id 回写**：push 返回后写回 `frontmatter.hivelet.note_id`（文件即真相，跟随笔记迁移）
5. 幂等（服务端三分支）：带 note_id → 追加 revision；无 note_id + asset →
   (asset, user, style) 匹配则追加 revision；独立笔记必须带 note_id 才是同一篇

## 退出码

`0` 成功 ｜ `1` 参数/文件错误 ｜ `2` 网络不可达 ｜ `3` 认证失败（重新 login）｜
`4` 校验拒绝（打印 field/rule/message，AI 修正后可重推）

## styles

`styles/*.md` 从 ai-notes 复制同步（文件头标注来源版本），是笔记格式的标准模板；
video-summary 等风格的标题/章节/引用规范见对应模板。
