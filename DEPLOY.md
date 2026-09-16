# RAG 演示部署说明

基础安装、构建索引和最小模式说明见 `README.md`。本文只说明启动、局域网、
手机热点和公网访问。

## 启动前准备

Windows 项目内虚拟环境：

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

需要本地语义模型、PDF 解析或 Chroma 时：

```bat
.venv\Scripts\python.exe -m pip install -r requirements-optional.txt
```

创建 `.env` 并构建一次索引：

```bat
copy .env.example .env
.venv\Scripts\python.exe scripts\build_index.py
```

## 生产启动

双击：

```text
start_production.bat
```

默认使用：

- 虚拟环境：`.venv`
- 监听地址：`0.0.0.0`
- 端口：`8765`
- 本机地址：`http://localhost:8765`

自定义端口：

```bat
start_production.bat 9000
```

脚本会显示端口占用检查、网卡名称和局域网访问地址，并在服务启动后自动打开
本机浏览器。

## 局域网访问

同事需要与服务器位于同一局域网，然后访问：

```text
http://你的局域网IP:8765
```

例如：

```text
http://192.168.x.x:8765
```

查看网卡 IPv4：

```bat
ipconfig
```

也可以直接查看 `start_production.bat` 输出的 WLAN 或以太网地址。不要使用
`localhost` 或 `127.0.0.1` 发给其他设备。

## Windows 防火墙

首次允许局域网或手机访问时，双击：

```text
allow_firewall.bat
```

在弹出的 UAC 提示中选择“是”。默认放行 TCP `8765`；使用其他端口时：

```bat
allow_firewall.bat 9000
```

检查监听：

```bat
netstat -ano | findstr ":8765"
```

出现 `0.0.0.0:8765` 表示服务已接受局域网连接。

## 手机热点访问

1. 电脑连接手机热点。
2. 运行一次 `allow_firewall.bat`。
3. 双击 `start_production.bat`。
4. 在命令行找到 `WLAN` 网卡的 IPv4 地址。
5. 手机访问 `http://电脑WLAN地址:8765`。

例如：

```text
http://172.20.x.x:8765
```

手机热点常见网段为 `172.20.10.x`，实际地址以脚本输出为准。

## 公网访问

不建议直接暴露本机端口。临时演示可以使用内网穿透工具。

### ngrok

服务启动后执行：

```bat
ngrok http 8765
```

ngrok 会输出公网地址，例如：

```text
https://example-name.ngrok-free.app
```

其他端口：

```bat
ngrok http 9000
```

演示结束后及时关闭 ngrok。

### frp

有固定公网服务器时，可以使用 TCP 转发：

```ini
[common]
server_addr = 你的公网服务器IP
server_port = 7000
token = 自定义令牌

[rag-web]
type = tcp
local_ip = 127.0.0.1
local_port = 8765
remote_port = 18765
```

启动 `frpc` 后访问：

```text
http://你的公网服务器IP:18765
```

## 停止与排错

- 关闭 `start_production.bat` 窗口或按 `Ctrl+C` 停止服务。
- 端口被占用时，换端口启动或关闭已有进程。
- 局域网无法访问时检查防火墙规则和网卡地址。
- 公网部署前必须确认 `.env` 没有进入版本控制。

当前 Web 服务没有登录认证，只建议在可信网络中运行。
