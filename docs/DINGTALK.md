# DingTalk Integration

钉钉桥接服务，将钉钉企业应用消息双向桥接到 OpenClaw Gateway。

## 架构

```
钉钉用户 ←[Stream API]→ dingtalk-bridge.py ←[HTTP API]→ OpenClaw Gateway (:18789) → Agent
```

- 使用钉钉 Stream API（长连接），无需公网暴露
- 桥接服务部署为 macOS LaunchAgent，自动重连
- 通过 Gateway HTTP API 转发消息，复用已有的 Agent 路由逻辑

## Step 1: 创建钉钉企业应用

1. 打开 [钉钉开放平台](https://open-dev.dingtalk.com/)
2. 登录你的企业管理员账号
3. 进入「应用开发」→「企业内部开发」→「创建应用」

### 应用配置

- **应用名称:** AI Assistant（或你喜欢的名称）
- **应用类型:** 企业内部应用

### 权限配置

在「权限管理」中开启以下权限：
- `qyapi_robot_sendmsg` — 企业机器人发消息
- `qyapi_chat_manage` — 群会话管理

### 机器人配置

1. 进入「消息推送」→ 开启「Stream 模式」
2. 记录下 **AppKey** 和 **AppSecret**

### 添加到群

1. 在目标钉钉群中，添加你创建的应用机器人
2. 用户 @机器人 发消息即可触发

## Step 2: 配置 .env

```bash
# 在 .env 中填入
DINGTALK_ENABLED=true
DINGTALK_APP_KEY=your_app_key_here
DINGTALK_APP_SECRET=your_app_secret_here

# 指定由哪个 Agent 处理钉钉消息（默认 main = Nexus）
DINGTALK_AGENT_ID=main
```

## Step 3: 部署

如果尚未运行 bootstrap，直接运行即可自动部署：

```bash
make setup
```

如果已经部署过，手动安装钉钉桥接：

```bash
# 安装桥接服务
./dingtalk/setup.sh

# 重新安装 LaunchAgent（会自动包含钉钉服务）
./launchd/install.sh
```

## Step 4: 验证

```bash
# 检查服务状态
launchctl list | grep dingtalk

# 查看日志
tail -f ~/.openclaw/logs/dingtalk.log

# 手动测试
source ~/.openclaw/dingtalk-bridge/.venv/bin/activate
python ~/.openclaw/dingtalk-bridge/bridge.py
```

在钉钉群中 @机器人 发送消息，应收到 AI 回复。

## 配置说明

### Agent 路由

默认所有钉钉消息路由到 Nexus（`DINGTALK_AGENT_ID=main`）。

Nexus 会根据意图自动调度到合适的 Agent（Observer、Arbiter 等），无需为每个 Agent 配置单独的钉钉机器人。

### 消息格式

- **收到消息:** 钉钉 Markdown → 纯文本 → 发给 Agent
- **回复消息:** Agent 纯文本 → 钉钉 Markdown 格式回复
- 支持 @提及触发和私聊触发

## 故障排除

### 桥接服务启动失败

```bash
# 检查错误日志
tail -50 ~/.openclaw/logs/dingtalk.err.log

# 常见问题：
# 1. AppKey/AppSecret 错误 → 检查 .env 配置
# 2. Gateway 未启动 → make restart
# 3. Python 依赖缺失 → source ~/.openclaw/dingtalk-bridge/.venv/bin/activate && pip install -r dingtalk/requirements.txt
```

### 消息发出但无回复

```bash
# 检查 Gateway 是否在运行
curl http://127.0.0.1:18789/api/v1/health

# 检查 Gateway 日志
tail -50 ~/.openclaw/logs/gateway.log
```

### Stream 连接断开

桥接服务内置自动重连机制（5 秒间隔）。如果持续断开：

1. 检查网络连接
2. 确认应用在钉钉开放平台处于「已发布」状态
3. 确认 Stream 模式已开启
