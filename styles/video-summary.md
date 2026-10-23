<!-- 标准同步自 ai-notes styles/video-summary.md（ai-notes-1.0.0，2026-10-11）。hivelet-skill 不依赖 ai-notes，仅复制维护。 -->
# 视频总结风格 — 学以致用的视频学习笔记

## 制作流程（B 站视频）

```bash
# 1. 转写（自动取 aid/cid、下载音频、whisper 生成逐行文字稿，幂等可重跑；工具属 media-summary skill）
bash ~/.claude/skills/media-summary-2.0.0/scripts/video-transcribe.sh <视频URL或BV号> [/tmp/bilibili_<前缀>]
#    → stdout 打印 aid/cid/duration/title（iframe 参数），文字稿在 <前缀>.txt

# 2. 新建笔记（英文 slug，日期前缀自动加）
bash $SKILL_DIR/scripts/ai-notes.sh new life "<英文slug>"

# 3. 按本文档模板写作，全量转写稿插入文末 details 折叠块
# 4. 发布：bash $SKILL_DIR/scripts/ai-notes.sh pub <file>（必须 pub 命令）
# 5. 验证：curl https://<域名>/ai-notes/<文件名>.html 含正文关键词（公开文件无 -pub 后缀）
```

## 原则

1. 四段固定结构：背景 → 总结 → 正文 → 参考，不增减顶级章节
2. **标题标准格式**：`<内容类型>｜<主体>（<YYYY-MM-DD>）：<主题概括>（全访谈）`——内容类型与 tags 的内容类型一致（人物采访/活动/演讲/课程）；主体：人物采访写 `人物 × 媒体`（人物在前，是检索锚点），活动写活动名，课程写 `课程名-集数`；日期是**采访/录制/活动日期**（≠ 视频发布日期 ≠ 笔记创建日期 filename 前缀），从官方信息或外部检索核实，拿不到精确日期时至少标注年月——同一人物/活动会被多次采访报道，日期是区分锚点；slug 建议也带采访日期（如 `dario-amodei-20260430`）。同一场采访被多个剪辑版搬运（完整版/节目精编版）时：标题用版本后缀区分（如「（全访谈・完整版）」「（节目版・含纪录片片段）」），slug 在采访日期后加版本后缀（`-full`/`-episode`），两篇笔记在 4.2 互见链接。示例：
   - `人物采访｜Dario Amodei × 彭博（2026-04-30）：Claude Code、就业冲击、五角大楼对决与 Mythos（全访谈）`
   - `活动｜America.gov 发布（2026-09-29）：马斯克×黄仁勋谈超级智能与能源，万斯谈 AI 监管（全访谈）`
3. 章节编号即框架：正文（三）与参考（四）的小节必须带编号（3.1、3.2……；4.1、4.2……），采访/对话类每个 Q 用三级编号标题（3.3.1、3.3.2……，标题即问题主题，不再用加粗 Q 行）；标题层级要能独立构成内容框架，在 TOC 中一目了然
4. 结论先行：核心观点放「总结」，3~5 条以内
5. 学以致用：TODO 按**角色分组**——普通人 / 程序员 / AI 浪潮同行者 / 投资者等（按视频内容适用的角色取舍，2~4 组），每组 1~3 条；每条从「**长期做有价值的事**」出发：可积累的习惯、可复用的框架、可持续跟踪的指标，不写一次性动作和"多复习几遍"这类空话
6. 播放器组件通用（`.video-float`，B 站/YouTube/自托管 `<video>` 均可）：正文开头；autoplay=0；**播放中且滚过才悬浮**右下角（三层播放检测）；悬浮态 resize:both 调大小；控件默认隐藏 hover 显示；📌 手动悬浮、✕ 退出
7. 框架图在 iframe 正下方，默认折叠（`<details>`），不占首屏
8. 参考分节编号：4.1 访谈/课程信息（元信息**一行展示**，｜分隔）、4.2 相关阅读（编号列表）、4.3 原文语录、4.4 原视频文字版
9. 原文语录：视频原话直接引用（blockquote），6~8 条金句，保留口语原味
10. 原视频文字版（全量转写）放文章**最后**，默认折叠（`<details>` + `<pre>` 逐行字幕格式）
11. TOC 是 md2html.py 全局行为（2026-10-03 起：桌面右上侧栏常显；窄屏**默认收起**、☰ 按钮在右上角、面板从顶部下展）
12. 标签包含**来源平台**（bilibili/youtube）和**内容类型**（人物采访/课程/演讲），如 `tags: [life, video-summary, bilibili, 人物采访]`
13. `<details>` 内含 markdown 内容时加 `markdown="1"` 属性（md2html 已启用 md_in_html 扩展），否则块内 markdown 不渲染

## 采访类视频变体（人物专访/对话节目）

- **正文用 QA 形式**：按"问 → 答"组织，每个话题一组；每个 Q 用三级编号标题（`#### 3.3.1 <问题主题>`）；**标题可以是提炼后的主题，但三级标题正下方必须保留完整问句行**（`**<提问者> 问**：<原始问句，含背景铺垫与括注>`）——提炼不等于丢信息，问句中的上下文（提问者的铺垫、限定语、括注）一条都不能少；**答（A）尽可能保留原汁原味的表达**——语气、比喻、口头禅翻译出来，不提炼成干巴巴的要点
- **英文采访的翻译**：以中文表达为主，专有名词/产品名保留英文（Grok、Optimus、Starship），**避免中英混杂的句子**
- **原文语录**按 QA 形式组织：问可转述（可加主题标签），答必须是转写原文逐字引用
- **原视频文字版**同样按 QA 组织：问标注主题，答保留转写原文逐字排版，不删减不改写；仍默认 `<details markdown="1">` 折叠
- **标题↔视频联动（必做，2026-10-23 从"可选"升级）**：每个小节标题**正下方**（正文行之前）加视频跳转 chip：`<a class="video-seek" data-t="<秒>">▶ MM:SS</a>`——时间戳从 whisper 转写时间轴（`[MM:SS --> ...]`）定位到该小节起点；没有 chips 的视频总结视为**不完整产物**（用户点击小节无法跳到视频对应位置）。注意：`video-transcribe.sh` 的 txt 输出没有时间轴，需用 `media-summary.sh transcribe --summary`（jsonl 段落数据含 start/end）或从 srt/json 输出取时间戳。点击由 video-float.js 重写 iframe src 的 `t` 参数实现跳转（跨域 iframe 唯一可靠方式），桌面端自动播放并进入悬浮跟踪状态；移动端浏览器（iOS Safari/Chrome 全系 WebKit）拦截一切重载后 iframe 的自动播放（连官方 `muted=1` 参数也无效，播放器 play() 带声被拒），video-float.js 自动降级为**定位暂停**（克隆新 iframe + autoplay=0），并弹出"已定位到 MM:SS，点击播放键开始"提示条。**chip 绝不能写进标题本身**（会进 TOC 产生嵌套 `<a>`，链接失效）

## 模板

### Frontmatter

```yaml
---
create: <YYYY-MM-DD HH:MM:SS>   # new 命令自动生成（UTC+8 秒级）
update: <YYYY-MM-DD HH:MM:SS>   # 内容有实质修改时手动更新（sync 不会自动刷）
author: <作者>
title: "<内容类型>｜<主体>（<YYYY-MM-DD>）：<主题概括>（全访谈）"
description: <一句话摘要：视频讲什么 + 最有价值的 1 个洞察>
category: <finance | tech | ...>
tags: [life, video-summary]
keywords: [<SEO 关键词>]
refs:
  - <原视频 URL>
---
```

### 正文结构

```markdown
# <标题>

## 一、背景

<!-- 问题：为什么看这个视频 / 遇到了什么问题 -->
<!-- 目标：看完想达到什么状态（可衡量） -->

## 二、总结

### 核心观点

<!-- 3~5 条，每条一句话，最关键的洞察 -->

### 学以致用 TODO

<!-- 按角色分组（2~4 组，按视频内容适用的角色取舍），每组 1~3 条，可打勾清单格式
     每条从「长期做有价值的事」出发：可积累的习惯、可复用的框架、可持续跟踪的指标
     常用角色：普通人 / 程序员 / AI 浪潮同行者 / 投资者 -->

**<角色一>（<该角色的长期价值定位>）**

- [ ] <可积累/可复用/可跟踪的具体动作>

**<角色二>（<定位>）**

- [ ] <...>

## 三、正文

### 3.1 在线观看

<!-- 只写 iframe，悬浮播放器由 md2html.py 自动增强（scripts/assets/video-float.css/.js）：
     播放中且滚过 → 右下角悬浮，可拖动（左上 ⠿）、可调大小（右下原生 resize 手柄）、✕ 退出；
     滚回自动还原，正文原位置大小不受影响 -->

<iframe src="https://player.bilibili.com/player.html?isOutside=true&aid=<aid>&bvid=<bvid>&cid=<cid>&p=1&autoplay=0&danmaku=0" scrolling="no" frameborder="no" framespacing="0" allowfullscreen="true" allow="autoplay; fullscreen; picture-in-picture" style="width:100%;max-width:900px;aspect-ratio:16/9;border:0;border-radius:8px;"></iframe>

<!-- B 站 aid/cid 从 https://api.bilibili.com/x/web-interface/view?bvid=<bvid> 获取
     YouTube: https://www.youtube.com/embed/<videoId>?autoplay=0
     自托管: 直接写 <video controls src="..."></video>，同样自动增强 -->

### 3.2 内容框架图（默认折叠）

<!-- 用 details 折叠，放在 iframe 正下方
     注意：summary 后和 </details> 前必须各留一个空行，否则代码块不会被渲染 -->

<details style="margin:16px 0;">
<summary><strong>📁 内容框架图（点击展开）</strong></summary>

```
<树状图内容>
```

</details>

### 3.3 <分节标题>

<!-- 按视频逻辑分节展开（3.3、3.4……）：案例、表格、概念辨析
     金句可以用 blockquote 穿插在对应小节
     采访/对话类：每个 Q 用三级编号标题 #### 3.3.1 <问题主题>，标题即问题 -->

#### 3.3.1 <问题主题>

<!-- 标题下第一行：完整问句（含提问者、背景铺垫、括注），信息不丢失 -->

**<提问者> 问**：<原始问句全文>

<!-- 答保留原汁原味表达 -->

## 四、参考

### 4.1 访谈/课程信息

<!-- 元信息一行展示（｜分隔） -->

**<类型>**：<课程名/活动名> ｜ 主讲/出场：<人名> ｜ 本集：<集数与标题>（约 <时长>） ｜ 来源：<平台 + UP主>

### 4.2 相关阅读

<!-- 编号列表：原视频 + 同系列/相关文章 -->

1. **原视频**：<原视频 URL>
2. **相关阅读**：[<标题>](<URL>) ・ [<标题>](<URL>)

### 4.3 原文语录（视频原话，whisper 转写）

> <视频原话，保留口语原味>

> <视频原话>

### 4.4 原视频文字版（全量转写，点击展开）

<details style="margin:16px 0;">
<summary><strong>📄 原视频文字版全文（whisper 本地转写，点击展开）</strong></summary>

<pre style="white-space:pre-wrap;font-size:13px;line-height:1.8;"><逐行字幕转写内容></pre>

</details>
```

## iframe 写法要求（B 站）

1. src 必须写完整 `https://player.bilibili.com/...`，**不要用 `//` 协议相对写法**（file:// 本地预览会挂）
2. 必须带内联样式撑开尺寸：`style="width:100%;max-width:900px;aspect-ratio:16/9;border:0;border-radius:8px;"`（默认只有 300×150）
3. 参数通过 bilibili API 获取：`https://api.bilibili.com/x/web-interface/view?bvid=<bvid>` 返回 `aid`、`cid`
4. 悬浮播放器**不用写在 md 里**——md2html.py 检测到 iframe/`<video>` 自动注入（`scripts/assets/video-float.css` + `video-float.js`）：播放中且滚过 → 右下角悬浮，可拖动（左上 ⠿）、可调大小（右下原生手柄）、✕ 退出；滚回还原且不影响正文原位置

## 写作检查清单

- [ ] 背景里有明确的问题和目标
- [ ] 标题（title + H1）符合标准格式 `<内容类型>｜<主体>（<日期>）：<主题概括>`，日期为采访/活动日期且与发布日期、创建日期区分清楚
- [ ] 核心观点 ≤ 5 条且每条独立成立
- [ ] 正文（三）与参考（四）小节带编号（3.1/3.2……、4.1~4.4），标题层级构成完整框架，TOC 可见
- [ ] TODO 按角色分组（2~4 组），每条是「长期做有价值的事」：可积累的习惯/可复用的框架/可持续跟踪的指标
- [ ] iframe 在正文开头（3.1），完整 https URL + 内联尺寸 + `autoplay=0&danmaku=0`，不写任何悬浮脚本
- [ ] 框架图在 iframe 下方（3.2），`<details>` 默认折叠，summary 前后有空行
- [ ] 采访类：每个 Q 用三级编号标题（3.3.1……），标题下保留完整问句行（提问者 + 原始问句 + 背景括注，信息不丢失），正文/语录/文字版均为 QA 形式，答保留原味；英文内容中文为主不混杂
- [ ] 参考分节：4.1 信息一行 ｜ 分隔、4.2 相关阅读编号列表、4.3 语录 blockquote、4.4 文字版折叠
- [ ] 标签含来源平台与内容类型
- [ ] 无个人信息（MIS、真实姓名等）
