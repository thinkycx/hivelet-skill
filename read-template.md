# 读命令输出模板（notes / get / assets）

hivelet 0.3.0 读命令的输出形态。AI 按这些模板解析结果、决定下一步操作。
服务端契约：`docs/api.md`（hivelet-server 仓库）；认证 Bearer token = 登录视角（可见自己的私有）。

## hivelet notes —— 列笔记

```bash
hivelet notes --mine                # 我的笔记（含私有；不登录只列 public 的）
hivelet notes --tag video-summary --sort hot --limit 5
hivelet notes --platform bilibili
```

输出（每行：id、标题[56 字截断]、🔒=私有、[平台]、作者、更新时间）：

```
共 3 篇（第 1/1 页）
     3  人物采访｜Sam Altman × NYT（2026-08-15）：算力、智能与监管（全访谈） [bilibili]  — admin · 10-17 07:44
    29  人物采访｜Dario Amodei × 彭博（2026-04-30）：Mythos、战争红线与万亿估值… [bilibili]  — admin · 10-17 07:44
    68  XekRung(伏渊息壤)深度技术报告:把安全智能压缩进小模型  🔒  — thinkycx · 10-18 09:02
拉取全文：hivelet get <note_id>；翻页：--page N
```

筛选参数：`--tag` / `--platform` / `--style` / `--category` / `--sort new|hot` / `--page` / `--limit`（≤100）。

## hivelet get —— 拉取笔记（元数据 + 整份 md）

```bash
hivelet get 68                     # stdout：元数据 + file（frontmatter + 正文）
hivelet get 68 -o ~/notes/x.md     # 存本地（自动回写 hivelet.note_id）
hivelet get 68 --rev 1             # 历史版本
```

stdout 形态（元数据行 + 空行 + 整份 md）：

```
note 68  rev 2/2
XekRung(伏渊息壤)深度技术报告:把安全智能压缩进小模型
作者 thinkycx  可见性 private  更新 2026-10-18T09:02:11

---
access: priv
title: XekRung(伏渊息壤)深度技术报告:把安全智能压缩进小模型
description: 深度调研阿里安全 AGI Lab 的网络安全垂直领域大模型…
tags: [tech, security, llm, ai-agent]
refs: [https://arxiv.org/abs/2605.00072]
---

## 一、执行摘要
…
```

要点：
- `file` 与 push 输入对称：改完 `hivelet push <文件>`（note_id 已回写）即修改 = 追加 revision
- 私有笔记需 owner token；rev 1 是首版，`rev 2/2` 中前者是当前返回版本、后者是最新版

## hivelet assets —— 列蜜源 / 搜索

```bash
hivelet assets --q BV1a5Y36MEWM       # 按资源id搜（B站 BV 号直接搜）
hivelet assets --q Sam                 # 按标题片段搜
hivelet assets --q BusinessTime        # 按原作者/登记人搜
hivelet assets --sort honey --limit 10
hivelet assets --source bilibili
```

输出（每行：id、[平台]、标题、蜜数、最佳蜜 id、原作者、登记人）：

```
共 1 个蜜源
     3  [bilibili] Sam Altman 专访完整版  蜜 2 篇 最佳蜜 #3  — 搬运UP（登记 admin）
蜜源详情：curl $BASE_URL/api/v1/assets/<id>；蜂蜜列表：…/assets/<id>/notes；push 直连：hivelet push note.md --asset-id <id>
```

`--q` 匹配：标题 / 原作者 / 资源id（BV号、YouTube id 等）/ 登记人 username。

**push 预检提醒**（蜜源已存在时 stderr）：

```
ℹ 蜜源已存在：asset 3（bilibili/BV1a5Y36MEWM）已有 2 篇蜜，最佳蜜 #3
  继续推送将关联到该蜜源；也可以直连：hivelet push <file> --asset-id 3
```

## 常见操作流程

### 修改已有笔记（编辑闭环）
```bash
hivelet notes --mine                     # 找 note_id
hivelet get 68 -o ~/notes/x.md           # 拉回整份 md
# ……编辑文件（frontmatter 和/或正文）
hivelet push ~/notes/x.md --model <llm>  # 重推 = 追加 revision，元数据随 frontmatter 更新
```

### 给已有蜜源写新笔记
```bash
hivelet assets --source bilibili         # 找 asset_id
hivelet push note.md --asset-id 3        # 直连（不做 URL 提取）
```

### 查看蜜源下的蜂蜜（选最佳先读）
```bash
curl -s $BASE_URL/api/v1/assets/3/notes | python3 -m json.tool
hivelet get <note_id>
```
