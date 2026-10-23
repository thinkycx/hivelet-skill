<!-- 标准同步自 ai-notes styles/default.md（ai-notes-1.0.0，2026-10-11）。hivelet-skill 不依赖 ai-notes，仅复制维护。 -->
# 默认风格 — 技术写作

## 原则

1. 问题驱动：每篇文章解决一个明确问题
2. 结论先行：核心发现在第二部分加粗一句话
3. 扁平结构：最多 3 级标题
4. 行动导向：结尾给出具体 Action
5. 数据支撑：论点需要证据（代码、日志、Benchmark）

## 模板

```yaml
---
create: <YYYY-MM-DD>
update: <YYYY-MM-DD>
author: <作者>
title: <标题>
description: <一句话描述>
category: <troubleshooting | research | architecture | workflow>
tags: [tag1, tag2]
keywords: [keyword1, keyword2]
refs:
  - <相关链接>
---
```

```markdown
# <标题>

## 一、背景

<!-- 问题：一句话定义核心问题 -->
<!-- 目标：解决后的理想状态，可量化的衡量指标 -->

## 二、结论

<!-- **核心结论加粗一句话** -->
<!-- 支撑依据：编号列表，5 条以内 -->

## 三、主要内容

<!-- **第三部分是文章主要内容，需要尽可能丰富** -->

### 3.1 <子主题>


## 四、Action
<!-- 具体下一步行动、命令、决策 -->


## 参考链接
```

## 写作规则
- 正文中文，代码/命令/专有名词用英文
- 段落短小（不超过 5 行）
- 结构化对比用表格
- 代码块标注语言
- 不用套话（"本文将介绍..."、"众所周知..."）
- 文件命名：`YYYY-MM-DD-<english-slug>.md`

## 图片规范

- 存放在 workspace 内的 `assets/` 目录
- 命名：`YYYY-MM-DD-<描述性名称>.<ext>`
- 引用：`![描述](assets/YYYY-MM-DD-name.png)`
