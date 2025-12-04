import WebVideoCreator, { VIDEO_ENCODER, logger } from "web-video-creator";

const src = process.argv.splice(2);
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const data = require(src[0]);

const wvc = new WebVideoCreator();

// 读取.env 配置
import dotenv from "dotenv";
dotenv.config();

const config = {
  mp4Encoder: process.env.VIDEO_CODEC_OUT || VIDEO_ENCODER.CPU.H264,
  browserUseGPU: process.env.BROWSER_USE_GPU === "true",
  compatibleRenderingMode: process.env.COMPATIBLE_RENDERING_MODE === "true",
};

if (process.env.BROWSER_VERSION && process.env.BROWSER_VERSION.length > 0) {
  config.browserVersion = process.env.BROWSER_VERSION;
}

wvc.config(config);

// 创建单幕视频
const video = wvc.createSingleVideo({
  url: data.url,
  width: 1920,
  height: 1080,
  fps: 60,
  duration: data.chunk_time * 1000,
  outputPath: data.output_src,
  startTime: Math.floor(data.start_time * 1000),
  frameQuality: 100,
  // 码率
  audioBitrate: "320k",
  videoBitrate: "10000k",
  // browserFrameRateLimit: false,
  beginFrameTimeout: 20000,
  // Cli 的进度条
  showProgress: true,
  pagePrepareFn: async (page) => {
    const _page = page.target;
    await _page.evaluate((data) => {
      // 直到inject_wvc是存在的函数，再执行inject_wvc
      return new Promise((resolve) => {
        const checkInject = () => {
          if (typeof inject_wvc === "function") {
            inject_wvc(data);
            resolve(true);
          } else {
            setTimeout(checkInject, 100);
          }
        };
        checkInject();
      });
    }, data);
  },
});

// video.addAudio({
//   path: data.audio_src,
//   loop: false,
//   volume: 100,
// });

// 监听合成完成事件
video.once("completed", (result) => {
  logger.success(
    `渲染完成！\n耗费: ${Math.floor(result.takes / 1000)}s\nRTF: ${result.rtf}`
  );
  process.exit();
});

// 启动合成
video.start();
