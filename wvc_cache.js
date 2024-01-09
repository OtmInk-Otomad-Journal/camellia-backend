import WebVideoCreator, { VIDEO_ENCODER, logger } from "web-video-creator";
// 用于手动清理缓存。
const wvc = new WebVideoCreator();
wvc.cleanBrowserCache();
wvc.cleanLocalFontCache();
wvc.cleanPreprocessCache();
wvc.cleanSynthesizeCache();