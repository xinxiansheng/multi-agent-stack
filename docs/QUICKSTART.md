# Quick Start

从一台裸 macOS 机器到跑通完整多 agent 体系，约 15 分钟。

## 前置条件

- macOS 13+ (Ventura or later)
- 管理员权限
- 至少一个 AI 模型 API Key (Anthropic / OpenAI / MiniMax)
- (可选) Telegram 账号 + Bot Token

## Step 1: 克隆项目

```bash
# 把 openclaw-stack 目录拷贝到目标机器
scp -r openclaw-stack/ user@target-mac:~/openclaw-stack/
# 或者直接在本机操作
cd ~/openclaw-stack
```

## Step 2: 配置环境变量

```bash
cp .env.template .env
nano .env   # 或用你喜欢的编辑器
```

必填项:
- `ANTHROPIC_API_KEY` — 至少填一个模型 API Key
- `TG_NEXUS_BOT_TOKEN` — Telegram 主 Bot Token（通过 @BotFather 创建）
- `TG_OBSERVER_BOT_TOKEN` — Observer 的 Bot Token
- `TG_OWNER_USER_ID` — 你的 Telegram User ID

可选项:
- `HTTP_PROXY` — 如果需要代理访问 API
- `MINIMAX_API_KEY` / `NEWAPI_API_KEY` — 备用模型

## Step 3: 一键部署

```bash
make setup
```

这个命令会自动:
1. 安装 Homebrew (如果没有)
2. 安装 Node.js, Python3, Git
3. 安装 OpenClaw 框架
4. 创建目录结构
5. 部署 Nexus + Observer 工作空间
6. 从 .env 生成 openclaw.json
7. 安装运维脚本 (健康检查、日志轮转)
8. 注册 LaunchAgent 服务
9. 运行验证检查

## Step 4: 个性化配置

```bash
# 编辑你的用户画像（注入到每个 Agent 会话）
nano ~/.openclaw/workspace/USER.md

# 编辑 Observer 的关注领域
nano ~/.openclaw/workspace-observer/SOUL.md
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

## 日常操作

```bash
make status      # 查看服务状态
make logs        # 查看最近日志
make logs-follow # 实时跟踪日志
make restart     # 重启 Gateway
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

### 配置变更后
```bash
# 重新生成 openclaw.json
make config

# 重启 Gateway 使配置生效
make restart
```

## 文件说明

```
openclaw-stack/
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
├── launchd/
│   ├── templates/         # LaunchAgent plist 模板
│   ├── install.sh         # 批量注册
│   └── uninstall.sh       # 批量卸载
├── services/
│   └── docker-compose.yml # RSSHub + Redis + Browserless
├── scripts/
│   ├── healthcheck.py     # 健康检查（每30分钟）
│   ├── logrotate.sh       # 日志轮转（每日03:00）
│   └── status-check.sh    # 状态概览
└── docs/
    ├── QUICKSTART.md      # 本文档
    └── ARCHITECTURE.md    # 架构说明
```
