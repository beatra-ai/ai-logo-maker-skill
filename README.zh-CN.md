# AI Logo Maker Skill

[English](./README.md) | 简体中文 | [日本語](./README.ja.md)

> 👉 也看看 [AI Poster Maker Skill](https://github.com/beatra-ai/ai-poster-maker-skill)

输入品牌名、行业或参考图，生成多个 Logo 方向并打磨成可缩放的品牌标识，在 Claude Code、Cursor、Codex、Windsurf、Cline 或 OpenClaw 里直接完成。

> [!IMPORTANT]
> 生成需要 [Beatra](https://beatra.ai?utm_source=github&utm_medium=flagship&utm_campaign=ai-logo-maker-skill) 账号并消耗积分，安装本身不收费。

| 问题 | 回答 |
| --- | --- |
| **能做什么** | 输入品牌名称、行业方向或参考图,生成专业 AI Logo、品牌标识和应用图标,支持多变体探索、精确品牌色和可缩放构图。 |
| **底层模型** | Qwen Image 2.0 Fast、Qwen Image 3.0、Qwen Image 3.0 Pro、GPT Image 2.5 Flare、GPT Image 2.5 Sunburst、GPT Image 2、Wan Image 2.7 Fast、Qwen Image 2.0 Pro、Wan Image 2.7 Pro、MiniMax Image 01 Live、Wan 2.7、Wan 3.0 Video、MiniMax H3、Seedance 2.0 Mini、HappyHorse 1.1、Seedance 2.0 Fast、Seedance 2.0、Wan 3.0 Video Prime、Seedance 2.5 |
| **运行要求** | Python 3.10+，以及能加载 `SKILL.md` 的 Agent |
| **费用** | 安装免费。每次生成消耗 Beatra 账号积分，只有你明确要求这次生成或批准确认卡后才会付费。 |
| **支持的 Agent** | Claude Code、Cursor、Codex、Windsurf、Cline、OpenClaw |

<p align="center"><img src="assets/hero.webp" width="800" alt="为虚构精品咖啡烘焙品牌 Brightmoss 探索的三个 logo 方向：咖啡豆与嫩叶组合标、带咖啡滴负形的 B 字母标、杯上日出徽章。由 Beatra AI 生成。"></p>

*为虚构精品咖啡烘焙品牌 Brightmoss 探索的三个 logo 方向：咖啡豆与嫩叶组合标、带咖啡滴负形的 B 字母标、杯上日出徽章。由 Beatra AI 生成。*

| Skill | Entry point | Version |
| --- | --- | --- |
| [`ai-logo-maker`](skills/ai-logo-maker) | [SKILL.md](skills/ai-logo-maker/SKILL.md) | 0.2.9 |

本仓库由 [beatra-ai/beatra-skills](https://github.com/beatra-ai/beatra-skills/tree/main/skills/ai-logo-maker) 自动发布，问题请到那里反馈。

## 安装

使用 [`skills`](https://skills.sh) CLI：

```bash
npx skills add beatra-ai/ai-logo-maker-skill
```

使用 GitHub CLI：

```bash
gh skill install beatra-ai/ai-logo-maker-skill ai-logo-maker
```

也可以克隆本仓库，把 `skills/ai-logo-maker` 复制到 `~/.claude/skills/`（Claude Code）、`~/.cursor/skills/`（Cursor）、`~/.agents/skills/`（Codex）、`~/.codeium/windsurf/skills/`（Windsurf）、`~/.cline/skills/`（Cline）或 `~/.openclaw/skills/`（OpenClaw）。

或者把下面这段话发给你的 Agent：

```text
从 https://github.com/beatra-ai/ai-logo-maker-skill 安装 ai-logo-maker skill（目录 skills/ai-logo-maker），然后按它的 SKILL.md 连接我的 Beatra 账号。
```

## 效果示例

<p align="center"><img src="assets/demo-2.webp" width="800" alt="选定的 Brightmoss 咖啡豆嫩叶方向，进一步细化为 App 图标和横版文字组合标。由 Beatra AI 生成。"></p>

*选定的 Brightmoss 咖啡豆嫩叶方向，进一步细化为 App 图标和横版文字组合标。由 Beatra AI 生成。*

在你的 Agent 里这样说：

```text
把已定稿的 Brightmoss 豆与叶 Logo 做成一个深墨绿圆角方形的 App 图标，再配一个横版文字标组合，两者放在同一张暖米色背景上。
```

提示词：

```text
Refine this accepted Brightmoss logo into a two-part brand presentation on one flat warm cream background (#F4EEE2). Left: an app icon, a solid rounded square in deep forest green (#1F4D3A) with the same coffee-bean-and-leaf symbol from the image centered inside in cream, generous padding, no text in the icon. Right: a horizontal lockup, the same green bean-and-leaf symbol placed to the left of the exact word "Brightmoss" in the same bold humanist sans-serif lettering, forest green, vertically centered with the symbol. Keep the symbol shape and the wordmark letterforms identical to the source. Flat vector, maximum two colors, no gradients, no shadows, no mockup, no tagline, no other text.
```

## 技术规格与输出限制

截至 2026-10-18。实时列表：https://docs.beatra.ai/zh/docs/models

- **上传** — 单个文件最大 100 MB；同时适用下方各模型的输入限制
- **文生图** — 10 个模型（Qwen Image 2.0 Fast、Qwen Image 3.0、Qwen Image 3.0 Pro、GPT Image 2.5 Flare、GPT Image 2.5 Sunburst、GPT Image 2、Wan Image 2.7 Fast、Qwen Image 2.0 Pro、Wan Image 2.7 Pro、MiniMax Image 01 Live）；PNG；单次最多 4 张；画布最大 16.8 MP
  - 16.8 MP（4K 档）：Wan Image 2.7 Pro（单次最多 4 张）；GPT Image 2.5 Flare、GPT Image 2.5 Sunburst、GPT Image 2（单次 1 张）
- **图生图** — 10 个模型（Qwen Image 2.0 Fast、Qwen Image 3.0、Qwen Image 3.0 Pro、Wan Image 2.7 Fast、Qwen Image 2.0 Pro、Wan Image 2.7 Pro、GPT Image 2.5 Flare、GPT Image 2.5 Sunburst、GPT Image 2、MiniMax Image 01 Live）；PNG；单次最多 4 张；画布最大 16.8 MP
  - 16.8 MP（4K 档）：GPT Image 2.5 Flare、GPT Image 2.5 Sunburst、GPT Image 2（单次 1 张）
  - 输入图片：单次最多 4 张，每张 10–20 MB；BMP、GIF、JPEG、PNG、TIFF、WEBP
- **图片编辑** — 6 个模型（Qwen Image 2.0 Fast、Qwen Image 3.0、Qwen Image 3.0 Pro、Wan Image 2.7 Fast、Qwen Image 2.0 Pro、Wan Image 2.7 Pro）；PNG；单次最多 4 张；画布最大 4.2 MP
  - 4.2 MP（2K 档）：Qwen Image 2.0 Fast、Qwen Image 3.0、Qwen Image 3.0 Pro、Wan Image 2.7 Fast、Qwen Image 2.0 Pro、Wan Image 2.7 Pro（单次最多 4 张）
  - 输入图片：单次最多 4 张，每张 10–20 MB；BMP、GIF、JPEG、PNG、TIFF、WEBP
- **图生视频** — 9 个模型（Wan 2.7、Wan 3.0 Video、MiniMax H3、Seedance 2.0 Mini、HappyHorse 1.1、Seedance 2.0 Fast、Seedance 2.0、Wan 3.0 Video Prime、Seedance 2.5）；480p 至 4K；2–30 秒；画幅 16:9、1:1、21:9、3:4、4:3、9:16；MOV、MP4
  - 4K：Seedance 2.0，最长 15 秒
  - 30 秒：Wan 3.0 Video、Wan 3.0 Video Prime、Seedance 2.5，最高 1080p
  - 原生音频：Wan 2.7、MiniMax H3

## 为什么用 Beatra，而不是直接调用模型 API

- **一个账号用到本 skill 的全部模型** — 文生图 10；图生图 10；图片编辑 6；图生视频 9（Qwen Image 2.0 Fast、Qwen Image 3.0、Qwen Image 3.0 Pro、GPT Image 2.5 Flare、GPT Image 2.5 Sunburst、GPT Image 2、Wan Image 2.7 Fast、Qwen Image 2.0 Pro、Wan Image 2.7 Pro、MiniMax Image 01 Live、Wan 2.7、Wan 3.0 Video、MiniMax H3、Seedance 2.0 Mini、HappyHorse 1.1、Seedance 2.0 Fast、Seedance 2.0、Wan 3.0 Video Prime、Seedance 2.5）（截至 2026-10-18），一次 Beatra 登录即可使用，不必分别管理各家模型的 key。
- **花不花钱由你决定** — 只有你明确要求这次生成，或批准显示实时积分估算的确认卡后才会付费。
- **先策划，再生成** — skill 先帮你规划、指导和检查，再在 Beatra 上生成。
- **文件可以核验** — `skills/` 下的每个文件都与 cdn.beatra.ai 上的发布归档逐字节一致，每次推送前用 SHA-256 校验。
- **更新由你掌控** — 不含自更新程序；用安装时的工具更新。
- **在你的 Agent 里运行** — Claude Code、Cursor、Codex、Windsurf、Cline、OpenClaw。

## 你能得到什么

- **先探索再决定** — 从一个品牌简报生成多个 logo 概念,并排比较不同方向,然后精修最强的那个。专业 logo 设计从选项开始。
- **为每个尺寸而生** — 每个概念都为 favicon 清晰度、应用图标精度和社交头像冲击力而设计。强轮廓和精简配色,从 16 像素到广告牌都可辨认。
- **你的精确品牌色** — 用 hex 值和加权调色板锁定精确品牌色,让 logo 承载你的品牌身份,而非随机配色。

## 适用场景

- **新企业和创业公司 logo** — 从公司名称和行业出发,获得专业品牌标识,在确定方向前比较多个概念。
- **应用图标与产品标识** — 创建适合应用商店、favicon、软件仪表盘和产品发布的方形图标,内置安全区域留白。
- **从已有素材刷新品牌** — 将草图、灵感板或已有 logo 转化为精致的现代标识,同时保留原始方向。
- **社交媒体与内容品牌化** — 打造头像、水印和一致的视觉标识,贯穿各平台和内容格式。

## 常见问题

### 我可以创建哪些 logo 风格?

文字标、字母标、图形标、抽象标、徽章和组合标。分享品牌名称、行业和想要的感觉,工具会推荐最适合的风格。

### 我的 logo 在很小的 favicon 上也清晰吗?

每个概念都以小尺寸可辨认为目标设计——强轮廓、高对比度和最少细节。在缩略图大小检查结果后再定稿。

### 我能匹配已有的品牌色吗?

可以。提供 hex 颜色值,logo 生成将以它们为调色板基础,实现精确的加权颜色控制。

### 我能改进已有的 logo 吗?

可以。上传已有 logo 或草图,描述需要改变的地方,精修会保留整体方向同时调整具体元素。

## 更新与安全

自 2026 年 10 月的版本起，本 skill 不再包含自更新程序：它只运行你安装的文件，从不自行替换。
请用安装时的工具更新——`npx skills update ai-logo-maker` 或 `gh skill update ai-logo-maker`。
详见 skill 内的 `references/updates-and-security.md`。

## 许可证

[MIT-0](LICENSE)：可自由使用、修改和再分发，包括商用，无需署名；与这些 skill 在 ClawHub 上的条款一致。

## 相关链接

- 官网 — https://www.beatra.cn?utm_source=github&utm_medium=flagship&utm_campaign=ai-logo-maker-skill
- 文档 — https://docs.beatra.cn?utm_source=github&utm_medium=flagship&utm_campaign=ai-logo-maker-skill
- 控制台 — https://console.beatra.cn
- 给 AI Agent 读的说明 — https://www.beatra.cn/llms.txt （索引）· https://www.beatra.cn/llms-full.txt （全部 skill 合成一个文件）

- 微信小程序 — 国内用户微信扫码使用

<img src="assets/beatra-mini-program-qr.jpg" alt="Beatra 微信小程序码" width="160">
