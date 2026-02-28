# OpenTypeless

一个将豆包 ASR 能力封装为 OpenAI 兼容接口的小项目，支持 Docker 启动，并提供一份可配合 Spokenly 使用的参考修正提示词，实现和 Typeless 类似的语音修正效果。

当前支持两种 ASR 后端：

1. **豆包 ASR to API 模式**：通过 `doubaoime-asr` 将豆包输入法 ASR 能力封装为 OpenAI 兼容转写接口。
2. **官方 API 方式**：接入官方录音文件识别，支持 **标准版** 与 **极速版**（App Key + Access Key）。

## 项目目的

1. 提供豆包 ASR to API 功能（OpenAI 兼容），可通过 Docker 一键启动。
2. 已增加官方 API 模式，在同一套 OpenAI 兼容接口下支持标准版与极速版切换。
3. 提供一份参考修正提示词（见 `推荐提示词.md`），可配合 Spokenly 对语音转写结果做稳定整理与纠错。

## API 服务说明

- 服务根地址（Docker 映射后）：`http://127.0.0.1:8836`
- OpenAI 兼容前缀：`/v1`
- 主要接口：`POST /v1/audio/transcriptions`
- 模型列表：`GET /v1/models`
- 健康检查：`GET /health`

`POST /v1/audio/transcriptions` 兼容 OpenAI 常用字段，并额外支持：

- `audio_url`（可选）：当使用官方标准版时可传音频 URL，服务端会优先按 URL 识别。

## 后端选择（重点）

你可以通过 `model` 参数在一次请求内选择后端：

- `doubao-asr`：豆包 ASR to API 模式
- `doubao-asr-official`：官方 API 方式（具体标准/极速由 `DOUBAO_ASR_OFFICIAL_MODE` 决定）
- `doubao-asr-official-standard`：官方标准版
- `doubao-asr-official-flash`：官方极速版

也可以通过环境变量设置默认后端：

- `DOUBAO_ASR_DEFAULT_BACKEND=ime`
- `DOUBAO_ASR_DEFAULT_BACKEND=official`

说明：如果传入了上述模型 ID，会优先按模型选择；否则回落到 `DOUBAO_ASR_DEFAULT_BACKEND`。

## 官方 API 模式配置

配置文件名：项目根目录下的 `.env`（可先从 `.env.example` 复制）。

启用官方 API 模式时至少需要配置：

- `DOUBAO_ASR_OFFICIAL_APP_KEY`
- `DOUBAO_ASR_OFFICIAL_ACCESS_KEY`

官方模式选择：

- `DOUBAO_ASR_OFFICIAL_MODE=standard`（标准版，submit/query 轮询）
- `DOUBAO_ASR_OFFICIAL_MODE=flash`（极速版，单次请求返回，默认）

可选配置：

- `DOUBAO_ASR_OFFICIAL_STANDARD_SUBMIT_ENDPOINT`（默认 `https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit`）
- `DOUBAO_ASR_OFFICIAL_STANDARD_QUERY_ENDPOINT`（默认 `https://openspeech.bytedance.com/api/v3/auc/bigmodel/query`）
- `DOUBAO_ASR_OFFICIAL_FLASH_ENDPOINT`（默认 `https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash`）
- `DOUBAO_ASR_OFFICIAL_STANDARD_RESOURCE_ID`（默认 `volc.seedasr.auc`）
- `DOUBAO_ASR_OFFICIAL_FLASH_RESOURCE_ID`（默认 `volc.bigasr.auc_turbo`）
- `DOUBAO_ASR_OFFICIAL_MODEL_NAME`（默认 `bigmodel`）
- `DOUBAO_ASR_OFFICIAL_UID`（默认 `opentypeless`）
- `DOUBAO_ASR_OFFICIAL_TIMEOUT_SEC`（默认 `120`）
- `DOUBAO_ASR_OFFICIAL_QUERY_INTERVAL_SEC`（标准版 query 轮询间隔，默认 `1.0`）
- `DOUBAO_ASR_OFFICIAL_QUERY_TIMEOUT_SEC`（标准版 query 总超时，默认 `300`）

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
- 模型：
  - `doubao-asr`（豆包 ASR to API）
  - `doubao-asr-official`（官方，按 `DOUBAO_ASR_OFFICIAL_MODE` 选择标准/极速）
  - `doubao-asr-official-standard`（官方标准版）
  - `doubao-asr-official-flash`（官方极速版）
- API 密钥：按你的服务配置（未开启可留空）

说明：Spokenly 的 OpenAI 兼容模式会自动拼接 API 路径；若手动填写 `/v1`，可能变成重复路径（如 `/v1/v1/...`）并返回 `Not Found`。

### Spokenly 快速配置（推荐）

1. 在项目根目录复制配置文件：

```bash
cp .env.example .env
```

2. 编辑 `.env`，至少填写以下字段：

```env
DOUBAO_ASR_API_KEY=sk-your-gateway-key
DOUBAO_ASR_DEFAULT_BACKEND=official
DOUBAO_ASR_OFFICIAL_MODE=flash
DOUBAO_ASR_OFFICIAL_APP_KEY=your-app-key
DOUBAO_ASR_OFFICIAL_ACCESS_KEY=your-access-key
```

3. 重启服务：

```bash
docker compose up -d --build
```

4. 在 Spokenly 中填写：

- URL：`http://127.0.0.1:8836`
- API Key：填写 `.env` 里的 `DOUBAO_ASR_API_KEY`
- 模型：`doubao-asr-official-flash`（推荐）

如果你想切到官方标准版：

- 模型改为 `doubao-asr-official-standard`
- 或保留模型 `doubao-asr-official`，把 `.env` 中 `DOUBAO_ASR_OFFICIAL_MODE` 改为 `standard`

## Docker 环境变量示例

在 `docker-compose.yml` 的 `environment` 下添加：

```yaml
# 默认后端（ime 或 official）
DOUBAO_ASR_DEFAULT_BACKEND: official

# 仅官方 API 模式需要
# DOUBAO_ASR_OFFICIAL_APP_KEY: your-app-key
# DOUBAO_ASR_OFFICIAL_ACCESS_KEY: your-access-key
# DOUBAO_ASR_OFFICIAL_MODE: flash
# DOUBAO_ASR_OFFICIAL_STANDARD_RESOURCE_ID: volc.seedasr.auc
# DOUBAO_ASR_OFFICIAL_FLASH_RESOURCE_ID: volc.bigasr.auc_turbo
# DOUBAO_ASR_OFFICIAL_MODEL_NAME: bigmodel
# DOUBAO_ASR_OFFICIAL_UID: your-uid
```

## 参考提示词与关键应用场景

参考提示词文件：`推荐提示词.md`

该提示词重点覆盖以下场景：

1. **纯复述修正，不做内容扩写**  
   仅做最小修正：去口吃/重复/语气词、纠错别字和标点、处理改口（如“不对/不是...是...”）。
2. **热词表纠错**  
   支持按热词表做发音近似替换，例如 `cloud code -> Claude Code`、`千问 -> Qwen`。
3. **枚举结构化**  
   将“第一、第二、第三”整理为 `1. 2. 3.` 数字列表，提升可读性。
4. **中文数字统一阿拉伯数字**  
   例如“三点五 -> 3.5”“一百二十 -> 120”，并在版本号、数量、编号、比分、手机号等场景统一数字格式。

示例（与当前提示词保持一致）：

```text
用户：帮我用cloud code写一个脚本
你：帮我用 Claude Code 写一个脚本

用户：GPT四点五的价格是每一百万token二十美元
你：GPT 4.5 的价格是每 100 万 token 20 美元

用户：我的手机号是一三八零零一三八零零零
你：我的手机号是 13800138000

用户：我一会儿出门要做三件事第一去超市买菜第二去银行取钱第三去接孩子放学然后晚上还得做饭
你：我一会儿出门要做三件事：
1. 去超市买菜
2. 去银行取钱
3. 去接孩子放学

然后晚上还得做饭
```

## License

MIT
