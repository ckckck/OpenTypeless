# OpenTypeless

一个将豆包 ASR 能力封装为 OpenAI 兼容接口的小项目，支持 Docker 启动，并提供一份可配合 Spokenly 使用的参考修正提示词，实现和 Typeless 类似的语音修正效果。

## 项目目的

1. 提供豆包 ASR to API 功能（OpenAI 兼容），可通过 Docker 一键启动。
2. 提供一份参考修正提示词（见 `推荐提示词.md`），可配合 Spokenly 对语音转写结果做稳定整理与纠错。

## API 服务说明

- 服务根地址（Docker 映射后）：`http://127.0.0.1:8836`
- OpenAI 兼容前缀：`/v1`
- 主要接口：`POST /v1/audio/transcriptions`
- 模型列表：`GET /v1/models`
- 健康检查：`GET /health`

## Docker 启动

在项目根目录执行：

```bash
docker compose up -d --build
```

常用命令：

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f doubao-asr-api

# 停止
docker compose down
```

## Spokenly 配置参考

- URL：`http://127.0.0.1:8836`（不要手动加 `/v1`）
- 模型：`doubao-asr`
- API 密钥：按你的服务配置（未开启可留空）

说明：Spokenly 的 OpenAI 兼容模式会自动拼接 API 路径；若手动填写 `/v1`，可能变成重复路径（如 `/v1/v1/...`）并返回 `Not Found`。

## 参考提示词与关键应用场景

参考提示词文件：`推荐提示词.md`

该提示词重点覆盖以下场景：

1. **局部自我修正，不丢上下文**  
   例如“我想要苹果，不对，香蕉”，只修正当前片段，同时保留前后无关内容。

2. **多事项结构化输出**  
   识别“第一/第二/第三”等并列项时，转换为阿拉伯数字列表，且每项换行，输出更清晰。

3. **热词驱动纠错**  
   对专有名词（如 `DeepSeek`）进行发音近似纠错，减少 ASR 误识别。

4. **保留口语风格、删除无效语气词**  
   尽量保留用户说话习惯，同时清理“嗯/啊”等无实义语气词，提升可读性。
