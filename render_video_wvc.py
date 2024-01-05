import subprocess
import hashlib
import json

def render_video(data,url,audio = None,fast = False):
    identify_code = hashlib.md5(str(data).encode()).hexdigest()
    json_name = f"temp/{identify_code}.json"
    with open(json_name,"w",encoding="utf-8-sig") as temp_json:
        json.dump(temp_json)
    command = ["node","wvc_render.js",json_name]
    subprocess.Popen(command).wait()