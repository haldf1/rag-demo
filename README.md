# 企业知识库 RAG 演示

一个可本地运行的 RAG 检索与问答演示项目。项目从文档解析、分块、向量化开始，
使用向量检索和 BM25 混合排序组织上下文，再可选调用大模型生成带来源标注的回答。

默认样例数据为自制内容。所有样例文档均为虚构内容，仅用于技术演示，仓库不包含
真实业务数据。

## 核心功能

- 支持 Markdown、TXT、CSV、DOCX；PDF 需要可选安装 `pymupdf`
- 按标题和段落自动分块，默认块大小 400 字符、重叠 60 字符
- 支持三种嵌入方式：云 API、本地 `sentence-transformers`、离线哈希嵌入
- 使用向量检索和 BM25，通过 RRF 融合排序
- 可选使用 `BAAI/bge-reranker-v2-m3` 做 rerank 精排
- 支持模板答案和 OpenAI 兼容接口，例如 DeepSeek
- 提供企业风格 Web 页面，支持打字机效果和回答来源展示
- 文档库支持查看、上传、删除，并增量同步检索索引
- 支持本机和局域网访问
- 提供离线评测，包括 Recall、Precision、MRR、关键词命中率和成本对比

## RAG 流程

```text
文档解析
  -> 文档分块
  -> 向量化
  -> 向量检索 + BM25 检索
  -> RRF 融合
  -> 可选 rerank 精排
  -> 组装 Top-K 上下文
  -> 模板回答或 LLM 回答
  -> 返回答案和来源片段
```

## 环境要求

- Python 3.10+
- Windows、macOS 或 Linux

最小运行模式不需要下载本地模型，只使用基础依赖、哈希嵌入和模板答案。

## 最小运行模式

### 1. 创建虚拟环境

Windows：

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 创建配置文件

Windows：

```bat
copy .env.example .env
```

macOS / Linux：

```bash
cp .env.example .env
```

最小模式使用 `.env.example` 中的默认配置：

```text
RAG_EMBEDDING_BACKEND=hash
RAG_RERANK_ENABLED=false
RAG_LLM_API_KEY=
```

该模式会使用哈希嵌入和模板答案，不调用外部 API。

### 3. 构建索引

```bat
python scripts\build_index.py
```

macOS / Linux：

```bash
python scripts/build_index.py
```

### 4. 检查检索

```bat
python scripts\smoke_test.py
```

macOS / Linux：

```bash
python scripts/smoke_test.py
```

### 5. 启动 Web

```bat
python scripts\run_server.py
```

macOS / Linux：

```bash
python scripts/run_server.py
```

浏览器访问：

```text
http://127.0.0.1:8765
```

Windows 也可以双击：

```text
start_ui.bat
start_production.bat
```

两个脚本默认使用项目内的 `.venv\Scripts\python.exe`。如果 `.venv` 不存在，
脚本会输出明确的创建命令。`start_production.bat` 额外支持端口参数、局域网
地址显示、自动打开浏览器和重复启动检测。

## 可选模型模式

安装本地模型、PDF 解析和向量库相关依赖：

```bat
pip install -r requirements-optional.txt
```

在 `.env` 中启用本地嵌入和 rerank：

```text
RAG_EMBEDDING_BACKEND=local
RAG_EMBEDDING_MODEL=BAAI/bge-m3
RAG_RERANK_ENABLED=true
RAG_RERANK_MODEL=BAAI/bge-reranker-v2-m3
```

模型缓存目录可以按需设置：

```text
HF_HOME=
HF_HUB_OFFLINE=1
```

`HF_HUB_OFFLINE=1` 适合模型已经缓存的离线环境。首次下载模型时可以先设置为
`0`，下载完成后再恢复为 `1`。

PDF 解析使用 `pymupdf`；没有安装时，PDF 文件会解析失败，但不影响其他文档格式。

## `.env` 配置

常用配置如下：

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `RAG_DOCS_DIR` | 空 | 文档目录；留空时优先 `docs_input/`，否则使用 `sample_docs/` |
| `RAG_INDEX_PATH` | `data/index.json` | 检索索引输出位置 |
| `RAG_EMBEDDING_BACKEND` | `hash` | `hash`、`local` 或 `cloud` |
| `RAG_EMBEDDING_MODEL` | `BAAI/bge-m3` | 本地或云嵌入模型名 |
| `RAG_LLM_API_KEY` | 空 | 留空时使用模板答案 |
| `RAG_LLM_BASE_URL` | DeepSeek 示例地址 | OpenAI 兼容接口地址 |
| `RAG_LLM_MODEL` | `deepseek-chat` | LLM 模型名 |
| `RAG_LLM_TIMEOUT_SECONDS` | `30` | LLM 请求超时 |
| `RAG_LLM_DIRECT_FALLBACK` | `true` | 本地代理不可用时尝试直连 |
| `RAG_UI_HOST` | `0.0.0.0` | Web 监听地址 |
| `RAG_UI_PORT` | `8765` | Web 监听端口 |

完整的配置项和占位值见 `.env.example`。

## 构建与更新索引

首次构建：

```bat
python scripts\build_index.py
```

Web 文档库支持以下操作，并会自动增量更新索引：

- 上传支持的文档
- 删除文档
- 刷新目录
- 直接向 `docs_input/` 或 `sample_docs/` 复制或删除文件

网页上传或删除时只处理变化的文档，不需要全量重新计算所有向量。

## 启动 Web 服务

最小模式启动：

```bat
python scripts\run_server.py
```

生产启动脚本：

```bat
start_production.bat
```

自定义端口：

```bat
start_production.bat 9000
```

生产脚本会：

- 使用项目内 `.venv`
- 监听 `0.0.0.0`
- 显示网卡名称和局域网访问地址
- 自动打开 `http://localhost:<端口>`
- 检测端口是否已被占用

## 文件上传与删除

打开页面顶部“文档库”：

- 左侧显示当前文档目录中的文件、大小和修改时间
- 目录为空时显示“暂无文档”
- “添加”会打开系统文件选择器
- 新文件会写入实际文档目录并进入 RAG 检索
- 每个文件都可以从网页删除，原文档也可以删除
- 删除会同时移除实体文件和对应检索片段

支持上传的格式：

```text
md, markdown, txt, csv, docx, pdf
```

浏览器不会把文件的完整本机路径交给网页，上传时只使用文件名和文件内容。

## 局域网访问

服务默认监听 `0.0.0.0:8765`。

本机访问：

```text
http://localhost:8765
```

同一局域网的同事访问：

```text
http://你的局域网IP:8765
```

例如：

```text
http://192.168.x.x:8765
```

Windows 首次开放局域网访问时，运行：

```bat
allow_firewall.bat
```

自定义端口：

```bat
allow_firewall.bat 9000
```

详细部署和公网访问说明见 `DEPLOY.md`。

## 命令行问答

```bat
python scripts\query.py "试用期一般是多长时间？"
```

配置了 LLM 时使用大模型回答；未配置或连接失败时自动降级为模板答案。

## 评测

```bat
python scripts\run_eval.py
```

结果输出到：

```text
eval/results/eval_report.md
eval/results/metrics.json
```

当前演示数据的参考结果：

| 指标 | 数值 |
| --- | --- |
| Recall@Top-K | 1.000 |
| Precision@Top-K | 0.292 |
| MRR | 0.875 |
| 片段命中关键词率 | 0.952 |
| RAG 平均输入 tokens | 267 |
| 全量文档方案 tokens | 11940 |

评测结果为当前样例数据和配置下的参考值。

## 目录结构

```text
RAG/
├── rag_demo/
│   ├── static/              # Web 页面和样式
│   ├── answer.py            # 回答生成与 LLM 降级
│   ├── documents.py         # 文档解析
│   ├── chunker.py           # 文档分块
│   ├── embeddings.py        # 嵌入后端
│   ├── search.py            # 混合检索
│   ├── vector_store.py      # 索引存取
│   └── ui_server.py         # Web API 和静态服务
├── scripts/                 # 构建、查询、评测和启动入口
├── sample_docs/             # 演示文档
├── docs/                    # 项目过程文档
├── eval/                    # 评测集和结果
├── data/index.json          # 本地生成的索引，不提交
├── requirements.txt         # 基础依赖
├── requirements-optional.txt
├── .env.example
├── DEPLOY.md
├── FRONTEND_UPGRADE.md
├── SECURITY.md
└── LICENSE
```

## 已知限制

- Web 服务没有登录认证，默认只适合本机或可信局域网使用。
- 公开服务默认无认证，仅建议本机或可信局域网运行；不要直接暴露到公网。
- 公开部署前应增加身份认证、权限控制和请求频率限制。
- 当前索引为本地 JSON，适合演示和中小规模数据。
- 本地模型模式在 CPU 上首次加载和构建索引可能较慢。
- PDF 解析依赖 `pymupdf`，扫描件文字识别需要额外 OCR 方案。
- Windows 批处理脚本主要面向 Windows；macOS/Linux 使用命令行步骤。
- LLM 未配置、超时或网络不可用时，会自动使用模板答案。

## License

本项目使用 [MIT License](LICENSE)。

## English Quick Start

### Requirements

Python 3.10 or newer.

### Minimal Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
python scripts/build_index.py
python scripts/run_server.py
```

Open `http://127.0.0.1:8765`.

The default minimal configuration uses hash embeddings, template answers, and
does not require model downloads or an LLM API key.

### Optional Local Models

```bash
pip install -r requirements-optional.txt
```

Then set `RAG_EMBEDDING_BACKEND=local` and `RAG_RERANK_ENABLED=true` in `.env`.

### Windows Launchers

- `start_ui.bat`: local demo launcher
- `start_production.bat`: LAN launcher with port and IP information
- `allow_firewall.bat`: one-time Windows firewall setup

See `DEPLOY.md` for LAN, mobile hotspot, ngrok, and frp examples.

### License

MIT License. See [LICENSE](LICENSE).
