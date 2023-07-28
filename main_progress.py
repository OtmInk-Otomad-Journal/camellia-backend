import logging
import os
import threading

from danmuku_time import danmuku_time
from program_function import exactVideoLength , getVideo , convert_csv , extract_single_column , inner_web
from render_video import render_video
# 声明变量
from config import *

# 日志记录
logging.basicConfig(format='[%(levelname)s]\t%(message)s',filename="log/" + time.strftime("%Y-%m-%d %H-%M-%S") + '.log', level=logging.DEBUG)
formatter = logging.Formatter('[%(levelname)s]\t%(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel('DEBUG')
logger = logging.getLogger()
logger.addHandler(console_handler)

# 启动端口
inner_web(port)

# 获取数据
ranked_list = convert_csv("data/data.csv")

# 主榜列表单独提取
mainArr = extract_single_column(ranked_list,"aid",main_end)

# PICK UP 数据
picked_list = []
if os.path.exists(f"./data/pick.csv"):
    picked_list = convert_csv(f"./data/pick.csv")

# 主榜段落合成
render_times = 0
for viding in ranked_list:
    render_times += 1
    if render_times > main_end:
        break
    if os.path.exists(f"./output/clip/MainRank_{render_times}.mp4"):
        continue
    video_src = getVideo(viding["aid"],int(viding["part"])) # 绝对路径以使用 HTML 模板
    full_time = exactVideoLength(viding["aid"])

    if render_times == 1:
        # 副榜段落合成
        if os.path.exists("./output/clip/SideRank.mp4"):
            pass
        ## 当存在 ED 时，就用指定 ED
        elif os.path.exists("./option/ed.mp4"):
            url = "file://" + os.path.abspath("./template/SideRank.html")
            work_info = {
                "start_time": 0,
                "sep_time": exactVideoLength("./option/ed.mp4"),
                "video_src": os.path.abspath("./option/ed.mp4"),
                "output_src": f"./output/clip/SideRank.mp4",
                "more_data": ranked_list[main_end:side_end]
            }
            render_video(work_info,url)
        ## 否则主榜连着副榜一起放
        else:
            url = "file://" + os.path.abspath("./template/MainToSideVideo.html")
            work_info = viding + {
                "sep_time": full_time,
                "start_time" : 0,
                "video_src": video_src,
                "cover_src": f"http://{host}:{port}/cover/{viding['aid']}.png",
                "output_src": f"./output/clip/MainRank_{render_times}.mp4",
                "more_data": ranked_list[main_end:side_end]
            }
            render_video(work_info,url)
            continue

    if viding["start_time"] == "":
        start_time,end_time = danmuku_time(viding["aid"],full_time,sep_time)
    else:
        start_time,end_time = int(viding["start_time"]),sep_time

    work_info = viding + {
        "full_time" : full_time,
        "sep_time": end_time - start_time,
        "start_time" : start_time,
        "end_time" : end_time,
        "video_src": video_src,
        "web_video_src": f"http://{host}:{port}{video_src}",
        "cover_src": f"http://{host}:{port}/cover/{viding['aid']}.png",
        "output_src": f"./output/clip/MainRank_{render_times}.mp4",
        "avatar_src": f"http://{host}:{port}/avatar/{viding['aid']}.png",
    }

    url = "file://" + os.path.abspath("./template/MainRank.html")
    render_video(work_info,url)


# PICK UP 合成
picks = 0
for picking in picked_list:
    picks += 1
    if os.path.exists(f"./output/clip/PickRank_{picks}.mp4"):
        continue
    video_src = os.path.abspath(getVideo(picking["aid"],picking["part"]))
    full_time = exactVideoLength(picking["aid"])
    start_time,end_time = danmuku_time(picking["aid"],full_time,sep_time)
    work_info = picking + {
        "full_time" : full_time,
        "start_time" : start_time,
        "sep_time": sep_time,
        "end_time" : end_time,
        "video_src": video_src,
        "output_src": f"./output/clip/PickRank_{picks}.mp4"
    }

    url = "file://" + os.path.abspath("./template/PickRank.html")
    render_video(work_info,url)

# 开头合成
if os.path.exists("./output/clip/Opening.mp4"):
    pass
else:
    render_simple()

# 总拼接
AllVideo(main_end,picked_list)