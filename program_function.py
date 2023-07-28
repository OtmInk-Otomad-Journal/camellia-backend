import requests
import logging
import subprocess
import codecs
import csv
import ffmpeg
from io import BytesIO
from PIL import Image
from config import *
from haishoku.haishoku import Haishoku

def get_img(aid):
    video_data = requests.get(url=f"https://api.bilibili.com/x/web-interface/view?aid={aid}").json()
    face = video_data["data"]["owner"]["face"]
    cover = video_data["data"]["pic"]
    # 头像
    if not os.path.exists(f"avatar/{aid}.png"):
        img_content = requests.get(url=face).content
        img = Image.open(BytesIO(img_content))
        img.save(f"avatar/{aid}.png")
    # 封面
    if not os.path.exists(f"cover/{aid}.png"):
        img_content = requests.get(url=cover).content
        img = Image.open(BytesIO(img_content))
        img.save(f"cover/{aid}.png")
    callback = {
        "avatar": os.path.abspath(f"avatar/{aid}.png"),
        "cover": os.path.abspath(f"cover/{aid}.png")
        }
    return callback

def turnAid(id):
    if ("av" in id) or ("AV" in id):
        return id[2:]
    elif ("BV" in id):
        site = "https://api.bilibili.com/x/web-interface/view?bvid=" + id
        lst = codecs.decode(requests.get(site).content, "utf-8").split("\"")
        return str(lst[16][1:-1])

# 视频长度获取
def exactVideoLength(url):
    tdur = float(ffmpeg.probe(url)["streams"][0]["duration"])
    return tdur

# 视频下载
def get_video(aid,part = 1):
    command = ["./lux"]
    if part > 1:
        p_src = f"?p={part}"
    else:
        p_src = ""
    if os.path.exists(f"./cookies/cookie.txt"):
        command.append("-c")
        command.append("./cookies/cookie.txt")
    if os.path.exists(f"./video/{aid}.mp4"):
        logging.info(f"av{aid} 视频已经存在")
        return os.path.abspath(f"./video/{aid}.mp4")
    while(not os.path.exists(f"./video/{aid}.mp4")):
        logging.info(f"下载 av{aid} 视频...")
        subprocess.Popen(command + ["-o","./video","-O",aid,f"av{aid}{p_src}"]).wait()
    logging.info(f"av{aid} 视频下载完成")
    return os.path.abspath(f"./video/{aid}.mp4")

# CSV 表格转换
def convert_csv(file):
    outlist = []
    with open(file,"r",encoding="utf-8-sig") as datafile:
        lists = csv.DictReader(datafile)
        ok = 0
        for sti in lists:
            outlist.append(sti)
    return outlist

def extract_single_column(post_list,target,end_num):
    extractArr = []
    ignum = 0
    for ig in post_list:
        ignum += 1
        if ignum > end_num:
            break
        extractArr.append(str(ig[target]))
    return extractArr

# 图像颜色均值
def average_image_color(file):
    dominant = Haishoku.getDominant(file)
    return dominant