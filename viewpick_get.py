import csv
import logging
import threading
from program_function import (
    get_img,
    convert_csv,
    extract_single_column,
    get_video,
    exactVideoLength,
    calc_color,
    html_unescape,
    get_danmaku,
    convert_csv,
)
from danmuku_time import danmuku_time

from get_video_info_score_func import retrieve_single_video_stat

# 声明变量
from config import *

allArr = []
pickHeader = [
    "score",
    "golden",
    "normal",
    "aid",
    "bvid",
    "title",
    "uploader",
    "part",
    "copyright",
    "pubtime",
    "start_time",
    "full_time",
    "duration",
    "web_prefix",
    "video_src",
    "cover_src",
    "avatar_src",
    "light_color",
    "dark_color",
]

with open(f"./data/viewpicked.csv", "w", encoding="utf-8-sig", newline="") as csvWrites:
    writer = csv.DictWriter(csvWrites, pickHeader)
    writer.writeheader()

    def getInfo(aid, score, golden, normal):
        try:
            pickAllInfo = retrieve_single_video_stat(video_aid=int(aid))
        except:
            logging.error(f"获取观众选视频 {aid} 信息失败，跳过")
            pickAllInfo = [None, {
                "aid": aid,
                "bvid": "",
                "cid": 0,
                "title": "信息获取失败",
                "owner": {"name": ""},
                "copyright": "",
                "pubdate": time.time(),
                "start_time": 0,
                "full_time": 0,
                "duration": 0,
            }]
        picked = pickAllInfo[1]
        try:
            vid_src = get_video(picked["aid"])
        except:
            vid_src = "error"
        danmaku_src = get_danmaku(picked["cid"], aid=picked["aid"])  # 弹幕获取
        try:
            exact_time = exactVideoLength(vid_src)
        except:
            exact_time = picked["duration"]
        start_time, full_time = danmuku_time(
            picked["aid"], exact_time, sep_time, cid=picked["cid"]
        )
        try:
            pic_src = get_img(picked["aid"])
        except:
            pic_src = {"cover": "", "avatar": ""}
        try:
            color_rgb = calc_color(pic_src["cover"])
        except:
            color_rgb = [(255, 255, 255), (0, 0, 0)]
        oneArr = {
            "score": score,
            "golden": golden,
            "normal": normal,
            "aid": picked["aid"],
            "bvid": picked["bvid"],
            "title": picked["title"],
            "uploader": picked["owner"]["name"],
            "copyright": picked["copyright"],
            "pubtime": time.strftime(
                "%Y/%m/%d %H:%M:%S", time.localtime(int(picked["pubdate"]))
            ),
            "start_time": start_time,
            "full_time": full_time,
            "duration": exact_time,
            "web_prefix": web_prefix,
            "video_src": vid_src,
            "cover_src": pic_src["cover"],
            "avatar_src": pic_src["avatar"],
            "light_color": str(color_rgb[0]),
            "dark_color": str(color_rgb[1]),
        }
        oneArr = html_unescape(oneArr)
        allArr.append(oneArr)
        writer.writerow(oneArr)
        logging.info("一个 观众选 作品已记录")

    def special_info(aid, score, golden, normal, title):
        oneArr = {
            "score": score,
            "golden": golden,
            "normal": normal,
            "aid": aid,
            "bvid": aid,
            "title": title,
            "uploader": "",
            "copyright": "",
            "pubtime": "",
            "start_time": 0,
            "full_time": 0,
            "duration": 0,
            "web_prefix": web_prefix,
            "video_src": "",
            "cover_src": "",
            "avatar_src": "",
            "light_color": "",
            "dark_color": "",
        }
        allArr.append(oneArr)
        writer.writerow(oneArr)
        logging.info("一个 观众选 作品已记录")

    pickInfo = convert_csv("./data/viewpick.csv")
    picks = 0

    # 首先先尝试下载所有视频，同时可下载 5 个
    max_workers = 5  # 同时下载的视频数量
    video_tasks = []  # 存储需要下载视频的任务
    
    # 收集所有需要下载视频的aid
    for pick in pickInfo:
        if pick["special"] != "t":  # 只处理非特殊视频
            aid = str(pick["aid"])
            if aid[0:2] == "av":
                aid = aid[2:]
            video_tasks.append(aid)
    
    # 使用线程池下载视频
    def download_video(aid):
        try:
            get_video(int(aid))
        except Exception as e:
            logging.error(f"下载视频 {aid} 时出错: {e}")
    
    semaphore = threading.Semaphore(max_workers)
    threads = []
    for aid in video_tasks:
        semaphore.acquire()
        thread = threading.Thread(target=lambda a: (download_video(a), semaphore.release()), args=(aid,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


    for pick in pickInfo:
        time.sleep(0.5)
        picks += 1
        aid = str(pick["aid"])
        if aid[0:2] == "av":
            aid = aid[2:]
        if pick["special"] == "t":
            special_info(aid, pick["score"],pick["golden"],pick["normal"], pick["title"])
        else:
            getInfo(aid, pick["score"], pick["golden"], pick["normal"])
        logging.info(f"进度 {picks} / {len(pickInfo)}")

# PICK UP 快速导航
picks = 0
for pickOne in allArr:
    picks += 1
    with open(
        f"./fast_view/bili_view_{usedTime}.txt", "a", encoding="utf-8-sig"
    ) as fast:
        if picks == 1:
            fast.write("结果\n")
        fast.write(f"{picks}\t{pickOne['bvid']}\n")
