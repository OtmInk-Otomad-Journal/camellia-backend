import subprocess
import hashlib
import json
import logging
from program_function import audio_process,video_cut
from config import *

def render_video(data,url,audio = None,fast = False):
    start_time = data["start_time"]
    full_duration = data["full_time"]
    if not fast:
        logging.info("正在裁剪视频...")
        video_file = video_cut(data["aid"],float(start_time),float(full_duration))
    else:
        video_file = ""
    logging.info("正在处理音频...")
    audio_file = audio_process(data["aid"],float(start_time)*1000,float(full_duration)*1000,audio)
    data.update({ "audio_src": audio_file , "video_src": video_file })

    identify_code = hashlib.md5(str(data).encode()).hexdigest()
    json_name = f"./temp/{identify_code}.json"
    with open(json_name,"w",encoding="utf-8-sig") as temp_json:
        json.dump(data,temp_json)
    command = ["node","wvc_render.js",json_name]
    logging.info("转交 Node.js 渲染")
    subprocess.Popen(command).wait()

    muitl_limit.release()