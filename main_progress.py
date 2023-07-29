import logging
import os

from danmuku_time import danmuku_time
from program_function import exactVideoLength , getVideo , convert_csv , extract_single_column
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
    full_time = exactVideoLength(viding["aid"])

    if render_times == 1:
        # 副榜段落合成
        if os.path.exists("./output/clip/SideRank.mp4"):
            pass
        ## 当存在 ED 时，就用指定 ED
        elif os.path.exists("./option/ed.mp4"):
            url = f"{render_prefix}/ed"
            work_info = {
                "start_time": 0,
                "full_time": exactVideoLength("./option/ed.mp4"),
                "web_prefix": web_prefix,
                "video_src": "./option/ed.mp4",
                "output_src": f"./output/clip/SideRank.mp4",
                "more_data": ranked_list[main_end:side_end]
            }
            render_video(work_info,url)
        ## 否则主榜连着副榜一起放
        else:
            url = f"{render_prefix}/side"
            viding.update({
                "full_time": full_time,
                "start_time" : 0,
                "output_src": f"./output/clip/MainRank_1.mp4",
                "more_data": ranked_list[main_end:side_end]
            })
            render_video(viding,url)
            continue
    # 否则正常渲染。
    url = f"{render_prefix}/main"
    viding.update({ "output_src": f"./output/clip/MainRank_{render_times}.mp4" })
    render_video(viding,url)


# PICK UP 合成
picks = 0
for picking in picked_list:
    picks += 1
    if os.path.exists(f"./output/clip/PickRank_{picks}.mp4"):
        continue
    video_src = os.path.abspath(getVideo(picking["aid"],picking["part"]))
    full_time = exactVideoLength(picking["aid"])
    start_time,end_time = danmuku_time(picking["aid"],full_time,sep_time)
    picking.update({ "output_src": f"./output/clip/PickRank_{picks}.mp4" })

    url = f"{render_prefix}/pick"
    render_video(picking,url)

# 开头合成
if os.path.exists("./output/clip/Opening.mp4"):
    pass
else:
    render_simple()

# 总拼接
AllVideo(main_end,picked_list)