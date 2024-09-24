import logging
import os
import threading
import yaml
import time

from all_create import AllVideo
from program_function import convert_csv, extract_single_column, check_env, check_dir
from render_video_wvc import render_video

import traceback


def main_progress():
    try:
        mainfunc()
    except Exception as e:
        logging.exception(traceback.format_exc())


def mainfunc():
    from config import render_prefix, web_prefix, main_end, side_end, muitl_limit

    # 日志记录
    formatter = logging.Formatter("[%(levelname)s]\t%(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel("DEBUG")
    logger = logging.getLogger()
    logger.addHandler(console_handler)

    # check_env()
    check_dir()

    # 获取数据
    ranked_list = convert_csv("./data/data.csv")
    calendar_list = convert_csv("./option/calendar.csv")

    # 日历合成
    with open("./config/calendar.yaml", "r") as conf_file:
        conf = yaml.safe_load(conf_file)

    if not os.path.exists(f"./output/clip/Calendar.mp4"):
        url = f"{render_prefix}/calendar"
        calendar_data = {
            "aid": "calendar",
            "output_src": f"./output/clip/Calendar.mp4",
            "full_time": conf["full_time"],
            "start_time": conf["start_time"],
            "web_prefix": web_prefix,
            "more_data": calendar_list,
            "url": url,
        }
        render_video(calendar_data, url, fast=True, audio="./option/calendar/bgm.mp3")

    # 主榜列表单独提取
    mainArr = extract_single_column(ranked_list, "aid", main_end)

    # PICK UP 数据
    picked_list = []
    if os.path.exists(f"./data/picked.csv"):
        picked_list = convert_csv(f"./data/picked.csv")

    # 主榜段落合成
    render_times = 0
    rend_q = []
    for viding in ranked_list:
        render_times += 1
        if render_times > main_end:
            break
        if os.path.exists(f"./output/clip/MainRank_{render_times}.mp4"):
            continue

        if render_times == 1:
            url = f"{render_prefix}/main"
            viding.update(
                {
                    "output_src": f"./output/clip/MainRank_1.mp4",
                    "side_duration": int(float(viding["full_time"]) * 0.6),
                    "more_data": ranked_list[main_end : main_end + side_end],
                    "url": url,
                }
            )
            muitl_limit.acquire()
            rend_s = threading.Thread(target=render_video, args=(viding, url))
            rend_s.start()
            rend_q.append(rend_s)
            # render_video(viding,url)
            continue
        # 否则正常渲染。
        url = f"{render_prefix}/main"
        viding.update(
            {"output_src": f"./output/clip/MainRank_{render_times}.mp4", "url": url}
        )
        muitl_limit.acquire()
        rend_s = threading.Thread(target=render_video, args=(viding, url))
        rend_s.start()
        rend_q.append(rend_s)
        # render_video(viding,url)

    # PICK UP 合成
    picks = 0
    for picking in picked_list:
        picks += 1
        url = f"{render_prefix}/pick"
        if os.path.exists(f"./output/clip/PickRank_{picks}.mp4"):
            continue
        picking.update(
            {"output_src": f"./output/clip/PickRank_{picks}.mp4", "url": url}
        )
        muitl_limit.acquire()
        rend_s = threading.Thread(target=render_video, args=(picking, url))
        rend_s.start()
        rend_q.append(rend_s)
        # render_video(picking,url)

    for sq in rend_q:
        sq.join()

    # 总拼接
    AllVideo(main_end, picked_list)

    logging.info("渲染工作全部完成！")


if __name__ == "__main__":
    logging.basicConfig(
        format="[%(levelname)s]\t%(message)s",
        filename="log/" + time.strftime("%Y-%m-%d %H-%M-%S") + ".log",
        level=logging.DEBUG,
    )
    main_progress()
