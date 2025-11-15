# 部分运行故障修复笔记

## 内存占用过大导致闪退

该情形下可分块渲染。

## 分块视频黑屏修复

该问题源自 web-video-creator 对视频终止时间的判断有误。

对 `node_modules/web-video-creator/core/CaptureContext.js` 的第 645 行进行修改：

```javascript
endTime: Math.min(e.getNumberAttribute("end-time") || e.getNumberAttribute("endTime") || Infinity, this.config.duration + this.startTime + 1000),
```

## MacOS 环境下的浏览器渲染报错

前往 `wvc_render.js` 将对应内容改成下面的：

```javascript
wvc.config({
  browserVersion: "141.0.7390.108", // wvc 默认拉取的旧版本在 Mac 下有问题，因此必须指定新版本
  browserUseGPU: false, // 没法用
  compatibleRenderingMode: true, // 兼容渲染模式
});
```

然后，注释掉 `/Library/Camellia/camellia-backend/node_modules/web-video-creator/media/VideoCanvas.js` 大概第 532 行的位置：

```javascript
decoder.configure({
  // 视频信息配置
  ...config,
  // 解码器硬件加速指示
  // hardwareAcceleration: this.hardwareAcceleration,
  // 关闭延迟优化，让解码器批量处理解码，降低负载
  optimizeForLatency: true,
});
```

这样应该就能解决问题了。

玩得愉快！
