import time
import os
import threading
import datetime

if os.path.exists("./time.txt"):
    usedTime = str(open("./time.txt","r").read())
else:
    usedTime = time.strftime("%Y%m%d", time.localtime())
    with open("./time.txt","w") as f:
        f.write(usedTime)

### 拉取数据相关 ###
sleep_inteval = 1             # 各处重复调用 api 的间隔秒数

base_path = "./AutoData/"       # 数据存储路径
delta_days = 11                 # 以今天往前的第 delta_days 日开始统计
range_days = 7                  # 统计 range_days 天的数据

selected_day = "230721"       # 用于 Debug 或其它用途 , YYMMDD
if selected_day != "":
    select = datetime.datetime.strptime(selected_day,"%y%m%d")
    delta_days = (datetime.datetime.now() - select).days + range_days - 1

# 音 MAD: 26; 人力: 126; 鬼调: 22；不要用大分区，如 "119" (鬼畜)
# 见 https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/video/video_zone.md
video_zones = [26, 126, 22]     # 拉取这些分区的视频列表
tag_whitezone = [26]            # 仅统计此分区，以及
tag_whitelist = ['音mad', "ytpmv"] # 含有这些 tag 的视频, 西文使用全小写
pull_video_copyright = -1       # 1: 仅自制, 0: 仅转载, -1: 全部

prefilter_comment_less_than = range_days**(1/2) # 评论大于此数的视频才会被拉取评论
pull_full_list_stat = 100       # 拉取前 pull_full_list_stat 个视频的点赞、硬币…数据, -1 为全部

# !Important! 拉取完整评论*可能*需登录, 见 config_login.py
# 或者使用下面的 cookie 文件
cookie_file_path = "./cookies/cookie.txt"
####################

main_max_title = 30
side_max_title = 23
pick_max_reason = 32
pick_max_box = 640
sep_time = 20 # 间隔时间
main_end = 15 # 主榜个数
side_end = 40 # 副榜个数
side_count = 4 # 副榜显示
staticFormat = ["png","jpg","jpeg"]
side_duration = side_end * 1.5

max_main_duration = 120 # 主榜第一最长时长

screen_size = (1920,1080)
fps = 60

screenRatio = 16 / 9

avatar_size = (70,70)
cover_size = (401,251)
side_avatar_size = (38,38)
side_cover_size = (276,156)

end_logo = True

main_to_side_offset = -1

insert_count = 5 # 主榜中断个数

render_format = {
    "vcodec": "h264_nvenc", # 若没有 CUDA 加速，请切换为其它编码器或直接注释本行。
    "video_bitrate" : "10000k",
    "audio_bitrate" : "320k"
}
all_render_format = {
    "vcodec": "h264_nvenc", # 若没有 CUDA 加速，请切换为其它编码器或直接注释本行。
    "video_bitrate" : "10000k",
    "audio_bitrate" : "320k",
    "r": "60"
}
read_format = {
    "vcodec": "h264_cuvid" # 若没有 CUDA 加速，请切换为其它编码器或直接注释本行。
}
muitl_limit = threading.Semaphore(30)
render_max_threading_count = 1

sequence_num_width = 6 # 序列渲染编号最大位数

web_prefix = "http://localhost:7213/" # 用于网页渲染的本地文件获取地址
render_prefix = "http://127.0.0.1:5173" # 用于网页渲染的在线模板端