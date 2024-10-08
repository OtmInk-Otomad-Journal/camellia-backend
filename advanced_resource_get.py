import csv
import logging
import time
import os
from program_function import (
    get_img,
    convert_csv,
    extract_single_column,
    get_video,
    exactVideoLength,
    calc_color,
    html_unescape,
    get_danmaku,
)
from danmuku_time import danmuku_time

import traceback

from get_video_info_score_func import retrieve_single_video_stat


def advanced_resource_get():
    """
    下载资源，包括主榜的视频下载与 Pick Up 的进一步数据
    """
    try:
        mainfunc()
    except Exception as e:
        logging.exception(traceback.format_exc())


def mainfunc():
    from config import main_end, side_end, usedTime, sep_time, web_prefix, activity_list

    # 获取数据
    ranked_list = convert_csv("./data/data.csv")
    mainArr = extract_single_column(ranked_list, "aid", main_end)

    # 导航导出
    ranks = 0
    for ranked in ranked_list:
        ranks += 1
        if ranks > main_end + side_end:
            break
        with open(
            f"./fast_view/bili_{usedTime}.txt", "a", encoding="utf-8-sig"
        ) as fast:
            if ranks == 1:
                fast.write("主榜\n")
            fast.write(f"{ranked['ranking']}\t{ranked['bvid']}\n")
        with open(
            f"./fast_view/wiki_{usedTime}.txt", "a", encoding="utf-8-sig"
        ) as fast:
            fast.write(
                "{{"
                + f"""OtmRanking/brick
|ranking={ranked["ranking"]}
|title={ranked["title"]}
|score={ranked["score"]}
|aid={ranked["aid"]}"""
                + "\n}}\n"
            )

    # 主榜的视频资源获取
    for item in mainArr:
        get_video(item)

    # Pick Up 的资源获取
    allArr = []
    pickHeader = [
        "aid",
        "bvid",
        "cid",
        "title",
        "reason",
        "uploader",
        "part",
        "copyright",
        "pubtime",
        "picker",
        "activity",
        "start_time",
        "full_time",
        "web_prefix",
        "video_src",
        "cover_src",
        "avatar_src",
        "light_color",
        "dark_color",
    ]

    with open(f"./data/picked.csv", "w", encoding="utf-8-sig", newline="") as csvWrites:
        writer = csv.DictWriter(csvWrites, pickHeader)
        writer.writeheader()

        def getInfo(aid, reason, picker, act):
            pickAllInfo = retrieve_single_video_stat(video_aid=int(aid))
            picked = pickAllInfo[1]
            vid_src = get_video(picked["aid"])
            exact_time = exactVideoLength(vid_src)
            danmaku_src = get_danmaku(picked["cid"], aid=picked["aid"])  # 弹幕获取
            start_time, full_time = danmuku_time(
                picked["aid"], exact_time, sep_time, cid=picked["cid"]
            )
            pic_src = get_img(picked["aid"])
            color_rgb = calc_color(pic_src["cover"])
            oneArr = {
                "aid": picked["aid"],
                "bvid": picked["bvid"],
                "cid": picked["cid"],
                "title": picked["title"],
                "reason": reason,
                "uploader": picked["owner"]["name"],
                "copyright": picked["copyright"],
                "pubtime": time.strftime(
                    "%Y/%m/%d %H:%M:%S", time.localtime(int(picked["pubdate"]))
                ),
                "picker": picker,
                "activity": act,
                "start_time": start_time,
                "full_time": full_time,
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
            logging.info("一个 Pick Up 作品已记录")

        if os.path.exists("./data/pick_filtered.csv"):
            with open(
                "./data/pick_filtered.csv", encoding="utf-8-sig", newline=""
            ) as csvfile:
                pickInfo = csv.DictReader(csvfile)
                for pick in pickInfo:
                    time.sleep(0.5)
                    if (str(pick["aid"]) in mainArr) and (
                        pick["activity"] not in activity_list
                    ):  # 判断主榜是否已经存在 Pick Up 作品，且非活动稿件。
                        continue
                    getInfo(
                        pick["aid"], pick["reason"], pick["picker"], pick["activity"]
                    )
    if len(allArr) == 0:
        os.remove(f"./data/picked.csv")

    # PICK UP 快速导航
    picks = 0
    for pickOne in allArr:
        picks += 1
        with open(
            f"./fast_view/bili_{usedTime}.txt", "a", encoding="utf-8-sig"
        ) as fast:
            if picks == 1:
                fast.write("Pick Up\n")
            fast.write(f"{picks}\t{pickOne['bvid']}\n")
        with open(
            f"./fast_view/wiki_{usedTime}.txt", "a", encoding="utf-8-sig"
        ) as fast:
            fast.write(
                "{{"
                + f"""OtmRanking/brick
|ranking={picks}
|title={pickOne['title']}
|score=PICK UP
|aid={pickOne['aid']}"""
                + "\n}}\n"
            )
    logging.info("--------------------")
    logging.info("资源获取进程已全部完成！")


if __name__ == "__main__":
    advanced_resource_get()
