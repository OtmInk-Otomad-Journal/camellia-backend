import logging
import os
import json
import time
import random
import asyncio
from typing import Dict

from config import (
    base_path,
    pull_video_copyright,
    delta_days,
    range_days,
    video_zones
)
from config import (
    tag_whitelist
)
from config import sleep_inteval, cookie_file_path

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s@%(funcName)s: %(message)s",
    encoding="utf-8",
)

from get_video_info_score_by_search import get_data_by_search
from get_video_info_score_struct import DateYield, Mid
from get_video_info_score_func import (
    get_info_by_time,
    get_credential_from_path
)

import datetime

now_date = datetime.datetime.now()
src_date = now_date + datetime.timedelta(days=-delta_days)
dst_date = src_date + datetime.timedelta(days=+range_days - 1)
# src_date = datetime.datetime.strptime("20090701","%Y%m%d")
# dst_date = datetime.datetime.strptime("20240331","%Y%m%d")
data_yield = DateYield(src_date, dst_date)

data_path = os.path.join(
    base_path, f"{data_yield.src_date_str} - {data_yield.dst_date_str}"
)

stat_dir = os.path.join(data_path, "stat")
info_dir = os.path.join(data_path, "info")
comment_dir = os.path.join(data_path, "comment")
os.makedirs(stat_dir, exist_ok=True)
os.makedirs(info_dir, exist_ok=True)
os.makedirs(comment_dir, exist_ok=True)

####################### 按分区拉取数据 #########################
all_video_info: Dict[int, Dict] = {}
# 更具体化：
# all_video_info: Dict[int, ] = {}
if not isinstance(video_zones, list):
    video_zones = []
for video_zone in video_zones:
    video_info_in_zone: Dict[int, Dict] = {}

    for src_date_str, dst_date_str in data_yield:
        video_info_in_zone_in_time: Dict[int, Dict] = {}

        info_package_file_name = f"info_{video_zone:03}_{src_date_str[:6]}.json"
        info_package_file_path = os.path.join(info_dir, info_package_file_name)
        if os.path.exists(info_package_file_path):
            logging.info(
                f"分区 {video_zone} 在 {src_date_str}~{dst_date_str} 的视频信息有存档，将读取"
            )
            with open(info_package_file_path, "r", encoding="utf-8") as f:
                video_info_in_zone.update(json.load(f))
            continue

        info_page, num_pages = get_info_by_time(
            1,
            video_zone,
            src_date_str,
            dst_date_str,
            copyright=str(pull_video_copyright),
        )
        logging.info(
            f"取得分区 {video_zone} ({src_date_str}~{dst_date_str} 部分) 的第 1 页，共 {num_pages} 页"
        )
        video_info_in_zone_in_time.update({i["id"]: i for i in info_page})
        # 如果页数正向遍历，那么一旦有视频被删除，列表上之后的视频会向前挪动
        # 跨页挪动的视频就会被漏掉，所以反向遍历
        for page_index in range(num_pages, 1, -1):
            time.sleep(sleep_inteval + random.random())
            info_page, _ = get_info_by_time(
                page_index,
                video_zone,
                src_date_str,
                dst_date_str,
                copyright=str(pull_video_copyright),
            )
            video_info_in_zone_in_time.update({i["id"]: i for i in info_page})
            logging.info(f"第 {page_index} 页完成")

        ## 由于 API 的更改，导致无论如何都会有丢失视频的风险。此时只能采用多次获取方式避免遗漏。
        # for collect_num in range(3): # 获取三次。
        #     logging.info(f"第 {collect_num + 1} 次获取数据")
        #     lst_pn = get_info_last_pn(video_zone, src_date_str)
        #     logging.info(f"获取到最末页为 {lst_pn}")
        #     for page_index in range(lst_pn, 1, -1):
        #         time.sleep(sleep_inteval + random.random())
        #         info_page, end_fil = get_info_by_time_fix(
        #             page_index, video_zone, src_date_str, dst_date_str,
        #             copyright=str(pull_video_copyright))
        #         video_info_in_zone_in_time.update({i['aid']:i for i in info_page})
        #         logging.info(f"第 {page_index} 页完成")
        #         if(end_fil):
        #             logging.info(f"已达获取最末日期，停止获取。")
        #             break

        with open(info_package_file_path, "w", encoding="utf-8") as f:
            json.dump(video_info_in_zone_in_time, f, ensure_ascii=False, indent=4)
        video_info_in_zone.update(video_info_in_zone_in_time)
    all_video_info.update(video_info_in_zone)

logging.info(f"按分区收录视频信息获取完成，目前视频总数: {len(all_video_info)}")

###################### 按搜索结果拉取数据 #########################

credential = get_credential_from_path(cookie_file_path)
cookie_raw = open(cookie_file_path, "r", encoding="utf-8").read()

search_result = []

for src_date_str, dst_date_str in data_yield:
    info_package_file_name = f"info_search_{src_date_str[:6]}.json"
    info_package_file_path = os.path.join(info_dir, info_package_file_name)
    if os.path.exists(info_package_file_path):
        logging.info(
            f"搜索结果在 {src_date_str}~{dst_date_str} 的视频信息有存档，将读取"
        )
        with open(info_package_file_path, "r", encoding="utf-8") as f:
            search_result += json.load(f)
        continue
    now_result = asyncio.run(
        get_data_by_search(tag_whitelist, src_date_str, dst_date_str)
    )
    search_result += now_result
    with open(info_package_file_path, "w", encoding="utf-8") as f:
        json.dump(now_result, f, ensure_ascii=False, indent=4)

logging.info(f"按搜索结果收录视频信息获取完成，所获视频总数: {len(search_result)}")

last_num = len(all_video_info)

# 取并集
for search_single in search_result:
    if not search_single["id"] in all_video_info:
        all_video_info.update({search_single["id"]: search_single})

logging.info(
    f"取并集完成，目前视频总数: {len(all_video_info)}，新增了 {len(all_video_info) - last_num} 个视频"
)