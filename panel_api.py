from pathlib import Path
import time
import logging
import ctypes
import inspect
import threading
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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

app.include_router(router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app=app,host=panel_prefix["address"],port=panel_prefix["port"])