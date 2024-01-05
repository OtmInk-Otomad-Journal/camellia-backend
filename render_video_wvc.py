import subprocess
import json

def render_video(data,url,audio = None,fast = False):
    command = ["node","wvc_render.js",json.dumps(data)]
    subprocess.Popen(command).wait()