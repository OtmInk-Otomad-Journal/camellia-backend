import logging
import os
import threading

from all_create import AllVideo
from program_function import convert_csv , extract_single_column
from render_video import render_video
# 声明变量
from config import *

# 日志记录
logging.basicConfig(format='[%(levelname)s]\t%(message)s',filename="log/" + time.strftime("%Y-%m-%d %H-%M-%S") + '.log', level=logging.INFO)
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
rend_q = []
for viding in ranked_list:
    render_times += 1
    if render_times > main_end:
        break
    if os.path.exists(f"./output/clip/MainRank_{render_times}.mp4"):
        continue

    if render_times == 1:
        # 副榜段落合成
        if os.path.exists("./output/clip/SideRank.mp4"):
            pass
        else:
            url = f"{render_prefix}/main"
            viding.update({
                "output_src": f"./output/clip/MainRank_1.mp4",
                "side_duration": int(float(viding["full_time"]) * 0.6),
                "more_data": ranked_list[main_end:side_end]
            })
            muitl_limit.acquire()
            rend_s = threading.Thread(target=render_video,args=(viding,url))
            rend_s.start()
            rend_q.append(rend_s)
            # render_video(viding,url)
            continue
    # 否则正常渲染。
    url = f"{render_prefix}/main"
    viding.update({ "output_src": f"./output/clip/MainRank_{render_times}.mp4" })
    muitl_limit.acquire()
    rend_s = threading.Thread(target=render_video,args=(viding,url))
    rend_s.start()
    rend_q.append(rend_s)
    # render_video(viding,url)

# PICK UP 合成
picks = 0
for picking in picked_list:
    picks += 1
    if os.path.exists(f"./output/clip/PickRank_{picks}.mp4"):
        continue
    picking.update({ "output_src": f"./output/clip/PickRank_{picks}.mp4" })
    url = f"{render_prefix}/pick"
    muitl_limit.acquire()
    rend_s = threading.Thread(target=render_video,args=(picking,url))
    rend_s.start()
    rend_q.append(rend_s)
    # render_video(picking,url)

for sq in rend_q:
    sq.join()

# 总拼接
AllVideo(main_end,picked_list)