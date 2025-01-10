import json
import time
import os
import random
import marshal
import datetime
import logging
import math
import requests
from typing import List, Tuple, Dict, Optional, Set, Callable, Optional, Any
from functools import partial
from collections import defaultdict

logging.basicConfig(
    level=logging.DEBUG, format="[%(asctime)s] %(levelname)s@%(funcName)s: %(message)s"
)
ignored_debug_lib = ["requests", "urllib3", "asyncio", "httpx", "httpcore"]
for lib in ignored_debug_lib:
    logging.getLogger(lib).setLevel(logging.WARNING)
from tqdm import tqdm

# pip install bilibili_api_python
from bilibili_api import comment, sync, video
from bilibili_api import Credential
from bilibili_api.exceptions import ResponseCodeException
from bilibili_api.exceptions.NetworkException import NetworkException
from aiohttp.client_exceptions import ServerDisconnectedError, ClientOSError
from httpx import ConnectTimeout, RemoteProtocolError, ReadTimeout

from get_video_info_score_struct import Mid


def calc_median(data: List[float]) -> float:
    data_ = sorted(data)
    half = len(data) // 2
    return (data_[half] + data_[~half]) / 2


def get_page_count(video_zone: int) -> int:
    headers = {
        "Accept": "*/*",
        # 'Cookie': raw_cookie,
        "Referer": "https://www.bilibili.com/v/kichiku/mad/",
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/61.0.3163.79 Safari/537.36 Maxthon/5.0",
    }
    # ↓只在子分区有效，比如音 MAD 区
    url = f"http://api.bilibili.com/x/web-interface/newlist?rid={video_zone}&type=0&pn=1&ps=1"
    response = requests.get(url, headers=headers)
    response.encoding = "utf-8"
    result = json.loads(response.text)
    if result["code"] == 0:
        return result["data"]["page"]["count"]
    return -1


## 介于 B 站获取视频列表的 API 不稳定，这是补救获取措施。
## 获取最末 pn 值。
def get_info_last_pn(video_zone: int, time_from: str, ps=50, sleep_inteval=0.1):
    headers = {
        "accept": "*/*",
        # 'Cookie': raw_cookie, # using cookie may lessen the prob that being blocked
        "referer": "https://www.bilibili.com/v/kichiku/mad/",  # 我不知道在请求其他分区时，填上不正确的 referer 会有什么影响
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.124 Safari/537.36 Edg/102.0.1245.41",
    }

    time_from_stamp = int(datetime.datetime.strptime(time_from, "%Y%m%d").timestamp())

    # 二分法
    st_num = 1
    while True:
        time.sleep(sleep_inteval)
        page_index = st_num
        url = f"https://api.bilibili.com/x/web-interface/newlist?rid={video_zone}&pn={page_index}&ps={ps}"
        _, data = apply_response_getter(url, headers)
        video_list: List[Dict[str, Any]] = data["archives"]
        if not video_list:
            return 0
        if video_list[-1]["pubdate"] > time_from_stamp:
            st_num += 10
        else:
            break
    ed_num = st_num
    st_num = 0
    gap = ed_num - st_num
    while gap > 1:
        time.sleep(sleep_inteval)
        page_index = int(st_num + gap / 2)
        url = f"https://api.bilibili.com/x/web-interface/newlist?rid={video_zone}&pn={page_index}&ps={ps}"
        _, data = apply_response_getter(url, headers)
        video_list: List[Dict[str, Any]] = data["archives"]
        if not video_list:
            return 0
        if video_list[-1]["pubdate"] > time_from_stamp:
            st_num = page_index
        else:
            ed_num = page_index
        gap = ed_num - st_num
    return ed_num


def get_all_tags(vid_list: Dict):
    pbar = tqdm(total=len(vid_list))
    for _, irt in enumerate(vid_list):
        tags = get_tags(irt)
        vid_list[irt].update({"tag": tags})
        pbar.update(1)
    return vid_list


def get_tags(aid: int, sleep_inteval=0.3):
    headers = {
        "accept": "*/*",
        # 'Cookie': raw_cookie, # using cookie may lessen the prob that being blocked
        "referer": "https://www.bilibili.com/v/kichiku/mad/",  # 我不知道在请求其他分区时，填上不正确的 referer 会有什么影响
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.124 Safari/537.36 Edg/102.0.1245.41",
    }

    url = f"https://api.bilibili.com/x/tag/archive/tags?aid={aid}"
    _, data = apply_response_getter(url, headers)
    time.sleep(sleep_inteval)
    tags = []
    for tag in data:
        tags.append(tag["tag_name"])
    return tags


def get_info_by_time_fix(
    page_index: int,
    video_zone: int,
    time_from: str,
    time_to: str,
    ps=50,
    copyright="-1",
):
    headers = {
        "accept": "*/*",
        # 'Cookie': raw_cookie, # using cookie may lessen the prob that being blocked
        "referer": "https://www.bilibili.com/v/kichiku/mad/",  # 我不知道在请求其他分区时，填上不正确的 referer 会有什么影响
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.124 Safari/537.36 Edg/102.0.1245.41",
    }
    url = f"https://api.bilibili.com/x/web-interface/newlist?rid={video_zone}&pn={page_index}&ps={ps}"

    endrule = False
    time_from_stamp = int(datetime.datetime.strptime(time_from, "%Y%m%d").timestamp())
    time_to_stamp = int(
        (
            datetime.datetime.strptime(time_to, "%Y%m%d") + datetime.timedelta(days=1)
        ).timestamp()
    )

    _, data = apply_response_getter(url, headers)
    video_list: List[Dict[str, Any]] = data["archives"]
    if not video_list:
        return [], 0
    video_list_filter = []
    for i, video in enumerate(video_list):
        if video["pubdate"] > time_to_stamp:
            endrule = True
            continue
        if video["pubdate"] < time_from_stamp:
            continue
        video["get_time"] = int(datetime.datetime.now().timestamp())
        video["tid"] = video_zone
        video["id"] = video["aid"]
        video["review"] = video["stat"]["reply"]
        video["pubdate"] = datetime.datetime.fromtimestamp(video["pubdate"]).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        video["mid"] = video["owner"]["mid"]
        video["author"] = video["owner"]["name"]
        video["favorites"] = video["stat"]["favorite"]
        video["play"] = video["stat"]["view"]
        video_list_filter.append(video)
    return video_list_filter, endrule


def get_info_by_time(
    page_index: int,
    video_zone: int,
    time_from: str,
    time_to: str,
    ps=50,
    copyright="-1",
    sleep_inteval=3.0,
):
    """
    :param time_from: 起始日期, 格式: yyyymmdd, 如: 20230701, 指此日期的 00:00 为始
    :param time_to:   结束日期, 格式: yyyymmdd, 如: 20230701, 指此日期的 23:59 为止
    :param ps:        每页视频数量，太大易被 ban
    :param copyright: "1": 自制, "0": 转载, "-1": 不限制
    """
    headers = {
        "accept": "*/*",
        # 'Cookie': raw_cookie, # using cookie may lessen the prob that being blocked
        "referer": "https://www.bilibili.com/v/kichiku/mad/",  # 我不知道在请求其他分区时，填上不正确的 referer 会有什么影响
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.124 Safari/537.36 Edg/102.0.1245.41",
    }
    url = f"https://api.bilibili.com/x/web-interface/newlist_rank?search_type=video&view_type=hot_rank&cate_id={video_zone}&page={page_index}&pagesize={ps}&time_from={time_from}&time_to={time_to}&copy_right={copyright}"

    # API 不稳定而需要多次尝试。
    api_try_times = 0
    while api_try_times < 10:
        _, data = apply_response_getter(url, headers)
        video_list: List[Dict[str, Any]] = data["result"]
        if not video_list:
            api_try_times += 1
            logging.info(f"{video_zone} 分区的第 {api_try_times} 次重试")
            time.sleep(sleep_inteval)
        else:
            break
    if not video_list:
        return [], 0

    for i, video in enumerate(video_list):
        video.pop("arcrank", None)
        video.pop("is_pay", None)
        video.pop("type", None)
        video.pop("badgepay", None)
        video["get_time"] = int(datetime.datetime.now().timestamp())
        video["tid"] = video_zone
        video["tag"] = video["tag"].lower().split(",")
    num_results: int = data["numResults"]
    num_pages: int = data["numPages"]
    return video_list, num_pages


# comment 具体格式见 https://github.com/SocialSisterYi/bilibili-API-collect/tree/master/docs/comment
def reply_trimmer(comments: List[Dict]) -> List[Dict]:
    processed_comments = []
    for comment in comments:
        processed_comments.append(
            {
                "rpid": comment["rpid"],
                "mid": comment["mid"],
                "uname": comment["member"]["uname"],  # 评论rpID, 发送者UID, 发送者暱稱
                "count": comment["count"],
                "rcount": comment["rcount"],
                "ctime": comment["ctime"],  # 回复条数, 回复条数, 发送时间
                "like": comment["like"],
                "message": comment["content"]["message"],
                "mentioned": [
                    comment_mentioned_uid["mid"]
                    for comment_mentioned_uid in comment["content"]["members"]
                ],
                "up_like": comment["up_action"]["like"],
                "replies": (
                    [
                        {
                            "rpid": replies["rpid"],
                            "mid": replies["mid"],
                            "uname": replies["member"][
                                "uname"
                            ],  # 评论rpID, 发送者UID, 发送者暱稱
                            "count": replies["count"],
                            "rcount": replies["rcount"],
                            "ctime": replies["ctime"],  # 回复条数, 回复条数, 发送时间
                            "like": replies["like"],
                            "message": replies["content"]["message"],
                            "mentioned": [
                                reply_mentioned_uid["mid"]
                                for reply_mentioned_uid in replies["content"]["members"]
                            ],
                            "up_like": replies["up_action"]["like"],
                        }
                        for replies in comment["replies"]
                    ]
                    if comment["replies"] is not None
                    else []
                ),
            }
        )
    return processed_comments


async def lazy_get_comments(aid: int, credential: Credential) -> List[Dict]:
    """
    懒加载获取评论
    """
    comments = []
    next = 0
    while True:
        c = await comment.get_comments(
            aid, comment.CommentResourceType.VIDEO, next, credential=credential
        )
        assert type(c) is dict
        if "replies" not in c or c["replies"] is None:
            break
        comments.extend(c["replies"])
        next = c["cursor"]["next"]
        if c["cursor"]["is_end"]:
            break
        time.sleep(0.25)
    return reply_trimmer(comments)


async def get_comments(aid: int, credential: Credential) -> List[Dict]:
    comments = []
    page = 1
    count = 0
    while True:
        c = await comment.get_comments(
            aid, comment.CommentResourceType.VIDEO, page, credential=credential
        )
        assert type(c) is dict
        if "replies" not in c or c["replies"] is None:
            break
        comments.extend(c["replies"])
        count += len(c["replies"])
        if count >= c["page"]["count"] or page > 100:
            break  # 12.6 发现为100页左右 // 400 页达目前已知最大限制。
        page += 1
        time.sleep(1)
    return reply_trimmer(comments)


def get_credential(cookie_raw: str) -> Tuple[str, ...]:
    from config_login import sessdata, bili_jct, buvid3, dedeuserid

    cookie_split = cookie_raw.replace("; ", ";").split(";")
    cookie_split = [i for i in cookie_split if i]
    cookie = {i.split("=")[0].lower(): i.split("=")[1] for i in cookie_split}
    sessdata = cookie.get("sessdata", sessdata)
    bili_jct = cookie.get("bili_jct", bili_jct)
    buvid3 = cookie.get("buvid3", buvid3)
    dedeuserid = cookie.get("dedeuserid", dedeuserid)
    return sessdata, bili_jct, buvid3, dedeuserid


def get_credential_from_path(cookie_file_path: str) -> Credential:
    from config_login import sessdata, bili_jct, buvid3, dedeuserid

    if os.path.isfile(cookie_file_path):
        cookie_raw = open(cookie_file_path, "r", encoding="utf-8").read()
        sessdata, bili_jct, buvid3, dedeuserid = get_credential(cookie_raw)
    else:
        if cookie_file_path != "":
            print(f"{cookie_file_path} 不存在")

    if not sessdata or not bili_jct or not dedeuserid:
        logging.warning("Cookie 信息不完整")
    else:
        logging.info("成功获取 Cookie")
    return Credential(sessdata=sessdata, bili_jct=bili_jct, buvid3=buvid3)


def retrieve_video_comment(
    data_path: str,
    all_video_info: Dict[int, Dict],
    *,
    credential: Credential,
    force_update=False,
    max_try_times=10,
    sleep_inteval=3.0,
) -> Tuple[Set[int], Set[int]]:
    # from config_login import sessdata, bili_jct, buvid3, dedeuserid
    # credential = Credential(sessdata=sessdata, bili_jct=bili_jct, buvid3=buvid3)
    skipped_aid = set()
    invalid_aid_path = os.path.join(data_path, "invalid_aid.pkl")
    if os.path.exists(invalid_aid_path):
        invalid_aid = marshal.load(open(invalid_aid_path, "rb"))
    else:
        invalid_aid = set()
    comment_dir = os.path.join(data_path, "comment")

    for n, video_info in enumerate(all_video_info.values()):
        video_aid = video_info["id"]
        comments_dir_by_date = os.path.join(comment_dir, video_info["pubdate"][:10])
        comment_file_path = os.path.join(comments_dir_by_date, f"{video_aid}.json")
        if not force_update and os.path.exists(comment_file_path):
            continue
        if video_aid in invalid_aid:
            continue

        status, comments = retrieve_single_video_comment(
            video_aid,
            credential=credential,
            max_try_times=max_try_times,
            sleep_inteval=sleep_inteval,
        )
        if status <= 0:
            if status == -1:
                invalid_aid.add(video_aid)
            if status == -2:
                skipped_aid.add(video_aid)
            time.sleep(sleep_inteval)
            continue

        if not os.path.exists(comments_dir_by_date):
            os.makedirs(comments_dir_by_date)
        with open(comment_file_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(comments, ensure_ascii=False, indent=4))
        if video_info["review"] > 20 * 2 and len(comments) == 20:
            logging.warning(
                f"获取 av{video_aid} 评论数{len(comments): 4} 过少，若此问题多次出现需考虑重新获取 Cookie；进度 {n+1: 4} / {len(all_video_info)}"
            )
        else:
            logging.debug(
                f"获取 av{video_aid} 评论成功，计评论数{len(comments): 4}, 进度 {n+1: 4} / {len(all_video_info)}"
            )

    if len(invalid_aid) > 0:
        marshal.dump(
            invalid_aid, open(os.path.join(data_path, "invalid_aid.pkl"), "wb")
        )
    return skipped_aid, invalid_aid


def retrieve_video_stat(
    data_path: str,
    aid_list: List[int],
    force_update=False,
    max_try_times=10,
    sleep_inteval=3.0,
    cookie_raw: Optional[str] = None,
) -> Tuple[Set[int], Set[int], Dict[int, Dict]]:
    """获取视频的各项数据，如播放量、点赞数、硬币数、弹幕数等
    :param data_path: 数据存储路径，将在该目录下生成 `stat` 子目录
    :param aid_list: av 号列表
    :param force_update: 是否强制更新，是则会重新获取所有视频的信息
    :param max_try_times: 最大尝试次数
    :param sleep_inteval: 间隔时间
    :param cookie_raw: cookie 字符串，针对某些早期「会员领域」视频用

    :return: 跳过的 aid, 无效的 aid, 以 av 号为键的视频数据字典
    """
    skipped_aid = set()
    invalid_aid_path = os.path.join(data_path, "invalid_aid.pkl")
    if os.path.exists(invalid_aid_path):
        invalid_aid = marshal.load(open(invalid_aid_path, "rb"))
    else:
        invalid_aid = set()
    stat_dir = os.path.join(data_path, "stat")

    selected_aid_stats: Dict[int, Dict] = {}
    for n, video_aid in enumerate(aid_list):
        stat_file_path = os.path.join(stat_dir, f"{video_aid}.json")
        if not force_update and os.path.exists(stat_file_path):
            selected_aid_stats[video_aid] = json.load(
                open(stat_file_path, "r", encoding="utf-8")
            )
            continue
        if video_aid in invalid_aid:
            continue

        status, stat = retrieve_single_video_stat(
            video_aid,
            max_try_times=max_try_times,
            sleep_inteval=sleep_inteval,
            cookie=cookie_raw,
        )
        if status in [-1, -2]:
            if status == -1:
                invalid_aid.add(video_aid)
            if status == -2:
                skipped_aid.add(video_aid)
            time.sleep(sleep_inteval)
            continue
        elif status == -403:
            logging.error(f"访问 av{video_aid} 需要 cookie，暂时跳过")
            continue

        with open(stat_file_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(stat, ensure_ascii=False, indent=4))
        selected_aid_stats[video_aid] = stat
        logging.debug(
            f"获取 av{video_aid} 信息成功，点赞{stat['like']:6}, 硬币{stat['coin']:4}，弹幕{stat['danmaku']:4}，版权 {stat['copyright']}; 进度 {n+1: 4} / {len(aid_list)}"
        )

    if len(invalid_aid) > 0:
        marshal.dump(
            invalid_aid, open(os.path.join(data_path, "invalid_aid.pkl"), "wb")
        )
    return skipped_aid, invalid_aid, selected_aid_stats


def str_match_first(
    src: str, target_first: Set[str], target_map: Dict[str, List[str]]
) -> bool:
    # 优化了一天结果还没原本速度快，摆了
    if not (inter := set(src).intersection(target_first)):
        return False
    target_filtered = []
    for i in inter:
        target_filtered.extend(target_map[i])
    for kw in target_filtered:
        if kw in src:
            return True
    return False


def calc_aid_score(
    video_info: Dict,
    comment_list: Optional[List[Dict]],
    good_keyword_first: Set[str],
    bad_keyword_first: Set[str],
    good_keyword_map: Dict[str, List[str]],
    bad_keyword_map: Dict[str, List[str]],
    all_mid_list: Dict[int, Mid],
    s2_base: float = 0,
) -> Tuple[float, float]:
    if not comment_list:
        return 0, 0
    comment_score_summary: Dict[int, List[float]] = defaultdict(list)
    for comment in comment_list:
        comment_mid = all_mid_list.get(comment["mid"], Mid(0))
        comment_s1 = comment_mid.s1 + comment_mid.s1_bias
        comment_s2 = comment_mid.s2 + s2_base
        comment_score = math.atan(comment_s1) / (math.pi * 2) + comment_s2
        comment_msg = comment["message"].lower()

        hit_good_key_words = str_match_first(
            comment_msg, good_keyword_first, good_keyword_map
        )
        hit_bad_key_words = str_match_first(
            comment_msg, bad_keyword_first, bad_keyword_map
        )
        multiply_value = (
            1 * (2 if hit_good_key_words else 1) * (0.5 if hit_bad_key_words else 1)
        )
        comment_score_summary[comment_mid.mid].append(comment_score * multiply_value)

    # aid_score = sum([calc_median(v)*math.sqrt(len(v)) for k,v in comment_score_summary.items()])
    aid_score = sum(
        [sum(v) for k, v in comment_score_summary.items()]
    )  # 不抑制重复评论的算法

    aid_favorite = video_info["favorites"]
    # aid_score /= math.log2(len(comment_list)+2)
    aid_score_norm = math.sqrt(aid_score * math.log10(aid_favorite / 10 + 1))
    # 调高了->热门视频的排名更高，调低了->低播放量而圈子向的视频排名更高
    return aid_score, aid_score_norm


def print_aid_info(
    video_info: Dict[str, Any],
    comments: List[Dict],
    good_keyword_first: Set[str],
    bad_keyword_first: Set[str],
    good_keyword_map: Dict[str, List[str]],
    bad_keyword_map: Dict[str, List[str]],
    all_mid_list: Dict[int, Mid],
):
    aid = video_info["id"]
    aid_author = video_info["author"]
    aiu_mid = video_info["mid"]
    aid_view = max(int(video_info["play"]), 0) if video_info["play"] != "--" else "--"
    aid_title = video_info["title"]
    aid_favorite = video_info["favorites"]
    aid_pubtime = video_info["pubdate"]
    aid_score, aid_score_norm = calc_aid_score(
        video_info,
        comments,
        good_keyword_first,
        bad_keyword_first,
        good_keyword_map,
        bad_keyword_map,
        all_mid_list,
    )
    print(
        f"[av{aid:10}] 计分 = {aid_score_norm:7.4f} @{aid_pubtime}, 播放{aid_view:7}, 收藏{aid_favorite:5}, 评论{len(comments):4} || [uid{aiu_mid:10}] {aid_author}: {aid_title}"
    )


def retrieve_single_video_tag(
    video_aid: int, max_try_times=10, sleep_inteval=3
) -> Tuple[int, List[str]]:
    task = video.Video(aid=video_aid).get_tags
    status, tags_raw = apply_bilibili_api(
        task, video_aid, max_try_times=max_try_times, sleep_inteval=sleep_inteval
    )
    # tags = [{'id':tag['tag_id'], 'name':tag['tag_name']} for tag in tags_raw]
    tags = [tag["tag_name"] for tag in tags_raw]
    return status, tags


def retrieve_single_video_comment(
    video_aid: int, credential: Credential, max_try_times=10, sleep_inteval=3.0
) -> Tuple[int, List[Dict]]:
    task = partial(lazy_get_comments, video_aid, credential)
    status, comments_raw = apply_bilibili_api(
        task, video_aid, max_try_times=max_try_times, sleep_inteval=sleep_inteval
    )
    return status, comments_raw


def retrieve_single_video_stat(
    video_aid: int, max_try_times=10, sleep_inteval=3.0, cookie: Optional[str] = None
) -> Tuple[int, Dict[str, Any]]:
    # task = video.Video(aid=video_aid).get_info # get_stat 貌似已经失效了
    # status, stat = apply_bilibili_api(task, video_aid, max_try_times=max_try_times, sleep_inteval=sleep_inteval)

    ### 临时补救 API，非必要不动它。
    headers = {
        "Accept": "*/*",
        # 'Cookie': raw_cookie,
        "Referer": "https://www.bilibili.com/v/kichiku/mad/",
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/61.0.3163.79 Safari/537.36 Maxthon/5.0",
    }
    if cookie:
        headers["Cookie"] = cookie
    time.sleep(0.2)
    logging.info(f"获取 av{video_aid}")
    temp_dict = requests.get(
        "https://api.bilibili.com/x/web-interface/view",
        {"aid": video_aid},
        headers=headers,
    )
    status = temp_dict.status_code

    if status == -403:  # 无 cookie 会「访问权限不足」的早期受屏蔽视频
        return -403, {}

    try:
        stat_json = temp_dict.json()
        stat = stat_json["data"]
    except:
        stat = None

    assert isinstance(stat, dict), f"获取 av{video_aid} 失败，{status = }, {stat = }"

    stating = stat["stat"]  # 由于获取的 get_info，stat 需要单独挤进去
    stat.update(stating)
    ciding = stat["pages"][0]  # 默认获取第一个视频的 cid
    stat.update(ciding)

    return status, stat


def apply_bilibili_api(
    task: Callable, video_aid: int, *, max_try_times=10, sleep_inteval=3.0
) -> Tuple[int, List[Dict]]:
    try_times = 0
    contents: List[Dict] = []
    while try_times < max_try_times:
        try:
            contents = sync(task())
            break
        except (
            ServerDisconnectedError,
            ClientOSError,
            ConnectTimeout,
            RemoteProtocolError,
            ReadTimeout,
        ):
            try_times += 1
            if try_times == max_try_times:  # 网络错误
                logging.warning(f"Keep ServerDisconnectedError at {video_aid}, skipped")
                return -2, []
            else:
                logging.info(
                    f"ServerDisconnectedError at {video_aid}, retrying {try_times} times"
                )
                switch_proxy()
        except ResponseCodeException as e:
            if e.code in {12002, 12061}:  # 大概是被删了或是移到别的分区了
                logging.warning(f"ResponseCodeException at {video_aid}, aborted")
                return -1, []  # Invalid
            else:
                logging.error(
                    f"Unhandled ResponseCodeException: {e.code} at {video_aid}, skipped"
                )
                return -2, []
        except NetworkException as e:
            if e.status in {412}:  # 被 B 站 ban 了
                logging.warning(
                    f"NetworkException 412 at {video_aid}, retrying {try_times} times"
                )
                try_times += random.randint(0, 1)
                if try_times > 5:
                    # 切换代理
                    switch_proxy()
                time.sleep(sleep_inteval * try_times * 2)
            else:
                logging.error(
                    f"Unhandled NetworkException: {e.status} at {video_aid}, skipped"
                )
                return -2, []
        except KeyboardInterrupt:
            logging.info(f"KeyboardInterrupt at av{video_aid}, exiting")
            exit()
        except Exception as e:
            logging.error(f"Unhandled Exception: {type(e)} {e}")
            from bilibili_api import settings

            if len(settings.proxy) > 0:
                switch_proxy()
            else:
                return -2, []
        finally:
            time.sleep(sleep_inteval * (try_times + 1))
    return 1, contents


def apply_response_getter(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    *,
    max_try_times=10,
    sleep_inteval=3.0,
) -> Tuple[int, Dict[str, Any]]:
    try_times = 0
    while try_times < max_try_times:
        try:
            response = requests.get(url, headers=headers)
        except (
            requests.exceptions.RequestException,
            requests.exceptions.ConnectionError,
        ) as e:
            logging.error(
                f"Unhandled RequestException: {e}, retrying {try_times} times"
            )
            try_times += 1
            time.sleep(sleep_inteval * (try_times + 1))
            continue

        response.encoding = "utf-8"
        result = json.loads(response.text)
        return_code = result["code"]
        if return_code != 0:
            logging.warning(
                f"未成功获取 {url} 数据: return_code={return_code}, message={result['message']}, 第 {try_times} 次尝试"
            )
            if return_code == -504:
                try_times += 1
                time.sleep(sleep_inteval * (try_times + 1))
                continue
            else:
                raise Exception(
                    f"Unhandled Response Code: {return_code}, {result['message']} For {url}"
                )
        data = result["data"]
        return 1, data
    raise Exception(f"Max Try Times Exceeded For {url}")


def switch_proxy():
    logging.info("切换代理")
    from bilibili_api import settings

    try:
        data = requests.get(url=os.getenv("PROXY_LIST_URL", "")).json()
        proxy_url = "http://" + data["obj"][0]["ip"] + ":" + data["obj"][0]["port"]
    except:
        proxy_url = ""
    settings.proxy = proxy_url
