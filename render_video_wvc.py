import execjs
import json

def render_video(data,url,audio = None,fast = False):
    with open('wvc_render.js','r') as render_js:
        code = execjs.compile(render_js.read())
        code.call('render_video',data)