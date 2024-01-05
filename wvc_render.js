import WebVideoCreator, { VIDEO_ENCODER, logger } from "web-video-creator";


const data = process.argv.splice(2)[0]

wvc.config({
    mp4Encoder: VIDEO_ENCODER.NVIDIA.H264
});

// 创建单幕视频
const video = wvc.createSingleVideo({
    // 需要渲染的页面地址
    url: data.url,
    // 视频宽度
    width: 1920,
    // 视频高度
    height: 1080,
    // 视频帧率
    fps: 60,
    // 视频时长
    duration: data.full_time * 1000,
    // 视频输出路径
    outputPath: data.output_src,
    // 是否在cli显示进度条，默认是不显示
    showProgress: true
});

// 监听合成完成事件
video.once("completed", result => {
    logger.success(`渲染完成！\n视频时长: ${Math.floor(result.duration / 1000)}s\n耗费: ${Math.floor(result.takes / 1000)}s\nRTF: ${result.rtf}`)
});

// 启动合成
video.start();