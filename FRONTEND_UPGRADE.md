# 前端改造与上线说明

快速安装和配置请优先查看 `README.md`，局域网、防火墙和公网部署请查看
`DEPLOY.md`。本文保留前端改造范围、验证结果和上线注意事项。

## 一、改动文件清单

| 文件 | 说明 |
| --- | --- |
| `rag_demo/static/index.html` | 企业风格页面结构、文档库模态框、文件选择、文件删除、问答交互和打字机效果 |
| `rag_demo/static/style.css` | 深蓝与金色企业风格、响应式布局、模态框、文件列表和状态样式 |
| `rag_demo/ui_server.py` | 文档列表、文件上传、文件删除、索引同步和单实例端口监听 |
| `rag_demo/config.py` | 默认监听地址改为 `0.0.0.0`，补充 LLM 超时和直连回退配置 |
| `rag_demo/answer.py` | LLM 超时、代理失败降级、未配置 LLM 时的友好提示 |
| `rag_demo/search.py` | 支持索引重新加载和空索引场景 |
| `rag_demo/vector_store.py` | 支持增量更新索引并保存目录签名 |
| `start_production.bat` | 生产启动脚本，支持自定义端口、局域网 IP 提示和自动打开浏览器 |
| `allow_firewall.bat` | 一次性提权并放行 Windows 防火墙端口，支持手机热点访问 |
| `start_ui.bat` | 原有本机演示启动方式 |
| `.gitignore` | 排除 `.env`、日志、缓存和生成索引 |
| `requirements.txt` | 基础运行依赖 |
| `LICENSE` | MIT 许可证 |
| `SECURITY.md` | 安全报告与部署说明 |
| `.env.example` | 补充监听地址、端口、LLM 超时和代理直连配置 |
| `README.md` | 补充运行和索引说明 |
| `DEPLOY.md` | 局域网、防火墙、ngrok 和 frp 部署说明 |
| `FRONTEND_UPGRADE.md` | 本文档 |

## 二、新增功能说明

### 1. 企业风格前端

- 深蓝 `#1a2a4a` 与金色 `#c9a84c` 配色。
- 顶部包含站点标识、导航菜单和清空对话按钮。
- 问答区采用左侧用户问题、右侧知识助手回答的布局。
- 回答支持打字机效果，发送按钮带加载状态。
- 适配桌面和移动端，无横向滚动。

### 2. 文档库

- 左侧“已有文档”读取真实的 `docs_input` 目录。
- 如果 `docs_input` 不存在，则回退到 `sample_docs`。
- 目录为空时显示“暂无文档”。
- 每个文件显示文件名、大小、修改时间和文件类型。
- 每个文件都提供“删除”按钮，原有文档也可以删除。
- “刷新”按钮会重新读取实际目录并同步检索索引。

### 3. 文件添加

- 点击“添加”会打开系统文件资源管理器。
- 支持 `.md`、`.markdown`、`.txt`、`.csv`、`.docx` 和 `.pdf`。
- 文件会写入实际文档目录，并立即参与 RAG 检索。
- 新增时只向量化新文档，不需要全量重建索引。
- 删除时只移除对应文档和向量，不需要重新计算其他文档。
- 文件元数据会保存到浏览器 `localStorage`。

### 4. 检索索引同步

- 网页上传或删除后，服务端自动更新索引。
- 直接修改 `docs_input` 或 `sample_docs` 后，刷新文档库或下一次提问时会自动检测变化。
- 索引文件保存目录签名；文件新增、删除或修改后只处理变化部分。

### 5. 局域网访问

- 服务默认监听 `0.0.0.0:8765`。
- 本机访问：`http://localhost:8765`
- 同一局域网同事访问：`http://你的局域网IP:8765`

## 三、访问方式

### 本机与局域网

- 本机：`http://localhost:8765`
- 局域网：`http://电脑局域网IP:8765`
- 自定义端口：`start_production.bat 9000`
- Windows 防火墙：首次运行 `allow_firewall.bat`

详细步骤见 `README.md` 和 `DEPLOY.md`。

## 四、上线前检查结果

本次检查结果如下：

| 检查项 | 结果 |
| --- | --- |
| `start_production.bat` | 可正常启动服务 |
| 服务监听地址 | `0.0.0.0:8765` |
| 重复启动保护 | 检测到端口占用后拒绝启动第二个实例 |
| 文档目录读取 | 当前回退目录为 `sample_docs`，读取 9 个文件 |
| 空目录状态 | 显示“暂无文档” |
| 问答功能 | 正常返回，来源为大模型 |
| 打字机效果 | 已触发，测试耗时约 2.6 秒 |
| 浏览器错误 | 无控制台错误 |
| 1366x768 | 无横向溢出，模态框完整显示 |
| 1920x1080 | 无横向溢出，模态框完整显示 |

## 五、常见问题

### 1. 端口 8765 被占用

启动脚本会自动检测并提示：

```text
Port 8765 is already in use.
```

可以关闭已有服务，或者换端口启动：

```bat
start_production.bat 9000
```

查看占用端口的进程：

```bat
netstat -ano | findstr ":8765"
```

### 2. 同事无法访问

检查以下内容：

- 服务是否显示监听 `0.0.0.0:8765`。
- 同事是否与服务器在同一局域网。
- 地址是否使用服务器局域网 IP，而不是 `localhost`。
- Windows 防火墙是否放行 TCP 端口。
- 是否已经运行过一次 `allow_firewall.bat`。

管理员 PowerShell 放行端口：

```powershell
New-NetFirewallRule -DisplayName "RAG Demo 8765" -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow
```

### 3. 手机连接电脑热点后如何访问

1. 电脑连接手机热点。
2. 运行 `allow_firewall.bat` 并在 UAC 提示中选择“是”。
3. 运行 `start_production.bat`。
4. 在命令行找到 `WLAN` 网卡的 IPv4 地址。
5. 手机访问 `http://电脑WLAN地址:8765`。

### 4. `docs_input` 目录不存在

系统会回退到 `sample_docs`。如果想使用自己的文档目录，在项目根目录创建：

```text
docs_input
```

然后重新启动服务。

### 5. 文档库显示“暂无文档”

说明当前活动目录存在但没有可显示文件。检查：

- `docs_input` 是否为空。
- 文件是否为支持的格式。
- 文件是否被系统隐藏。

### 6. 新增文档后没有命中

检查：

- 文件是否实际出现在 `sample_docs` 或 `docs_input`。
- 文件格式是否为 `.md`、`.txt`、`.csv`、`.docx` 或 `.pdf`。
- 服务日志是否出现“检索索引已增量同步”。
- PDF 解析是否安装了 `pymupdf`。

### 7. 回答仍然使用模板答案

检查 `.env`：

```text
RAG_LLM_API_KEY
RAG_LLM_BASE_URL
RAG_LLM_MODEL
```

如果本地代理不可用，代码会尝试直连 LLM。详细错误会显示在页脚和回答中，不会直接暴露 WinError 堆栈。

### 8. 如何停止服务

关闭 `start_production.bat` 所在的命令行窗口，或按 `Ctrl+C`。

## 六、安全提醒

- 当前 Web 服务没有登录认证，任何能访问局域网地址的人都可以查询、上传和删除文档。
- 不建议直接暴露到公网。
- 临时公网演示可使用 ngrok 或 frp，参见 `DEPLOY.md`。
- 正式上线前建议增加身份认证、权限控制和操作审计。
