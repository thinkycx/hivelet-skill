<!-- 标准同步自 ai-notes styles/daily-log.md（ai-notes-1.0.0，2026-10-11）。hivelet-skill 不依赖 ai-notes，仅复制维护。 -->
# 日报风格

触发词：`daily-log`、`写日报`、`工作日志`、`总结今天`、`生成日报`

本风格不使用标准正文模板（不需要"背景→结论→主要内容→Action"结构），使用专用日报格式。

## 文件位置

- 日报：`daily-log/YYYY-MM-DD.md`
- Prompts 记录：`daily-log/prompts/YYYY-MM-DD-prompts.txt`

## 工作流（完整步骤）

### Step 1: 提取当日 prompts 并保存

```bash
DATE="$(date +%Y-%m-%d)"  # 或用户指定的日期
PROMPTS_DIR="$NOTES_DIR/daily-log/prompts"
mkdir -p "$PROMPTS_DIR"
python3 "$SKILL_DIR/scripts/extract-daily-prompts.py" "$DATE" > "$PROMPTS_DIR/${DATE}-prompts.txt"
```

脚本从 `~/.claude/projects/` 提取当天所有会话的用户 prompt，输出到文件。

### Step 2: 阅读 prompts，生成日报

1. 读取 `$PROMPTS_DIR/${DATE}-prompts.txt` 的完整内容
2. 基于 prompts 内容分析当日实际工作
3. 按照下方模板格式写入 `daily-log/$DATE.md`
4. 产出链接从 ai-notes 目录查找对应的 pub 文件，生成正确的 `.html` URL

### Step 3: sync 上传（PRIV）

```bash
cd "$NOTES_DIR" && bash "$SKILL_DIR/scripts/ai-notes.sh" sync "daily-log/$DATE.md"
```

### Step 4: 返回结果

输出给用户：
- VIEW_URL（从 sync 输出中解析）
- Prompts 文件：`daily-log/prompts/$DATE-prompts.txt`
- 日报文件：`daily-log/$DATE.md`

## 模板

```yaml
---
create: YYYY-MM-DD
update: YYYY-MM-DD
author: thinkycx
title: 工作日志 YYYY-MM-DD
category: workflow
tags: [daily-log]
refs:
  - <当日关键产出链接(.html)>
---
```

```markdown
# 工作日志 YYYY-MM-DD

## 今日工作

| 优先级 | 方向 | 工作项 | 时间 | 工作内容与产出 |
|--------|------|--------|------|---------------|
| P0 | ... | ... | ~Xh | 做了什么。产出：[名称](正确的URL) |
| P1 | ... | ... | ~Xh | 做了什么。产出：— |

## 复盘

**主线：** 一句话描述主线 + 聚焦度评价

**可复利迁移资产：** 列出换公司不归零的产出

**消耗性工作：** 列出纯运维/调试类工作

1. ...（3-5 条核心收获，每条一句话，写可迁移的洞察）

**改进建议：**

1. ...（3 条，基于当天 session 模式给出具体可操作的改进建议）

## 明日 Action [draft]

- [ ] P0 — ...（最多 3 条，对照本月目标确认后删 [draft] 标记）

## 附录：Session 汇总

按起始时间排序。同一项目连续的 session 可合并为一行。

| ID | 时间 | Prompts | 项目 | 内容摘要 |
|----|------|---------|------|----------|
| S01 | HH:MM~HH:MM | N | 项目名 | 一句话描述该 session 做了什么 |
| S02-04 | HH:MM~HH:MM | N | 项目名 | 同一项目多个 session 可合并 |
```

## 关联文件

- 本月目标：`daily-log/YYYY-MM-goals.md`（只放里程碑，不设 backlog）
- Prompts 记录：`daily-log/prompts/YYYY-MM-DD-prompts.txt`
- 日报 Action 是 AI 基于当天惯性给的建议（[draft]），用户对照月度目标人工确认后生效

## 规则

1. 关注事实和产出，不描述过程
2. 时间估算取近似值，精确到 0.5h
3. "核心收获"写可迁移的洞察，不是任务描述
4. 复盘部分保持扁平结构，不用三级标题，用加粗标记区分段落
5. Action 必须标 [draft]，等人工确认后才生效
6. **必须先执行 extract-daily-prompts.py 提取并保存 prompts，再基于 prompts 内容生成日报**
7. 日报基于 prompts 的实际内容生成，不靠猜测
8. 产出链接必须指向正确的 `.html` URL（pub文件从 ai-notes 目录确认后生成）
