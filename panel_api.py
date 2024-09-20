import datetime
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
from fastapi import APIRouter, FastAPI, Body, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from program_function import convert_csv, turnAid

from config import panel_prefix

from advanced_data_get import advanced_data_get

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

@router.get("/backend/get-data")
async def get_data():
    """
    启动获取数据脚本，并开启 SSE 传回日志
    """

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
    return { "code": 0, "msg": None, "data": convert_csv("data/data.csv") }

@router.post("/backend/save-data")
async def save_data(data: list[dict] = Body(...)):
    """
    保存 data.csv 文件，并将原始版本重命名
    """
    try:
        if os.path.exists("data/data.csv"):
            shutil.move("data/data.csv",f"data/backup/data {time.strftime('%Y-%m-%d %H-%M-%S')}.csv")
        with open("data/data.csv","w",encoding="utf-8-sig",newline='') as csvfile:
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
    with open("data/pick.csv","w",encoding="utf-8-sig",newline="") as file:
        file.write(data)

@router.get("/backend/pull-pickup-data")
async def pull_data():
    """
    获取已经存在的 pick.csv 文件，根据时间范围限制返回量，以 JSON 返回
    """
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

app.include_router(router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app=app,host=panel_prefix["address"],port=panel_prefix["port"])