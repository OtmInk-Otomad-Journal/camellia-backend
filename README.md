# 音之墨 Camellia Backend

本项目是目前正在 B 站上持续发布的音之墨音MAD排行榜的自动化合成脚本，主要使用 Python 语言编写。
目前是 Camellia 更新计划。

# 现行流程

* 数据获取 advanced_data_get.py
* 数据审核
* 过滤推荐 pick_filter.py
* 渲染视频 main_progress.py
* 封面设计
* 视频发布

# 前置环境

* 视频序列需要 FFmpeg 支持
* 视频渲染需要 Chrome 浏览器以及它的 Driver 支持。
* 后端地址需进行 HTTP 转发，在 render_prefix 修改相应地址。
* 前端模板需运行在 HTTP 环境中，在 web_prefix 修改相应地址。
* 字体至少需要 **HarmonyOS Sans SC** 、**Montserrat**，工具字体可添加 **TH-Tshyn**。