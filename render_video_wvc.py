import subprocess
import hashlib
import json
from program_function import audio_process
from config import *

def render_video(data,url,audio = None,fast = False):
    start_time = data["start_time"]
    full_duration = data["full_time"]
    audio_file = audio_process(data["aid"],float(start_time)*1000,float(full_duration)*1000,audio)
    data.update({ "audio_src": audio_file })

    identify_code = hashlib.md5(str(data).encode()).hexdigest()
    json_name = f"temp/{identify_code}.json"
    with open(json_name,"w",encoding="utf-8-sig") as temp_json:
        json.dump(data,temp_json)
    command = ["node","wvc_render.js",json_name]
    subprocess.Popen(command).wait()