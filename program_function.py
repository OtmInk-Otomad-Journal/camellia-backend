import hashlib
import shutil
import requests
import logging
import subprocess
import codecs
import csv
import ffmpeg
import colorsys
import html
import pydub
import os
import yt_dlp

from io import BytesIO
from PIL import Image
import numpy as np
from haishoku.haishoku import Haishoku

from dataclasses import dataclass

# import yt_dlp


def get_img(aid):
    from config import api_header

    video_data = requests.get(
        url=f"https://api.bilibili.com/x/web-interface/view?aid={aid}",
        headers=api_header,
    ).json()
    face = video_data["data"]["owner"]["face"]
    cover = video_data["data"]["pic"]
    # 头像
    if not os.path.exists(f"./avatar/{aid}.png"):
        img_content = requests.get(url=face, headers=api_header).content
        img = Image.open(BytesIO(img_content))
        img.save(f"./avatar/{aid}.png")
    # 封面
    if not os.path.exists(f"cover/{aid}.png"):
        img_content = requests.get(url=cover, headers=api_header).content
        img = Image.open(BytesIO(img_content))
        img.save(f"./cover/{aid}.png")
    callback = {"avatar": f"./avatar/{aid}.png", "cover": f"./cover/{aid}.png"}
    return callback


def turnAid(id: str) -> str:
    """
    将 BV 号亦或 av 号统一转为不带「av」前缀的 av 号，返回字符串
    """
    from config import api_header

    if (id[0:2] == "av") or (id[0:2] == "AV"):
        return id[2:]
    elif "BV" in id:
        site = "https://api.bilibili.com/x/web-interface/view?bvid=" + id
        lst = codecs.decode(
            requests.get(site, headers=api_header).content, "utf-8"
        ).split('"')
        return str(lst[16][1:-1])


# 视频长度获取
def exactVideoLength(url):
    tdur = float(ffmpeg.probe(url)["streams"][0]["duration"])
    return tdur

# 复制视频
def copy_video(aid, newaid):
    shutil.copy(f"./video/{aid}.mp4",f"./video/{newaid}.mp4")

# 视频下载
def get_video(aid, part=1, cid=None, skipConvert=False):
    d_time = 0
    command = ["./lux"]
    if part > 1:
        p_src = f"?p={part}"
    else:
        p_src = ""
    if os.path.exists(f"./cookies/cookie.txt"):
        command.append("-c")
        command.append("./cookies/cookie.txt")
    if os.path.exists(f"./video/{aid}.mp4"):
        logging.info(f"av{aid} 视频已经存在")
        return f"./video/{aid}.mp4"
    while not os.path.exists(f"./video/{aid}.mp4"):
        d_time += 1
        if d_time <= 5:
            logging.info(f"第 {d_time} 次下载 av{aid} 视频...")
            process = subprocess.Popen(
                command + ["-o", "./video", "-O", str(aid), f"av{aid}{p_src}"],
                stdout=subprocess.PIPE,
                text=True,
                encoding="utf-8-sig",
            )
            for info in iter(process.stdout.readline, "b"):
                if process.poll() is not None:
                    break
                if len(info) != 0:
                    logging.info(info.replace("\n", ""))
        # 备用 yt-dlp
        if d_time > 5:
            logging.error(f"av{aid} 下载失败，请手动处理！")
            raise Exception("视频下载失败")
            # logging.info(f"改用 yt-dlp，第 {d_time} 次下载 av{aid} 视频...")
            # yt_opt = {"outtmpl": f"./video/{aid}.%(ext)s"}
            # try:
            #     with yt_dlp.YoutubeDL(yt_opt) as ydl:
            #         ydl.download([f"https://www.bilibili.com/video/av{aid}"])
            # except:
            #     pass
    if d_time != 0 and skipConvert == False:
        any_to_avc(f"./video/{aid}.mp4")
    logging.info(f"av{aid} 视频下载完成")
    return f"./video/{aid}.mp4"


# 弹幕下载
def get_danmaku(cid, aid=None):
    from config import api_header

    if(os.path.exists(f"./danmaku/{cid}.xml")):
        logging.info(f"av{aid} 弹幕已存在，直接返回")
        return f"./danmaku/{cid}.xml"

    danmaku_content = requests.get(
        f"https://comment.bilibili.com/{cid}.xml", headers=api_header
    )
    try_times = 0
    while danmaku_content.status_code != 200 and try_times <= 10:
        try_times += 1
        danmaku_content = requests.get(
            f"https://comment.bilibili.com/{cid}.xml", headers=api_header
        )
    if danmaku_content.status_code != 200:
        logging.warning(f"av{aid} 弹幕获取失败")
        return ""
    else:
        danmaku_content = danmaku_content.content
    with open(f"./danmaku/{cid}.xml", "wb") as danmaku:
        danmaku.write(danmaku_content)
    logging.info(f"av{aid} 弹幕获取完成")
    return f"./danmaku/{cid}.xml"


# 编码以及码率转换
def any_to_avc(file):
    from config import smooth_bit_rate, smooth_render_format

    info = ffmpeg.probe(file)["streams"][0]
    format = info["codec_name"]
    bit_rate = info["bit_rate"]
    if (format not in ["h264", "avc"]) or (int(bit_rate) > smooth_bit_rate):
        ori_name = file.split("/")
        ori_name[-1] = "ori_" + ori_name[-1]
        rename = "/".join(ori_name)
        os.rename(file, rename)
        video = ffmpeg.input(rename)
        ffmpeg.output(video, file, **smooth_render_format).run()


# CSV 表格转换
def convert_csv(file):
    outlist = []
    with open(file, "r", encoding="utf-8-sig") as datafile:
        lists = csv.DictReader(datafile)
        for sti in lists:
            outlist.append(sti)
    return outlist


def extract_single_column(post_list, target, end_num):
    extractArr = []
    ignum = 0
    for ig in post_list:
        ignum += 1
        if ignum > end_num:
            break
        extractArr.append(str(ig[target]))
    return extractArr


# 图像颜色均值
def average_image_color(file):
    dominant = Haishoku.getDominant(file)
    return dominant


def average_image_palette(file):
    palette = Haishoku.getPalette(file)
    return palette


def calc_color(file):
    # dark_mean = 90
    # light_mean = 229
    color_palette = average_image_palette(file)
    outnum = 0
    palette_num = len(color_palette)
    for single_color in color_palette:
        # outnum += 1
        # std = std_judge(single_color[1])
        # if std <= 15: # 计算标准差，以便选取更为鲜艳的颜色
        #     if not (outnum >= palette_num):
        #         if not color_palette[outnum][0] < 0.1:
        #             continue
        # mean = np.mean(single_color[1])
        # if not mean > 0: # 防止纯黑以至分母乘 0
        #     single_color[1] = (1,1,1)
        #     mean = 1
        # light_adjust = light_mean / mean
        # dark_adjust = dark_mean / mean
        # light_color = adjust_brightness(single_color[1],light_adjust)
        # dark_color = adjust_brightness(single_color[1],dark_adjust)
        outnum += 1
        hsl = rgb2hsl(single_color[1])
        if hsl[1] < 0.25:
            if not (outnum >= palette_num):
                if not color_palette[outnum][0] < 0.15:
                    continue
        light_color = f"({hsl[0]},{hsl[1]*100}%,75%)"
        dark_color = f"({hsl[0]},{hsl[1]*100}%,35%)"
        return [light_color, dark_color]


def rgb2hsl(rgb):
    hls = colorsys.rgb_to_hls(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
    hsl = (hls[0] * 360, hls[2], hls[1])
    return hsl


def adjust_brightness(rgb, scale):
    return (rgb[0] * scale, rgb[1] * scale, rgb[2] * scale)


def std_judge(rgb):
    std = np.std(rgb)
    return std


def check_dir():
    """
    检查文件夹是否齐全，否则就新建
    """
    dirpaths = [
        "avatar",
        "cover",
        "cover/calendar",
        "data",
        "data/backup",
        "config",
        "fast_view",
        "log",
        "option",
        "option/calendar",
        "output",
        "output/clip",
        "output/final",
        "video",
        "videoc",
        "audio",
        "cookies",
        "temp",
        "option/ads",
        "danmaku",
        "driver",
    ]
    for dirpath in dirpaths:
        if not os.path.exists(dirpath):
            logging.warning(f"文件夹不齐全，新建了 {dirpath} 文件夹")
            os.mkdir(dirpath)
    if not os.path.exists("./option/blacklist.csv"):
        # 预先黑名单
        with open(
            "option/blacklist.csv", "w", encoding="utf-8-sig", newline=""
        ) as blackfile:
            header = ["aid", "title"]
            blackInfo = csv.DictWriter(blackfile, header)
            blackInfo.writeheader()
    if not os.path.exists("./option/adjust.csv"):
        # 预先内容系数调整
        with open(
            "option/adjust.csv", "w", encoding="utf-8-sig", newline=""
        ) as adjustfile:
            header = ["name", "uid", "adjust_scale"]
            adjustInfo = csv.DictWriter(adjustfile, header)
            adjustInfo.writeheader()
    if not os.path.exists("./option/calendar.csv"):
        # 日历
        with open(
            "option/calendar.csv", "w", encoding="utf-8-sig", newline=""
        ) as adjustfile:
            header = ["color", "progress", "date", "title", "subtitle", "cover"]
            adjustInfo = csv.DictWriter(adjustfile, header)
            adjustInfo.writeheader()
    if not os.path.exists("./option/append.csv"):
        # 追加内容
        with open(
            "option/append.csv", "w", encoding="utf-8-sig", newline=""
        ) as file:
            pass


def check_env():
    assert os.path.exists(
        "./driver/chromedriver.exe"
    ), "./driver/ 缺失 chromedriver.exe 驱动程序"


def html_unescape(dict):
    """
    将字典里的值全部逃离 HTML 化
    """
    out_dict = {}
    for key, value in dict.items():
        out_dict.update({key: html.unescape(str(value))})
    return out_dict


def audio_process(aid, start_time=0, duration=10000, audio=None):
    """
    音频处理
    """
    if audio != None:
        sound = pydub.AudioSegment.from_file(audio)
        sound = sound[int(start_time) : int(start_time + duration)]  # 切片
    else:
        sound = pydub.AudioSegment.from_file(f"./video/{aid}.mp4")
        sound = sound[int(start_time) : int(start_time + duration)]  # 切片
    silent_time = 500
    silent = pydub.AudioSegment.silent(duration=silent_time)

    sound = sound.apply_gain(-sound.max_dBFS)  # 响度标准化

    ## 已经弃用的功能

    # 判断分组极差，判断压缩
    # chunks = pydub.utils.make_chunks(sound[int(duration/4):int(duration*3/4)],100) # 排除首末可能存在的判断失误
    # clup = int((duration/4 - duration*3/4) // 100)
    # dBFS_array = []
    # for i, chunk in enumerate(chunks):
    #     dBFS_array.append(chunk.max_dBFS)
    # dBFS_aver = np.average(dBFS_array)
    # if(abs(np.max(dBFS_array) - dBFS_aver) > 2.5 and np.std(dBFS_array) / clup < 0.04): # 若偏差大于 2.5 且单组标准差小于 0.04，则压缩
    #     sound = sound.apply_gain(-dBFS_aver)
    #     sound = pydub.effects.compress_dynamic_range(sound,threshold=0,ratio=4.0, attack=5.0, release=50.0)

    sound = silent.append(sound, crossfade=silent_time)
    sound = sound.append(silent, crossfade=silent_time)  # 交叉淡入
    sound.export(f"./audio/{aid}.mp3", format="mp3", bitrate="320k")
    return f"./audio/{aid}.mp3"

@dataclass
class VideoChunk:
    start_time: float # 相对于原视频的起始时间
    render_start_time: float # 实际渲染起始时间
    front_reserved_time: float # 前置保留时间
    back_reserved_time: float # 后置保留时间
    duration: float
    filepath: str

def video_cut(aid, start_time=0, duration=10) -> list[VideoChunk]:
    """
    裁剪视频并规格化尺寸。
    """
    from config import screenRatio, vcodec, slip_second

    videoSourceSize = ffmpeg.probe(f"./video/{aid}.mp4")["streams"][0]
    videoRatio = videoSourceSize["width"] / videoSourceSize["height"]
    logging.info(f"视频原始尺寸: {videoSourceSize['width']}x{videoSourceSize['height']}，比例: {videoRatio:.2f}，目标比例: {screenRatio:.2f}")
    # 因为时长有波动，必须使用原生 ffmpeg。
    if videoRatio >= screenRatio:
        should_height = videoSourceSize["width"] / screenRatio
        padding = (should_height - videoSourceSize["height"]) / 2
        scale_src = f"pad={videoSourceSize['width']}:{should_height}:0:{padding}:black"
    else:
        should_width = videoSourceSize["height"] * screenRatio
        padding = (should_width - videoSourceSize["width"]) / 2
        scale_src = f"pad={should_width}:{videoSourceSize['height']}:{padding}:0:black"
    
    cut_result = []

    render_start_time = 0
    for new_start_time in range(int(start_time), int(start_time + duration), slip_second):
        front_reserved = 0 # 预留前几秒，防止切割点出现黑屏等问题
        back_reserved = 0 # 预留后几秒，防止切割点出现黑屏等问题

        video_dst = f"./videoc/{aid}_{new_start_time}.mp4"
        if new_start_time + slip_second >= start_time + duration:
            actual_duration = (start_time + duration) - new_start_time
            # 此时也表明是最后一段切割
        else:
            actual_duration = slip_second
            back_reserved = 1

        actual_start_time = new_start_time

        if(new_start_time != start_time):
            front_reserved = 1
            actual_start_time -= front_reserved

        avaliable_duration = actual_duration
        actual_duration += front_reserved + back_reserved

        command = [
            "ffmpeg", "-i",
            f"./video/{aid}.mp4",
            "-ss", str(actual_start_time),
            "-t", str(actual_duration),
            "-vf", scale_src,
            "-c:v", vcodec,
            "-c:a", "aac",
            "-ar", "44100",
            video_dst,
        ]

        if os.path.exists(video_dst):
            os.remove(video_dst) # 必须重新生成，防止出错

        logging.info(f"正在裁剪 av{aid} 视频片段，总时长 {duration} : 应于 {new_start_time} 秒开始，提前 {front_reserved} 秒，后放 {back_reserved} 秒, 时长 {actual_duration} 秒...")

        process = subprocess.Popen(
            command,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8-sig",
        )

        for info in iter(process.stderr.readline, "b"):
            if process.poll() is not None:
                break
            if len(info) != 0:
                logging.info(info.replace("\n", ""))

        cut_result.append(
            VideoChunk(
                start_time=new_start_time,
                duration=avaliable_duration,
                render_start_time=render_start_time,
                front_reserved_time=front_reserved,
                back_reserved_time=back_reserved,
                filepath=video_dst
            )
        )

        render_start_time += avaliable_duration

    return cut_result

def video_merge(chunks: list[VideoChunk], audio_src: str, output_src: str):
    """
    合并视频片段
    """
    from config import vcodec

    hash = hashlib.md5(str(chunks).encode()).hexdigest()
    # 将合并列表写入临时文件
    with open(f"./temp/merge_list_{hash}.txt", "w", encoding="utf-8") as merge_file:
        for chunk in chunks:
            # 写入绝对路径以防 ffmpeg 报错
            merge_file.write(f"file '{os.path.abspath(chunk.filepath)}'\n")
    
    command = [
        "ffmpeg", "-f", "concat", "-safe", "0", "-i",
        f"./temp/merge_list_{hash}.txt",
        "-i", audio_src,
        "-c:v", "copy",
        "-c:a", "copy",
        output_src,
    ]

    logging.info(f"正在合并视频片段...")

    process = subprocess.Popen(
        command,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8-sig",
    )

    for info in iter(process.stderr.readline, "b"):
        if process.poll() is not None:
            break
        if len(info) != 0:
            logging.info(info.replace("\n", ""))


def intilize_dict(given_dict: dict) -> dict:
    """
    将字典中可转化整形的字符串全部转为整形
    """

    def _loop_convert(item: dict):
        for key, value in item.items():
            if isinstance(value, dict):
                value = _loop_convert(value)
            if isinstance(value, list):
                value = _loop_convert_list(value)
            if isinstance(value, str):
                if value.isdigit():
                    value = int(value)
            item.update({key: value})
        return item

    def _loop_convert_list(item: list):
        new_item = []
        for value in item:
            if isinstance(value, dict):
                value = _loop_convert(value)
            if isinstance(value, list):
                value = _loop_convert_list(value)
            if isinstance(value, str):
                if value.isdigit():
                    value = int(value)
            new_item.append(value)
        return new_item

    return _loop_convert(given_dict)
