# 音之墨 Camellia Backend

本项目是目前正在 B 站上持续发布的音之墨音 MAD 排行榜的自动化合成脚本，主要使用 Python 语言编写。
目前是 Camellia 更新计划。

# 现行流程

- 面板操作
- 数据获取
- 数据审核
- 下载视频
- 渲染视频
- 封面设计
- 视频发布

# 配置指导

## 配置字体包

字体至少需要 **HarmonyOS Sans SC** 、**Montserrat**，工具字体可添加 **TH-Tshyn**。

## 安装 pip 包

请先配置 Python 环境，然后执行下面的命令。

```bash
pip install -r requirements.txt
```

## 安装并配置 ffmpeg

前往 [ffmpeg 官网](https://ffmpeg.org/) 下载并配置。

## 配置 Lux

下载 [Lux](https://github.com/iawia002/lux) 并置于本项目的根目录下。

## 安装 Node.js

安装 [Node.js](https://nodejs.org/en/download/) 并配置好环境变量。

## 配置 npm 包

执行下面的命令以获取 [WebVideoCreator](https://github.com/Vinlic/WebVideoCreator) 引擎等。

```bash
npm install
```

## 配置 .env

将 `.env.template` 复制以新建你的 `.env` 文件，并替换其中的变量。

## 配置前端 / 后端文件

将本项目的根目录使用合适的引擎进行 HTTP 转发，将地址放在 `.env` 的 `WEB_PREFIX` 字段中，用于网页渲染的本地文件获取地址，需要包含最后一个斜杠。

将[前端](https://github.com/OtmInk-Otomad-Journal/camellia-frontend)部署在合适的目录，并使用合适的引擎架设网页服务器，用于网页渲染的在线模板端，将地址放在 `.env` 的 `RENDER_PREFIX` 字段中，**无需包含最后一个斜杠**。

`PANEL_PREFIX` 将用于管理面板前端的后端访问。

## 配置审核后端

如果你的审核和管理方均在同一台主机上，则可以不需要执行该步骤。

在远程目录下同样 clone 该项目并配置环境，配置 `ONLINE_AUTH_KEY`，`ONLINE_PORT`，该项需和管理主机的一致。

随后在远程主机执行下列命令以启动远程审核后端：

```bash
python auditor_panel_api.py
```

## 配置审核面板

将[管理面板前端](https://github.com/OtmInk-Otomad-Journal/camellia-panel) clone 于合适的目录下。

如果不是默认端口，请修改对应 `src/common/config.ts` 下的端口。

将对应项目下的 `.env` 中的 `VITE_IDENTITY` 设为 `"AUDITOR"`，`VITE_ONLINE_API_URL` 设为审核面板访问其后端的地址（该项和部署位置有关，如果是远程主机请填写上一步暴露的 API 地址，如果是本地主机请填写`http://localhost:xxxx/`）。

构建，将构建后的目录进行 HTTP 转发，并使用合适的引擎架设网页服务器。

此时便可访问审核面板。

## 配置管理后端

运行下面以启动管理后端。

```bash
python panel_api.py
```

## 配置管理面板

将[管理面板前端](https://github.com/OtmInk-Otomad-Journal/camellia-panel) clone 于合适的目录下。

如果不是默认端口，请修改对应 `src/common/config.ts` 下的端口。

将对应项目下的 `.env` 中的 `VITE_IDENTITY` 设为 `"ADMIN"`。如果想要面板和管理后端分离，请修改对应 `src/common/config.ts` 下的对应地址。

构建，将构建后的目录进行 HTTP 转发，并使用合适的引擎架设网页服务器。

此时便可访问管理面板。
