import logging
import os
import threading

from all_create import AllVideo
from program_function import convert_csv , extract_single_column , check_env
from render_video_wvc import render_video
# 声明变量
from config import *

# 日志记录
logging.basicConfig(format='[%(levelname)s]\t%(message)s',filename="log/" + time.strftime("%Y-%m-%d %H-%M-%S") + '.log', level=logging.INFO)
formatter = logging.Formatter('[%(levelname)s]\t%(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel('INFO')
logger = logging.getLogger()
logger.addHandler(console_handler)

check_env()

# 获取数据
ranked_list = convert_csv("data/viewpicked.csv")

# 段落合成
render_times = 0
rend_q = []
for viding in ranked_list:
    render_times += 1
    if os.path.exists(f"./output/clip/ViewRank_{render_times}.mp4"):
        continue

    # 正常渲染。
    url = f"{render_prefix}/viewpick"
    viding.update({ "output_src": f"./output/clip/ViewRank_{render_times}.mp4" , "url": url })
    muitl_limit.acquire()
    rend_s = threading.Thread(target=render_video,args=(viding,url))
    rend_s.start()
    rend_q.append(rend_s)
    # render_video(viding,url)

for sq in rend_q:
    sq.join()

# 总拼接