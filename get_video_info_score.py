import asyncio
import json
import os
import marshal
import datetime
import logging
import time
import random
import shutil
from collections import defaultdict
from typing import List, Tuple, Dict, Set

from config import (
    base_path,
    weight_path,
    weight_new_comp,
    pull_video_copyright,
    video_zones,
    delta_days,
    range_days,
    recursive_times,
)
from config import (
    tag_whitelist,
    tag_whitezone,
    prefilter_comment_less_than,
    main_end,
    side_end,
)
from config import pull_full_list_stat, sleep_inteval, cookie_file_path

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s@%(funcName)s: %(message)s",
    encoding="utf-8",
)

from get_video_info_score_by_search import get_data_by_search
from get_video_info_score_func import (
    calc_median,
    get_info_by_time,
    get_credential_from_path,
    lower_tags,
    retrieve_video_comment,
    calc_aid_score,
    retrieve_video_stat,
    print_aid_info,
    get_info_last_pn,
    get_info_by_time_fix,
    get_all_tags,
)
from get_video_info_score_struct import DateYield, Mid

# 其实这些关键词的影响并不大
target_good_keyword = [
    "fuxi",
    "复习",
    "複習",
    "fx",
    "高技术",
    "好听",
    "好汀",
    "好聽",
    "喜欢",
    "喜歡",
    "支持",
    "漂亮",
    "舒服",
    "死了",
    "厉害",
    "厲害",
    "最好",
    "最高",
    "最佳",
    "订餐",
    "sk",
    "suki",
    "suang",
    "爽",
    "不错",
    "不錯",
    "牛逼",
    "牛批",
    "nb",
    "！！！",
    "神",
    "帅",
    "帥",
    "触",
    "觸",
    "强",
    "強",
    "棒",
    "天才",
    "tql",
    "wsl",
    "yyds",
    "小号",
    "震撼",
    "すき",
    "可爱",
    "上瘾",
    "上头",
    "洗脑",
    "草",
    "我浪",
    "顶",
]
target_bad_keyword = [
    "加油",
    "注意",
    "建议",
    "进步",
    "稚嫩",
    "不足",
    "不好",
    "文艺复兴",
    "倒退",
    "大势所趋",
    "dssq",
    "烂",
]


if not os.path.exists(base_path):
    os.makedirs(base_path)
now_date = datetime.datetime.now()
src_date = now_date + datetime.timedelta(days=-delta_days)
dst_date = src_date + datetime.timedelta(days=+range_days - 1)
# src_date = datetime.datetime.strptime("20090701","%Y%m%d")
# dst_date = datetime.datetime.strptime("20240331","%Y%m%d")
data_yield = DateYield(src_date, dst_date)
logging.info(
    f"选取时间 从 {data_yield.src_date_str}-00:00 到 {data_yield.dst_date_str}-23:59"
)
data_path = os.path.join(
    base_path, f"{data_yield.src_date_str} - {data_yield.dst_date_str}"
)
stat_dir = os.path.join(data_path, "stat")
info_dir = os.path.join(data_path, "info")
comment_dir = os.path.join(data_path, "comment")
os.makedirs(stat_dir, exist_ok=True)
os.makedirs(info_dir, exist_ok=True)
os.makedirs(comment_dir, exist_ok=True)

target_good_keyword_first: Set[str] = set([kw[0] for kw in target_good_keyword])
target_bad_keyword_first: Set[str] = set([kw[0] for kw in target_bad_keyword])
target_good_keyword_first_map: Dict[str, List[str]] = defaultdict(list)
target_bad_keyword_first_map: Dict[str, List[str]] = defaultdict(list)
for kw in target_good_keyword:
    target_good_keyword_first_map[kw[0]].append(kw)
for kw in target_bad_keyword:
    target_bad_keyword_first_map[kw[0]].append(kw)

####################### 按分区拉取数据 #########################
all_video_info: Dict[int, Dict] = {}
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

###################################################################

# 评论和tag检测的顺序对调了下。
# 目前对调了回来。

whitelist_filter = lambda video_info: (video_info["tid"] in tag_whitezone) or (
    len(set(video_info["tag"]).intersection(tag_whitelist)) > 0
)
all_video_info = {int(k): v for k, v in all_video_info.items() if whitelist_filter(v)}
logging.info("按白名单过滤后，待拉取视频数: " + str(len(all_video_info)))

comment_count_filter = lambda video_info: (
    video_info["review"] >= prefilter_comment_less_than
)
all_video_info = {k: v for k, v in all_video_info.items() if comment_count_filter(v)}
logging.info("按评论数过滤后，待拉取视频数: " + str(len(all_video_info)))

# all_video_info = get_all_tags(all_video_info)

## 追加视频
import csv

with open("./option/append.csv", encoding="utf-8-sig", newline="") as f:
    reader = csv.reader(f)
    aids = []
    for row in reader:
        for sig in row:
            aids.append(int(sig))
    _, _, datas = retrieve_video_stat(
        data_path, aids, sleep_inteval=sleep_inteval, cookie_raw=cookie_raw
    )
    for key, item in datas.items():
        datas[key].update(
            {
                "id": key,
                "review": datas[key]["reply"],
                "pubdate": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(datas[key]["pubdate"])
                ),
                "mid": datas[key]["owner"]["mid"],
                "favorites": datas[key]["favorite"],
                "author": datas[key]["owner"]["name"],
                "play": datas[key]["view"],
                "tag": ["音MAD"]
            }
        )
        logging.info(f"手动追加了 {key}")
    all_video_info.update(datas)

skipped_aid, invalid_aid = retrieve_video_comment(
    data_path,
    all_video_info,
    credential=credential,
    force_update=False,
    sleep_inteval=sleep_inteval,
)
if len(skipped_aid) > 0:
    logging.warning("被跳过的 aid: " + str(skipped_aid))
if len(invalid_aid) > 0:
    logging.info("无效的 aid: " + str(invalid_aid))
    marshal.dump(invalid_aid, open(os.path.join(data_path, "invalid_aid.pkl"), "wb"))

####################### 计算得分 #########################
logging.info("汇总评论中")
mid_dump_path_built = os.path.join(
    weight_path, "mid_list.dat"
)  # 构建出来的、会更新的权重
mid_dump_path_basic = os.path.join(weight_path, "mid_list_base.dat")  # 底本
mid_dump_path_bakup = os.path.join(weight_path, "mid_list.bak.dat")  # 备份
mid_dump_path_obsol = os.path.join(weight_path, "mid_list_obs.dat")  # 旧权重

if os.path.exists(mid_dump_path_built):
    all_mid_list: Dict[int, Mid] = Mid.deserialize_mid(mid_dump_path_built)
elif os.path.exists(mid_dump_path_basic):
    all_mid_list: Dict[int, Mid] = Mid.deserialize_mid(mid_dump_path_basic)
else:
    logging.error("权重文件缺失，将退出")
    exit()
weight_new_comp = max(min(weight_new_comp, 1.0), 0.0)
if weight_new_comp < 1.0:
    logging.info(f"新权重比例为 {weight_new_comp}，将读取旧权重并混合")
    all_mid_list_old: Dict[int, Mid] = Mid.deserialize_mid_oldstyle(mid_dump_path_obsol)
    all_mid_list = {
        k: v.mix_weight(all_mid_list_old.get(k, None), weight_new_comp)
        for k, v in all_mid_list.items()
    }
mid_s2_list = [mid_info.s2 for mid_info in all_mid_list.values()]
all_mid_s2_median = calc_median(mid_s2_list)
# for mid in sorted(all_mid_list.values(), key=lambda x: -x.s1):
#     if mid.s1>10: print("s1 = %7.2f, s2 = %4.2f, mid=%10i, name = %s" % (mid.s1, mid.s1, mid.mid, mid.name,))

aid_to_comment: Dict[int, List[Dict]] = defaultdict(list)
to_be_update_aid: List[int] = []  # 需要更新权重的 aid
s2_unit = 0.0003183094617716277  # math.atan(0.002) / (math.pi*2)
for aid, video_info in all_video_info.items():
    comment_file_path = os.path.join(
        comment_dir, video_info["pubdate"][:10], f"{aid}.json"
    )
    if not (os.path.exists(comment_file_path) or aid in invalid_aid):
        logging.warning(f"comment file {comment_file_path} not found")
        _, invalid_aid = retrieve_video_comment(
            data_path,
            all_video_info,
            credential=credential,
            force_update=False,
            sleep_inteval=sleep_inteval,
        )
        if not os.path.exists(comment_file_path) or aid in invalid_aid:
            continue
    if aid not in invalid_aid:
        with open(comment_file_path, "r", encoding="utf-8") as f:
            aid_to_comment[aid] = json.load(f)

    # 更新各 mid 的 s2 权重
    if (video_mid := video_info["mid"]) not in all_mid_list:
        all_mid_list[video_mid] = Mid(video_mid)
    if aid not in all_mid_list[video_mid].video_aids:
        all_mid_list[video_mid].add_video_aid(aid)
        to_be_update_aid.append(aid)
        for comment in aid_to_comment.get(aid, []):
            if (comment_mid := comment["mid"]) not in all_mid_list:
                all_mid_list[comment_mid] = Mid(comment_mid)
            all_mid_list[comment["mid"]].s2 += s2_unit

logging.info("计算视频得分")

# aid_to_score: Dict[int, float] = {}
aid_to_score_norm: Dict[int, float] = {}
for index in range(recursive_times):
    logging.info(f"更新 uid 权重中，第 {index+1}/{recursive_times} 次迭代")
    for video_aid, video_info in all_video_info.items():
        _, video_score_norm = calc_aid_score(
            video_info,
            aid_to_comment.get(video_aid, []),
            target_good_keyword_first,
            target_bad_keyword_first,
            target_good_keyword_first_map,
            target_bad_keyword_first_map,
            all_mid_list,
            s2_base=all_mid_s2_median,
        )
        aid_to_score_norm[video_aid] = video_score_norm
    if index == recursive_times - 1:
        break

    for mid in all_mid_list:
        mid_info = all_mid_list[mid]
        mid_score = sum(
            [
                aid_to_score_norm.get(aid, 0)
                for aid in mid_info.video_aids
                if aid in to_be_update_aid
            ]
        )
        mid_info.s1_bias = mid_score
logging.info("计分完成")

###################################
### 将总榜拆分成多个榜单
all_rank_datas = {
    "ytpmv": [],
    "common": []
}

for video_aid, video_info in all_video_info.items():
    if("ytpmv" in lower_tags(video_info["tag"])):
        all_rank_datas["ytpmv"].append(video_aid)
    else:
        all_rank_datas["common"].append(video_aid)
###################################

aid_and_score: List[Tuple[int, float]] = [(k, v) for k, v in aid_to_score_norm.items()]

all_aid_and_scores = {
    "ytpmv": [],
    "common": []
}

for rank_type, aids in all_rank_datas.items():
    for k, v in aid_to_score_norm.items():
        if k in aids:
            all_aid_and_scores[rank_type].append((k,v))

for rank_type, single_aid_and_score in all_aid_and_scores.items():
    all_aid_and_scores[rank_type].sort(key=lambda x: -x[1])

aid_and_score.sort(key=lambda x: -x[1])
if __name__ == "__main__":
    for aid, aid_score in aid_and_score[: main_end + side_end]:
        print_aid_info(
            all_video_info[aid],
            aid_to_comment.get(aid, []),
            target_good_keyword_first,
            target_bad_keyword_first,
            target_good_keyword_first_map,
            target_bad_keyword_first_map,
            all_mid_list,
        )

pull_size = pull_full_list_stat if pull_full_list_stat > 0 else len(aid_and_score)

logging.info(f"将获取各排行前 {pull_size} 条视频的信息")
selected_aid = []
for rank_type, single_aid_and_score in all_aid_and_scores.items():
    selected_aid += [aid for aid, _ in single_aid_and_score[:pull_size]]
_, _, selected_video_stat = retrieve_video_stat(
    data_path, selected_aid, sleep_inteval=sleep_inteval, cookie_raw=cookie_raw
)

# if os.path.exists(mid_dump_path_bak): os.remove(mid_dump_path_bak)
if os.path.exists(mid_dump_path_built):
    shutil.copy2(mid_dump_path_built, mid_dump_path_bakup)
Mid.serialize_mid(all_mid_list, mid_dump_path_built)

logging.info(f"数据部分完成")


"""
* 各项意义见下 URL，实际稍有差别:
* https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/search/search_response.md
>>> print(all_video_info[615690406])
{
日期'pubdate': '2023-07-09 16:14:23',
封面'pic': '//i0.hdslb.com/bfs/archive/9af57aef1930c8808fc9440e960ada109a0a7a96.jpg',
    'tag': ['原曲不使用','迈克尔·杰克逊','ytpmv','michael\xa0jackson','ditizo','蚊的音mad征集令'],
时长'duration': 97,
av号'id': 615690406,
    'rank_score': 7189, # B 站自己展示用的排名，和我们的排名无关
    'senddate': 1688890463,
作者'author': '坏枪',
评论'review': 109,
UID 'mid': 6636705,
    'is_union_video': 0,
    'rank_index': 10,
播放'play': '7189',
    'rank_offset': 10,
简介'description': '嗷！\n\nBGM：Ditizo (Original) - The Guy Who Made（BV17r4y1n7wK）\n\n本作品参与了蚊的音MAD征集令 - 自由赛道',
弹幕'video_review': 9,
收藏'favorites': 431,
    'arcurl': 'http://www.bilibili.com/video/av615690406',
bv号'bvid': 'BV1Wh4y1E7RU',
标题'title': 'Ditizo!',
    'vt': 0,
    'enable_vt': 0
分区'tid': 26
    'get_time': 1689543449}

>>> print(selected_video_stat[615690406])
{   'aid': 615690406,
    'bvid': 'BV1Wh4y1E7RU',
    'view': 7419,
    'danmaku': 9,
    'reply': 109,
    'favorite': 437,
    'coin': 371,
    'share': 47,
    'like': 1190,
    'now_rank': 0,
    'his_rank': 0,
    'no_reprint': 1,
    'copyright': 1, 
    'argue_msg': '',
    'evaluation': '',
    'vt': None}

>>> print(aid_to_score_norm[315555174])
4.305885
"""
