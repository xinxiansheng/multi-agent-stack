# Quick Start

从一台裸 macOS 机器到跑通完整多 agent 体系，约 15 分钟。

## 前置条件

- macOS 13+ (Ventura or later)
- 管理员权限
- 至少一个 AI 模型 API Key (Anthropic / OpenAI / MiniMax)
- (可选) Telegram 账号 + Bot Token
- (可选) 钉钉企业应用（见 [DINGTALK.md](./DINGTALK.md)）

## Step 1: 克隆项目

```bash
git clone https://github.com/xinxiansheng/multi-agent-stack.git
cd multi-agent-stack
```

## Step 2: 配置环境变量

```bash
cp .env.template .env
nano .env   # 或用你喜欢的编辑器
```

必填项:
- `ANTHROPIC_API_KEY` — 至少填一个模型 API Key

通讯渠道（至少选一）:
- **Telegram:** `TG_NEXUS_BOT_TOKEN` + `TG_OBSERVER_BOT_TOKEN` + `TG_OWNER_USER_ID`
- **钉钉:** `DINGTALK_ENABLED=true` + `DINGTALK_APP_KEY` + `DINGTALK_APP_SECRET`

可选项:
- `HTTP_PROXY` — 如果需要代理访问 API
- `MINIMAX_API_KEY` / `NEWAPI_API_KEY` — 备用模型
- `VOLCENGINE_API_KEY` — OpenViking 知识库所需的向量嵌入

## Step 3: 一键部署

```bash
make setup
```

这个命令会自动:
1. 安装 Homebrew (如果没有)
2. 安装 Node.js, Python3, Git, gettext
3. 安装 OpenClaw 框架
4. 创建目录结构
5. 部署 Nexus + Observer 工作空间
6. 从 .env 生成 openclaw.json
7. 部署 Observer 采集管线
8. 部署 OpenViking 知识库 + Dashboard
9. (可选) 部署钉钉桥接服务
10. 安装运维脚本 (健康检查、日志轮转)
11. 注册 LaunchAgent 服务
12. 运行验证检查

## Step 4: 个性化配置

```bash
# 编辑你的用户画像（注入到每个 Agent 会话）
nano ~/.openclaw/workspace/USER.md

# 编辑 Observer 的关注领域
nano ~/.openclaw/workspace-observer/config/interests.md

# 编辑 Observer 的信源列表
nano ~/.openclaw/workspace-observer/config/sources.md
```

## Step 5: 验证

```bash
# 检查所有服务状态
make status

# 查看日志
make logs

# 和 Nexus 对话
openclaw chat

# 和 Observer 对话
openclaw chat --agent observer
```

### 验证各子系统

```bash
# OpenViking 知识库
curl http://localhost:2033/status

# Dashboard
open http://localhost:2034

# Observer 采集管线（dry-run 模式）
python3 ~/.openclaw/workspace-observer/scripts/collect.py --dry-run
```

## 日常操作

```bash
make status      # 查看服务状态
make logs        # 查看最近日志
make logs-follow # 实时跟踪日志
make restart     # 重启 Gateway
make config      # 重新生成 openclaw.json
make backup      # 备份配置和工作空间
make restore     # 从最新备份恢复
```

## 添加新 Agent

```bash
# 交互式创建
make new-agent

# 或直接指定参数
./new-agent.sh arbiter Arbiter "⚖️" "strategic advisor"
```

脚手架会自动:
1. 创建 workspace 目录和模板文件
2. 初始化 Git
3. 打印后续配置步骤（注册到 openclaw.json、创建 Telegram Bot 等）

## 启动 RSSHub（信息采集基础设施）

```bash
# 需要先安装 Docker
cd services/
docker compose up -d

# 验证
curl http://localhost:2035/
```

## 故障排除

### Gateway 无法启动
```bash
# 查看错误日志
tail -50 ~/.openclaw/logs/gateway.err.log

# 手动启动测试
openclaw gateway --port 18789

# 重新加载 LaunchAgent
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
```

### Telegram Bot 无响应
```bash
# 检查 Bot Token 是否正确
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# 检查代理连通性
curl -x http://127.0.0.1:7890 https://api.telegram.org/

# 查看 Gateway 日志中的 Telegram 相关错误
grep -i telegram ~/.openclaw/logs/gateway.log | tail -20
```

### 钉钉 Bot 无响应
```bash
# 查看桥接服务日志
tail -50 ~/.openclaw/logs/dingtalk.err.log

# 手动启动测试
source ~/.openclaw/dingtalk-bridge/.venv/bin/activate
python ~/.openclaw/dingtalk-bridge/bridge.py

# 验证 Gateway 可达
curl http://127.0.0.1:18789/api/v1/health
```

### OpenViking 知识库
```bash
# 查看日志
tail -50 ~/.openclaw/logs/openviking.err.log

# 手动启动测试
cd ~/projects/openviking-local
source .venv/bin/activate
python server.py --port 2033
```

### 配置变更后
```bash
# 重新生成 openclaw.json
make config

# 重启 Gateway 使配置生效
make restart
```

## 文件说明

```
multi-agent-stack/
├── .env.template          # 环境变量模板 → 拷贝为 .env 并填写
├── bootstrap.sh           # 一键部署主脚本
├── new-agent.sh           # Agent 脚手架工具
├── Makefile               # 常用操作入口
├── config/
│   ├── openclaw.template.json  # 主配置模板
│   └── generate-config.sh      # 配置生成脚本
├── agents/
│   ├── nexus/             # Nexus 工作空间模板
│   ├── observer/          # Observer 工作空间模板
│   └── _template/         # 新 Agent 空白模板
├── observer/
│   ├── scripts/           # collect.py, daily.py
│   └── config/            # sources.md, interests.md, scoring.md, web_sources.yaml
├── openviking/
│   ├── server.py          # MCP 知识库服务
│   ├── dashboard-server.py # Dashboard HTTP 服务
│   ├── build-dashboard.py # Dashboard 页面生成
│   ├── memory-sync.py     # Agent 记忆同步
│   └── setup.sh           # 安装脚本
├── dingtalk/
│   ├── bridge.py          # 钉钉 ↔ Gateway 桥接服务
│   ├── setup.sh           # 安装脚本
│   └── requirements.txt   # Python 依赖
├── launchd/
│   ├── templates/         # LaunchAgent plist 模板
│   ├── install.sh         # 批量注册
│   └── uninstall.sh       # 批量卸载
├── shared/
│   └── STATE.yaml         # 跨 Agent 共享状态
├── scripts/
│   ├── healthcheck.py     # 健康检查（每30分钟）
│   ├── logrotate.sh       # 日志轮转（每日03:00）
│   ├── status-check.sh    # 状态概览
│   └── morning-briefing.sh # 晨间简报（每日08:30）
├── services/
│   └── docker-compose.yml # RSSHub + Redis + Browserless
└── docs/
    ├── QUICKSTART.md      # 本文档
    ├── ARCHITECTURE.md    # 架构说明
    ├── MODELS.md          # 模型选型
    └── DINGTALK.md        # 钉钉集成指南
```
