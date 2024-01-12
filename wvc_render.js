import WebVideoCreator, { VIDEO_ENCODER, logger } from "web-video-creator";

const src = process.argv.splice(2)
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const data = require(src[0])

const wvc = new WebVideoCreator();

wvc.config({
    mp4Encoder: VIDEO_ENCODER.INTEL.H264
});

// 创建单幕视频
const video = wvc.createSingleVideo({
    url: data.url,
    width: 1920,
    height: 1080,
    fps: 60,
    duration: data.full_time * 1000,
    outputPath: data.output_src,
    frameQuality: 100,
    // 码率
    audioBitrate: "320k",
    videoBitrate: "10000k",
    // GPU 加速
    browserUseGPU: true,
    browserFrameRateLimit: false,
    // Cli 的进度条
    showProgress: true,
    pagePrepareFn: async page => {
        const _page = page.target;
        await _page.evaluate(function(data){
            setTimeout(inject_wvc(data),1000);
        },data)
    }
});

video.addAudio({
    path: data.audio_src,
    loop: false,
    volume: 100
});

// 监听合成完成事件
video.once("completed", result => {
    logger.success(`渲染完成！\n耗费: ${Math.floor(result.takes / 1000)}s\nRTF: ${result.rtf}`);
    process.exit();
});

// 启动合成
video.start();