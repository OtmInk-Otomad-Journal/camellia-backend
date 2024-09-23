import datetime
import importlib
from io import BytesIO
import json
from pathlib import Path
import time
import logging
import ctypes
import inspect
import threading
import csv
import os
import shutil
from typing import Callable
import yaml

from fastapi import APIRouter, FastAPI, Body, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from PIL import Image
import hashlib

from program_function import convert_csv, turnAid, intilize_dict, check_dir

import config

from config import panel_prefix

check_dir()

def reload_config():
    """
    重载配置
    """
    importlib.reload(config)

def _async_raise(tid, exctype):
   """raises the exception, performs cleanup if needed"""
   tid = ctypes.c_long(tid)
   if not inspect.isclass(exctype):
      exctype = type(exctype)
   res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
   if res == 0:
      raise ValueError("invalid thread id")
   elif res != 1:
      # """if it returns a number greater than one, you're in trouble,
      # and you should call it again with exc=NULL to revert the effect"""
      ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
      raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
   _async_raise(thread.ident, SystemExit)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

router = APIRouter()

def clean_logger():
    """
    清理日志器
    """
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.root.handlers.clear()

def log_stream(log_time):
    """
    循环返回日志
    """
    with open(Path(f"./log/{log_time}.log"), "r", encoding="utf-8-sig") as log_file:
        # log_file.seek(0, 2)
        while True:
            line = log_file.readline()
            if line:
                yield f"data: {line}\n\n"

@router.get("/backend/get-data-config")
async def get_data_config():
    """
    获取周刊数据配置，以 JSON 返回
    """
    with open("./config/data.yaml","r") as conf_file:
        conf = yaml.safe_load(conf_file)
    return { "code": 0, "msg": None, "data": conf }

@router.post("/backend/save-data-config")
async def save_data_config(data: dict = Body(...)):
    """
    上传周刊数据配置
    """
    with open("./config/data.yaml","r") as conf_file:
        conf = yaml.safe_load(conf_file)
        if(conf == None):
            conf = data
        else:
            conf.update(data)
        conf = intilize_dict(conf)
    with open("./config/data.yaml","w") as conf_file:
        conf_file.write(yaml.dump(conf))

    reload_config()

    return { "code": 0, "msg": None, "data": {} }

@router.get("/backend/get-data")
async def get_data():
    """
    启动获取数据脚本，并开启 SSE 传回日志
    """
    from advanced_data_get import advanced_data_get

    # 如果线程中已经存在未完成的该线程，则直接返回该线程
    for prog in threading.enumerate():
        props = prog.name.split(",")
        if props[0] == 'advanced_data_get':
            log_time = props[1]
            return StreamingResponse(log_stream(log_time), media_type="text/event-stream")

    # 否则启动新线程
    clean_logger()
    log_time = time.strftime("%Y-%m-%d %H-%M-%S")
    logging.basicConfig(format='[%(levelname)s]\t%(message)s',level=logging.INFO,filename="log/" + log_time + '.log', encoding="utf-8-sig")
    thread = threading.Thread(target=advanced_data_get,name=f'advanced_data_get,{log_time}')
    thread.start()
    return StreamingResponse(log_stream(log_time), media_type="text/event-stream")

@router.get("/backend/get-data/stop")
async def stop_get_data():
    """
    强行中止获取数据线程
    """
    for prog in threading.enumerate():
        props = prog.name.split(",")
        if props[0] == 'advanced_data_get':
            stop_thread(prog)
    return { "code": 0, "msg": None, "data": None }

@router.get("/backend/pull-data")
async def pull_data():
    """
    获取已经存在的 data.csv 文件，以 JSON 返回
    """
    try:
        data = convert_csv("./data/data.csv")
        return { "code": 0, "msg": None, "data": data}
    except:
        return { "code": -1, "msg": "未知错误", "data": {}}

@router.post("/backend/save-data")
async def save_data(data: list[dict] = Body(...)):
    """
    保存 data.csv 文件，并将原始版本重命名
    """
    try:
        if os.path.exists("./data/data.csv"):
            shutil.move("./data/data.csv",f"./data/backup/data {time.strftime('%Y-%m-%d %H-%M-%S')}.csv")
        with open("./data/data.csv","w",encoding="utf-8-sig",newline='') as csvfile:
            co_header = data[0].keys()
            writer = csv.DictWriter(csvfile, co_header)
            writer.writeheader()
            writer.writerows(data)
        return { "code": 0, "msg": None, "data": {} }
    except:
        return { "code": -1, "msg": "未知错误", "data": {} }

@router.post("/backend/upload-pickup")
async def upload_pickup(file: UploadFile = File(...)):
    """
    上传 Pick Up 数据，并保存为 pick.csv
    """
    contents = await file.read()
    data = contents.decode("utf-8-sig")
    with open("./data/pick.csv","w",encoding="utf-8-sig",newline="") as file:
        file.write(data)

@router.get("/backend/pull-pickup-data")
async def pull_data():
    """
    获取已经存在的 pick.csv 文件，根据时间范围限制返回量，以 JSON 返回
    """
    try:
        from config import activity_list

        min_time = datetime.datetime.today() + datetime.timedelta(days=-8)
        pickList = []
        with open("./data/pick.csv","r",encoding="utf-8-sig",newline='') as csvfile:
            listed = csv.DictReader(csvfile)
            for item in listed:
                time = item["提交时间（自动）"]
                realtime = datetime.datetime.strptime(time,"%Y/%m/%d %H:%M:%S")
                if realtime < min_time:
                    continue
                aid = turnAid(str(item["推荐作品 av 号 / BV 号（必填）"]))
                text = item["推荐理由（必填）"]
                picker = item["推荐人"]
                if picker == "":
                    picker = "神秘人"
                if item["您的备注"] in activity_list: # 活动特别识别
                    act = item["您的备注"]
                else:
                    act = ""
                pickList.append({
                    "status": True,
                    "aid": aid,
                    "reason": text,
                    "picker": picker,
                    "activity": act
                })
        return { "code": 0, "msg": None, "data": pickList }
    except:
        return { "code": -1, "msg": "未知错误", "data": {} }

@router.post("/backend/send-pickup-data")
async def send_pickup_data(data: list[dict] = Body(...)):
    """
    传回 Pick Up 处理数据
    """
    try:
        if os.path.exists("./data/pick_filtered.csv"):
            shutil.move("./data/pick_filtered.csv",f"./data/backup/pick_filtered {time.strftime('%Y-%m-%d %H-%M-%S')}.csv")
        with open("./data/pick_filtered.csv","w",encoding="utf-8-sig",newline='') as csvfile:
            co_header = data[0].keys()
            writer = csv.DictWriter(csvfile, co_header)
            writer.writeheader()
            for item in data:
                if item["status"] != True:
                    continue
                writer.writerow(item)
        return { "code": 0, "msg": None, "data": {} }
    except:
        return { "code": -1, "msg": "未知错误", "data": {} }

@router.get("/backend/get-pickup-data")
async def get_pickup_data():
    """
    启动获取 Pick Up 数据脚本，并开启 SSE 传回日志
    """
    from advanced_resource_get import advanced_resource_get

    # 如果线程中已经存在未完成的该线程，则直接返回该线程
    for prog in threading.enumerate():
        props = prog.name.split(",")
        if props[0] == 'advanced_resource_get':
            log_time = props[1]
            return StreamingResponse(log_stream(log_time), media_type="text/event-stream")

    # 否则启动新线程
    clean_logger()
    log_time = time.strftime("%Y-%m-%d %H-%M-%S")
    logging.basicConfig(format='[%(levelname)s]\t%(message)s',level=logging.INFO,filename="log/" + log_time + '.log', encoding="utf-8-sig")
    thread = threading.Thread(target=advanced_resource_get,name=f'advanced_resource_get,{log_time}')
    thread.start()
    return StreamingResponse(log_stream(log_time), media_type="text/event-stream")

@router.get("/backend/get-pickup-data/stop")
async def stop_get_data():
    """
    强行中止获取数据线程
    """
    for prog in threading.enumerate():
        props = prog.name.split(",")
        if props[0] == 'advanced_resource_get':
            stop_thread(prog)
    return { "code": 0, "msg": None, "data": None }

send_cookie_status = False

@router.get("/backend/send-cookie")
async def send_cookie():
    """
    获取 B 站 Cookie，将会返回二维码
    """
    global send_cookie_status
    send_cookie_status = True
    return StreamingResponse(qr_code_stream(), media_type="text/event-stream")

@router.get("/backend/send-cookie/stop")
async def send_cookie_stop():
    """
    停止获取二维码
    """
    global send_cookie_status
    send_cookie_status = False
    return { "code": 0, "msg": None, "data": None }

def qr_code_stream():
    """
    返回二维码流
    """
    import requests
    import time
    url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate?source=main-fe-header'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0',
        'Referer': 'https://www.bilibili.com/',
        'Origin': 'https://www.bilibili.com'
    }

    response = requests.get(url=url, headers=headers).json()
    qrcode_key = response['data']['qrcode_key']
    yield "data: " + json.dumps({"qr_code_url": response['data']['url']}) + "\n\n"

    check_login_url = f'https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={qrcode_key}&source=main-fe-header'
    # 创建一个Session对象
    session = requests.Session()
    while send_cookie_status:
        try:
            data = session.get(url=check_login_url, headers=headers).json()
            if data['data']['code'] == 0:
                response = session.get('https://www.bilibili.com/', headers=headers)
                with open('cookies/cookie.txt', 'w') as f:
                    for key, value in session.cookies.get_dict().items():
                        f.write(f"{key}={value};")
                yield "data: " + json.dumps({"success": True}) + "\n\n"
                break
            time.sleep(1)
        except:
            yield "data: " + json.dumps({"success": False}) + "\n\n"
            break

@router.get("/backend/get-calendar")
async def get_calendar():
    """
    获取当前小日历
    """
    return { "code": 0, "msg": None, "data": convert_csv("option/calendar.csv") }

@router.post("/backend/save-calendar")
async def send_pickup_data(data: list[dict] = Body(...)):
    """
    传回小日历
    """
    try:
        if data == []:
            with open("option/calendar.csv","w",encoding="utf-8-sig",newline='') as csvfile:
                csvfile.write("")
            return { "code": 0, "msg": None, "data": {} }
        with open("option/calendar.csv","w",encoding="utf-8-sig",newline='') as csvfile:
            co_header = data[0].keys()
            writer = csv.DictWriter(csvfile, co_header)
            writer.writeheader()
            writer.writerows(data)
        return { "code": 0, "msg": None, "data": {} }
    except:
        return { "code": -1, "msg": "未知错误", "data": {} }

@router.post("/backend/upload-calendar-image")
async def upload_pickup(file: UploadFile = File(...)):
    """
    上传小日历背景图片
    """
    contents = await file.read()
    md5 = hashlib.md5(contents).hexdigest()
    url = f"/cover/calendar/{md5}.png"
    image = Image.open(BytesIO(contents))
    image.save(f".{url}")
    return { "code": 0, "msg": None, "data": {"url": url} }

@router.post("/backend/upload-calendar-config")
async def upload_pickup_config(data: dict = Body(...)):
    """
    上传小日历配置
    """
    with open("./config/calendar.yaml","r") as conf_file:
        conf = yaml.safe_load(conf_file)
        if(conf == None):
            conf = data
        else:
            conf.update(data)
    with open("./config/calendar.yaml","w") as conf_file:
        conf_file.write(yaml.dump(conf))

    return { "code": 0, "msg": None, "data": {} }

@router.get("/backend/get-calendar-config")
async def get_calendar_config():
    """
    获取小日历配置，以 JSON 返回
    """
    with open("./config/calendar.yaml","r") as conf_file:
        conf = yaml.safe_load(conf_file)
    return { "code": 0, "msg": None, "data": conf }

@router.post("/backend/upload-calendar-music")
async def upload_calendar_music(file: UploadFile = File(...)):
    """
    上传小日历音乐
    """
    contents = await file.read()
    with open("./option/calendar/bgm.mp3","wb") as file:
        file.write(contents)
    return { "code": 0, "msg": None, "data": {} }

@router.get("/backend/start-render")
async def start_render():
    """
    启动渲染脚本，并开启 SSE 传回日志
    """
    from main_progress import main_progress

    # 如果线程中已经存在未完成的该线程，则直接返回该线程
    for prog in threading.enumerate():
        props = prog.name.split(",")
        if props[0] == 'main_progress':
            log_time = props[1]
            return StreamingResponse(log_stream(log_time), media_type="text/event-stream")

    # 否则启动新线程
    clean_logger()
    log_time = time.strftime("%Y-%m-%d %H-%M-%S")
    logging.basicConfig(format='[%(levelname)s]\t%(message)s',level=logging.INFO,filename="log/" + log_time + '.log', encoding="utf-8-sig")
    thread = threading.Thread(target=main_progress,name=f'main_progress,{log_time}')
    thread.start()
    return StreamingResponse(log_stream(log_time), media_type="text/event-stream")

@router.get("/backend/start-render/stop")
async def stop_get_data():
    """
    强行中止渲染线程
    """
    for prog in threading.enumerate():
        props = prog.name.split(",")
        if props[0] == 'main_progress':
            stop_thread(prog)
    return { "code": 0, "msg": None, "data": None }

@router.get("/backend/download-result/{filename}")
async def download_file(filename: str):
    """
    直接下载对应视频
    """
    directory_path = f"./output/final/"
    file_path = os.path.join(directory_path, filename)
    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)

@router.get("/backend/get-result-list")
async def get_result_list():
    """
    获取存在的视频列表
    """
    directory_path = f"./output/final/"
    file_list = []
    for curDir, dirs, files in os.walk(f"{directory_path}"):
        for file in files:
            file_list.append({"value": file})
    return { "code": 0, "msg": None, "data": {"files": file_list} }

@router.get("/backend/get-fastview-list")
async def get_fastview_list():
    """
    获取存在的快速导航列表
    """
    directory_path = f"./fast_view/"
    file_list = []
    for curDir, dirs, files in os.walk(f"{directory_path}"):
        for file in files:
            file_list.append({"value": file})
    return { "code": 0, "msg": None, "data": {"files": file_list} }

@router.get("/backend/get-fastview/{filename}")
async def get_fastview(filename: str):
    """
    获取快速导航内容
    """
    with open(f"./fast_view/{filename}",encoding="utf-8-sig") as file:
        return { "code": 0, "msg": None, "data": {"content": file.read()}}

app.include_router(router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app=app,host=panel_prefix["address"],port=panel_prefix["port"])