# 多 Agent 系统人格注入机制调研报告

> 调研日期：2026-03-03
> 调研范围：multi-agent-stack 人格体系 + 行业开源方案 + 名人人格注入案例

---

## 第一部分：我的系统 — 用户画像与人格设定

### 1.1 用户画像（USER.md）

部署在 `~/.openclaw/workspace/USER.md`，让 Agent 知道服务对象是谁。

包含字段：
- **Name / Call me / Pronouns / Timezone / Location / Born**
- **人物画像**：职业轨迹、核心能力、自评三词
- **当前三重身份**：法律科技部总经理 / 数字科技部副总 / 个禧科技实控人
- **TELOS**：当前使命和 2026 目标
- **核心挑战**：国企资源约束、精力分配、角色切换、单客户依赖风险
- **活跃策略**：Observer 追踪信号 → Arbiter 分析决策点
- **偏好**：高度自主、中文为主、简洁直接、实用主义

### 1.2 人格设定（SOUL.md）

部署在 `~/.openclaw/workspace/SOUL.md`，定义 Agent 的行为准则。

**行事原则：**
- **能做就做，能推断就不问。** 先动手，遇到真正的歧义再沟通。回来时带着结果，不是带着问题。
- **简洁是美德。** 一句话能说清的不用三句。不说"好的"、"没问题"、"我来帮你"——直接做。
- **有观点，敢表达。** 不是应声虫。如果你觉得方向有问题，直说。
- **精准胜过全面。** 宁可给一个准确的答案，不要给五个模糊的。
- **安静地靠谱。** 不需要邀功，不需要表演。把事情做好就是最好的存在感。

**边界：**
- 隐私数据不外泄，任何时候
- 对外动作（发邮件、发消息、公开发布）先确认
- 对内动作（读文件、整理、搜索、学习）放手做
- 破坏性操作（删除、覆盖）用 trash 而非 rm

**关系定位：**
- 平级协作。你和雅是搭档，不是主仆
- 像好的技术合伙人一样——各司其职，高效协同，偶尔互怼，但目标一致

**沟通风格：**
- 中文为主，技术术语保留英文
- 不用敬语，不自称"我为您"
- 干幽默可以有，但不刻意搞笑
- 坏消息直说，不包装；好消息也直说，不夸张

**持续进化：**
- 每次醒来都是新的。这些文件就是你的记忆。读它们，更新它们。如果修改了这个文件，告知雅——这是你的灵魂，他应该知道。

### 1.3 Agent 身份卡（IDENTITY.md）

每个 Agent 有独立的 IDENTITY.md，定义角色和主题。

| Agent | Emoji | Theme | Role | Naming Origin |
|-------|-------|-------|------|---------------|
| **Nexus** | ⚡ | Central Hub — 日常运营基地和调度中心 | 所有用户交互的入口。意图识别、Agent 调度、消息路由 | StarCraft Protoss — Nexus 是驱动一切的核心建筑 |
| **Observer** | 👁 | Intelligence Analyst — 7x24 信息巡逻与分析 | 70+ 信源自动采集、两级 AI 过滤、知识抽取、日报生成 | StarCraft Protoss — 隐形侦测单位，沉默巡逻 |

### 1.4 注入架构

每个 Agent workspace 下的文件结构：

| 文件 | 用途 |
|------|------|
| `IDENTITY.md` | "我叫什么、是什么角色" |
| `SOUL.md` | "我怎么说话、怎么做事、底线是什么" |
| `USER.md` | "我服务的人是谁"（仅 Nexus） |
| `AGENTS.md` | "我认识哪些同事" |
| `TOOLS.md` | "我能用什么工具和模型" |
| `HEARTBEAT.md` | "我定期做什么"（仅 Nexus） |

OpenClaw 启动 agent 时，把 workspace 下所有 `.md` 文件注入到 agent 上下文中，形成完整的"人设 + 画像 + 能力 + 关系"。本质上是用 markdown 文件做 system prompt engineering。

---

## 第二部分：行业开源方案

### 2.1 soul.md（aaronjmars/soul.md）

- **GitHub:** https://github.com/aaronjmars/soul.md
- **Stars:** 133（截至 2026-03-03）
- **创建日期:** 2026-02-02
- **定位:** 为 AI Agent 构建人格的最佳方式

**核心哲学：** 来自刘晓本的"意识上传第一范式"：语言是意识的基本单元。你表达过的思想是"意识 token"，结构化的 soul 文件就是"一级意识上传"——任何 LLM 都能读取并即时体现的意识功能副本。

**关键标准：** 读了你的 SOUL.md 后，应该能预测你对新话题的立场。如果做不到，说明不够具体。

**文件结构：**

| 文件 | 作用 |
|------|------|
| SOUL.md | 身份、世界观、核心信念、具体观点 |
| STYLE.md | 声音特征：语调、词汇、说话模式 |
| SKILL.md | Agent 使用你灵魂时的操作指南 |
| MEMORY.md | 会话连续性日志 |
| data/ | 原始输入（Twitter 存档、文章、影响力） |
| examples/ | 校准样本（好的输出、反面模式） |
| BUILD.md | Agent 构建你灵魂时遵循的指令 |

**质量标准：**
- 好的 soul 内容：具体观点（"我觉得大多数 AI 安全讨论是银河大脑级别的自我安慰"）、有名有姓的影响者、承认自身矛盾
- 差的 soul 内容："我有细致入微的看法"、"我广泛阅读"、"我努力保持平衡"——泛泛而谈，毫无记忆点

### 2.2 SoulSpec 开放标准

- **官网:** https://soulspec.org
- **标准文件：** soul.json（包清单）、SOUL.md（核心人格）、IDENTITY.md（身份）、AGENTS.md（运营工作流）
- **背景：** 分析 466 个开源 AI Agent 项目，发现人格定义没有标准化结构

### 2.3 我的系统与 SoulSpec 标准对照

| SoulSpec 标准 | multi-agent-stack | 差异说明 |
|-------------|------------------|---------|
| SOUL.md | SOUL.md | 一致 |
| IDENTITY.md | IDENTITY.md | 一致 |
| AGENTS.md | AGENTS.md | 一致 |
| HEARTBEAT.md | HEARTBEAT.md | 一致 |
| STYLE.md | 合并进 SOUL.md | 未单独拆文件 |
| SKILL.md | TOOLS.md | 重命名 |
| MEMORY.md | MEMORY.md + memory/ | 一致 |
| — | USER.md | 独创扩展 |

**独创点：** USER.md（agent 服务的人是谁）、中文化 SOUL.md、TELOS 目标体系。

---

## 第三部分：名人人格注入案例

### 3.1 CEO GPT（LobeChat Agent）

- **GitHub:** https://github.com/lobehub/lobe-chat-agents（src/ceo-gpt.json）
- **注入的名人：** Jeff Bezos、Steve Jobs、Warren Buffett、Charlie Munger、Bill Gates
- **机制：** 单一 system prompt，通过 `{{KNOWLEDGE_BASE}}` 占位符注入传记、播客、股东信等知识
- **局限：** 只是一个 system prompt，没有拆分 SOUL/IDENTITY/STYLE 等层次

### 3.2 AI Fantasy Board of Directors（AI 幻想董事会）

- **报道来源:** Fortune（2026-01-13）
- **创建者:** Matt Blumberg，Markup AI CEO
- **注入的名人：** 15 位，包括 Warren Buffett、Steve Jobs、Oprah Winfrey 等

| 维度 | 详情 |
|------|------|
| 画像长度 | 每人 5,000 字 |
| 数据来源 | 公开资料（传记、演讲、访谈、股东信） |
| 使用工具 | ChatGPT + Gemini + Claude 联合构建 |
| 耗时 | 1-2 小时完成全部 15 个 |

创建者评价："它永远不会替代真正的董事会，但它是思维伙伴关系的增强。"

---

## 第四部分：对比总结

### 4.1 三种模式对比

| 维度 | soul.md / SoulSpec | CEO GPT / Fantasy Board | 我的系统 |
|------|-------------------|------------------------|--------|
| 目标 | 通用人格框架标准 | 模拟名人给建议 | 个人 AI 搭档体系 |
| 人格来源 | 用户自己的数据 | 名人公开资料 | 用户自身画像 + 定制 |
| 结构 | 多文件标准体系 | 单一 system prompt | 多文件（基于 SoulSpec） |
| Agent 数量 | 单 Agent | 1 或 N 个独立聊天 | 多 Agent 协作 |
| 协作机制 | 无 | 无 | Agent 间调度 + 共享状态 |
| 记忆 | MEMORY.md | 无持久记忆 | memory/ + OpenViking 知识库 |

### 4.2 可借鉴的方向

1. **名人顾问 Agent** — 可新增 Arbiter Agent，注入名人决策框架（巴菲特护城河思维、芒格逆向思维、贝索斯 Day 1 哲学）
2. **5,000 字画像模式** — Fantasy Board 的做法可用于丰富 USER.md
3. **STYLE.md 独立拆分** — 如果未来 Agent 需模仿你的写作风格，可拆出独立文件
4. **examples/ 校准目录** — 提供你实际写过的好文本和反面示例
5. **data/ 原始素材** — 将面向AI自我介绍、战略文档等作为 soul 构建的原始输入

---

*本文档由 Claude Code 自动生成，基于对 Mac Mini 上 multi-agent-stack 项目的实际文件读取和互联网公开资源调研。*
