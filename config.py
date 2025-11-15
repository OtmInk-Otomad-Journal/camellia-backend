import time
import os
import threading
import datetime
import yaml
import pytz

from dateutil.parser import isoparse

with open("./config/data.yaml", "r") as conf_file:
    conf = yaml.safe_load(conf_file)

usedTime = time.strftime("%Y%m%d", time.localtime())  # 不再采用存储文本的时间，改为即刻

activity_list = {"wc": "每周挑战特殊推荐"}

### 拉取数据相关 ###
api_header = {
    "Accept": "*/*",
    # 'Cookie': raw_cookie,
    "Referer": "https://www.bilibili.com/v/kichiku/mad/",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/61.0.3163.79 Safari/537.36 Maxthon/5.0",
}

sleep_inteval = 1  # 各处重复调用 api 的间隔秒数

base_path = "./AutoData/"  # 视频数据及评论
delta_days = 11  # 以今天往前的第 delta_days 日开始统计
range_days = 7  # 统计 range_days 天的数据

selected_day = ""  # Debug 等用，指定结束日, YYMMDD 230721
if selected_day != "":
    select = datetime.datetime.strptime(selected_day, "%y%m%d")
    delta_days = (datetime.datetime.now() - select).days + range_days - 1

# 由面板控制时间范围
timezone = pytz.timezone("Asia/Shanghai")  # 本地时区
if len(conf["time_range"]) != 0 and len(selected_day) == 0:
    end_day = isoparse(conf["time_range"][1]).astimezone(timezone)
    start_day = isoparse(conf["time_range"][0]).astimezone(timezone)
    range_days = (end_day - start_day).days + 1
    delta_days = (datetime.datetime.now(tz=timezone) - end_day).days + range_days - 1

weight_path = "./weight/"  # 用户评论权重
weight_new_comp = 1.0  # 新权重的权重，0 代表完全使用旧权重，1 代表完全使用新权重
recursive_times = 4  # 更新权重时的迭代次数；1 代表不更新；一般 4 即收敛

# 音 MAD: 26; 人力: 126; 鬼调: 22；不要用大分区，如 "119" (鬼畜)
# 见 https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/video/video_zone.md
video_zones = conf["video_zones"]  # 拉取这些分区的视频列表 # [26, 126, 22]
tag_whitezone = conf["tag_whitezone"]  # 仅统计此分区，以及 # 26
tag_whitelist = conf[
    "tag_whitelist"
]  # 含有这些 tag 的视频, 西文使用全小写 # ['音mad', "ytpmv"]
pull_video_copyright = -1  # 1: 仅自制, 0: 仅转载, -1: 全部

prefilter_comment_less_than = range_days ** (1 / 2)  # 评论大于此数的视频才会被拉取评论
pull_full_list_stat = conf[
    "pull_full_list_stat"
]  # 拉取前 pull_full_list_stat 个视频的点赞、硬币…数据, -1 为全部 # 100

rank_types = ["ytpmv","common"] # 榜单类型

# !Important! 拉取完整评论*可能*需登录, 见 config_login.py
# 或者使用下面的 cookie 文件
cookie_file_path = "./cookies/cookie.txt"
####################

main_max_title = 30
side_max_title = 23
pick_max_reason = 32
pick_max_box = 640
sep_time = conf["sep_time"]  # 间隔时间 # 20
main_end = conf["main_end"]  # 主榜个数 # 15
side_end = conf["side_end"]  # 副榜个数 # 40
side_count = 4  # 副榜显示
staticFormat = ["png", "jpg", "jpeg"]
side_duration = side_end * 1.5

max_main_duration = conf["max_main_duration"]  # 主榜第一最长时长 70

screen_size = (1920, 1080)
fps = 60

screenRatio = 16 / 9

main_to_side_offset = -1

insert_count = conf["insert_count"]  # 主榜中断个数 # 5

vcodec = "libx264"

render_format = {"vcodec": vcodec, "video_bitrate": "10000k", "audio_bitrate": "320k"}
all_render_format = {
    "vcodec": vcodec,
    "video_bitrate": "10000k",
    "audio_bitrate": "320k",
    "r": "60",
}
read_format = {
    # "vcodec": "h264_cuvid" # 若没有 CUDA 加速，请切换为其它编码器或直接注释本行。
}
audio_render_format = {"audio_bitrate": "320k"}
# smooth_bit_rate = 5000000 # 5k码率保证渲染正常

smooth_bit_rate = float("inf")  # 无限码率

smooth_render_format = {
    "vcodec": vcodec,
    # "video_bitrate" : "4500k",
    "audio_bitrate": "320k",
}
muitl_limit = threading.Semaphore(3)

render_max_threading_count = 1  # 正常渲染下最大线程数
slip_second = 20 # 每分块的时长

render_fast_threading_count = 10  # 快速渲染下线程数

sequence_num_width = 6  # 序列渲染编号最大位数


web_prefix = "http://localhost:7213/"  # 用于网页渲染的本地文件获取地址
render_prefix = "http://localhost:7214"  # 用于网页渲染的在线模板端
panel_prefix = {"address": "0.0.0.0", "port": 7215}  # 用于面板管理的地址
