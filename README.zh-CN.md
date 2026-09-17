# AI Logo Maker Skill

[English](./README.md) | 简体中文

输入品牌名、行业或参考图，生成多个 Logo 方向并打磨成可缩放的品牌标识，在 Claude Code、Codex 或 OpenClaw 里直接完成。

> [!IMPORTANT]
> 生成需要 [Beatra](https://beatra.ai) 账号并消耗积分，安装本身不收费。

| 问题 | 回答 |
| --- | --- |
| **能做什么** | 输入品牌名称、行业方向或参考图,生成专业 AI Logo、品牌标识和应用图标,支持多变体探索、精确品牌色和可缩放构图。 |
| **运行要求** | Python 3.10+，以及能加载 `SKILL.md` 的 Agent |
| **费用** | 安装免费。每次生成消耗 Beatra 账号积分，只有你明确要求这次生成或批准确认卡后才会付费。 |
| **支持的 Agent** | Claude Code、Codex、OpenClaw |

<p align="center"><img src="assets/hero.webp" width="800" alt="为虚构精品咖啡烘焙品牌 Brightmoss 探索的三个 logo 方向：咖啡豆与嫩叶组合标、带咖啡滴负形的 B 字母标、杯上日出徽章。由 Beatra AI 生成。"></p>

*为虚构精品咖啡烘焙品牌 Brightmoss 探索的三个 logo 方向：咖啡豆与嫩叶组合标、带咖啡滴负形的 B 字母标、杯上日出徽章。由 Beatra AI 生成。*

| Skill | Entry point | Version |
| --- | --- | --- |
| [`ai-logo-maker`](skills/ai-logo-maker) | [SKILL.md](skills/ai-logo-maker/SKILL.md) | 0.1.7 |

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

也可以克隆本仓库，把 `skills/ai-logo-maker` 复制到 `~/.claude/skills/`（Claude Code）、`~/.agents/skills/`（Codex）或 `~/.openclaw/skills/`（OpenClaw）。

或者把下面这段话发给你的 Agent：

```text
从 https://github.com/beatra-ai/ai-logo-maker-skill 安装 ai-logo-maker skill（目录 skills/ai-logo-maker），然后按它的 SKILL.md 连接我的 Beatra 账号。
```

## 效果示例

<p align="center"><img src="assets/demo-2.webp" width="800" alt="选定的 Brightmoss 咖啡豆嫩叶方向，进一步细化为 App 图标和横版文字组合标。由 Beatra AI 生成。"></p>

*选定的 Brightmoss 咖啡豆嫩叶方向，进一步细化为 App 图标和横版文字组合标。由 Beatra AI 生成。*

提示词：

```text
Refine this accepted Brightmoss logo into a two-part brand presentation on one flat warm cream background (#F4EEE2). Left: an app icon, a solid rounded square in deep forest green (#1F4D3A) with the same coffee-bean-and-leaf symbol from the image centered inside in cream, generous padding, no text in the icon. Right: a horizontal lockup, the same green bean-and-leaf symbol placed to the left of the exact word "Brightmoss" in the same bold humanist sans-serif lettering, forest green, vertically centered with the symbol. Keep the symbol shape and the wordmark letterforms identical to the source. Flat vector, maximum two colors, no gradients, no shadows, no mockup, no tagline, no other text.
```

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

## 更新

安装后的 skill 每天最多检查一次新版本，替换前先校验官方归档，任何一步失败都不会动你已安装的版本。
随时可以关闭，见 skill 内的 `references/automatic-updates-and-safety.md`。

## 许可证

[MIT-0](LICENSE)：可自由使用、修改和再分发，包括商用，无需署名；与这些 skill 在 ClawHub 上的条款一致。
