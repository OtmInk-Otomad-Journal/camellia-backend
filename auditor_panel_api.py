import time
import csv
import os
import shutil

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from fastapi import APIRouter, FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware

from program_function import convert_csv


def auditor_check_dir():
    """
    检查文件夹是否齐全
    """
    dirpaths = ["data", "data/backup"]
    for dirpath in dirpaths:
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)


auditor_check_dir()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()


@router.get("/backend/pull-data")
async def pull_data():
    """
    获取已经存在的 data.csv 文件，以 JSON 返回
    """
    try:
        data = convert_csv("./data/data.csv")
        return {"code": 0, "msg": None, "data": data}
    except:
        return {"code": -1, "msg": "未知错误", "data": {}}


@router.post("/backend/save-data")
async def save_data(data: list[dict] = Body(...)):
    """
    保存 data.csv 文件，并将原始版本重命名
    """
    try:
        if os.path.exists("./data/data.csv"):
            shutil.move(
                "./data/data.csv",
                f"./data/backup/data {time.strftime('%Y-%m-%d %H-%M-%S')}.csv",
            )
        with open("./data/data.csv", "w", encoding="utf-8-sig", newline="") as csvfile:
            co_header = data[0].keys()
            writer = csv.DictWriter(csvfile, co_header)
            writer.writeheader()
            writer.writerows(data)
        return {"code": 0, "msg": None, "data": {}}
    except:
        return {"code": -1, "msg": "未知错误", "data": {}}


@router.get("/down-data/")
async def down_data(key: str = ""):
    """
    传回审核后的数据
    """
    if key == os.getenv("ONLINE_AUTH_KEY", ""):
        try:
            return {"code": 0, "msg": None, "data": convert_csv(data)}
        except:
            return {"code": -1, "msg": "未知错误", "data": {}}
    else:
        return {"code": -403, "msg": "权限禁止", "data": {}}


@router.post("/push-data/")
async def down_data(data: list[dict] = Body(...), key: str = ""):
    """
    上传审核前的数据
    """
    if key == os.getenv("ONLINE_AUTH_KEY", ""):
        try:
            if os.path.exists("./data/data.csv"):
                shutil.move(
                    "./data/data.csv",
                    f"./data/backup/data {time.strftime('%Y-%m-%d %H-%M-%S')}.csv",
                )
            with open(
                "./data/data.csv", "w", encoding="utf-8-sig", newline=""
            ) as csvfile:
                co_header = data[0].keys()
                writer = csv.DictWriter(csvfile, co_header)
                writer.writeheader()
                writer.writerows(data)
            return {"code": 0, "msg": None, "data": {}}
        except:
            return {"code": -1, "msg": "未知错误", "data": {}}
    else:
        return {"code": -403, "msg": "权限禁止", "data": {}}


app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    port = os.getenv("ONLINE_PORT", "")
    uvicorn.run(app=app, host="0.0.0.0", port=port)
