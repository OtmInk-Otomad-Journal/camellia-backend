import csv
import logging
from program_function import get_img , convert_csv , extract_single_column , get_video , exactVideoLength , calc_color , html_unescape , get_danmaku
from danmuku_time import danmuku_time

from get_video_info_score_func import retrieve_single_video_stat
# 声明变量
from config import *

allArr = []
pickHeader = ["score","aid","bvid",
              "title","uploader",
              "part","copyright",
              "pubtime",
              'start_time','full_time','duration',
              'web_prefix','video_src','cover_src','avatar_src',
              'light_color', 'dark_color']

with open(f"./data/viewpicked.csv",'w',encoding="utf-8-sig", newline='') as csvWrites:
    writer = csv.DictWriter(csvWrites,pickHeader)
    writer.writeheader()

    def getInfo(aid,score):
        pickAllInfo = retrieve_single_video_stat(video_aid=int(aid))
        picked = pickAllInfo[1]
        vid_src = get_video(picked["aid"])
        danmaku_src = get_danmaku(picked["cid"],aid=picked["aid"]) # 弹幕获取
        exact_time = exactVideoLength(vid_src)
        start_time , full_time = danmuku_time(picked["aid"],exact_time,sep_time,cid=picked["cid"])
        pic_src = get_img(picked["aid"])
        color_rgb = calc_color(pic_src["cover"])
        oneArr = {
                "score": score,
                "aid": picked["aid"],
                "bvid": picked["bvid"],
                "title": picked["title"],
                "uploader": picked["owner"]["name"],
                "copyright": picked["copyright"],
                "pubtime": time.strftime("%Y/%m/%d %H:%M:%S",time.localtime(int(picked["pubdate"]))),
                'start_time': start_time,
                'full_time': full_time,
                'duration': exact_time,
                'web_prefix': web_prefix,
                'video_src': vid_src,
                'cover_src': pic_src["cover"],
                'avatar_src': pic_src["avatar"],
                'light_color': str(color_rgb[0]),
                'dark_color': str(color_rgb[1]),
                }
        oneArr = html_unescape(oneArr)
        allArr.append(oneArr)
        writer.writerow(oneArr)
        logging.info("一个 观众选 作品已记录")

    with open("./data/viewpick.csv",encoding="utf-8-sig",newline='') as csvfile:
        pickInfo = csv.DictReader(csvfile)
        picks = 0
        for pick in pickInfo:
            time.sleep(0.5)
            picks += 1
            getInfo(pick["aid"],pick["score"])
            logging.info(f"进度 / {len(allArr)}")

# PICK UP 快速导航
picks = 0
for pickOne in allArr:
    picks += 1
    with open(f"./fast_view/bili_view_{usedTime}.txt","a",encoding="utf-8-sig") as fast:
        if picks == 1:
            fast.write("结果\n")
        fast.write(f"{picks}\t{pickOne['bvid']}\n")