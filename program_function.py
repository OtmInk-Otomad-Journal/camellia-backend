import requests
import logging
import subprocess
import codecs
import csv
import ffmpeg
import colorsys
import html
from io import BytesIO
from PIL import Image
from config import *
import numpy as np
from haishoku.haishoku import Haishoku

def get_img(aid):
    video_data = requests.get(url=f"https://api.bilibili.com/x/web-interface/view?aid={aid}").json()
    face = video_data["data"]["owner"]["face"]
    cover = video_data["data"]["pic"]
    # 头像
    if not os.path.exists(f"./avatar/{aid}.png"):
        img_content = requests.get(url=face).content
        img = Image.open(BytesIO(img_content))
        img.save(f"./avatar/{aid}.png")
    # 封面
    if not os.path.exists(f"cover/{aid}.png"):
        img_content = requests.get(url=cover).content
        img = Image.open(BytesIO(img_content))
        img.save(f"./cover/{aid}.png")
    callback = {
        "avatar": f"./avatar/{aid}.png",
        "cover": f"./cover/{aid}.png"
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
        return f"./video/{aid}.mp4"
    while(not os.path.exists(f"./video/{aid}.mp4")):
        logging.info(f"下载 av{aid} 视频...")
        subprocess.Popen(command + ["-o","./video","-O",str(aid),f"av{aid}{p_src}"]).wait()
    logging.info(f"av{aid} 视频下载完成")
    return f"./video/{aid}.mp4"

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

def average_image_palette(file):
    palette = Haishoku.getPalette(file)
    return palette

def calc_color(file):
    # dark_mean = 90
    # light_mean = 229
    color_palette = average_image_palette(file)
    outnum = 0
    palette_num = len(color_palette)
    for single_color in color_palette:
        # outnum += 1
        # std = std_judge(single_color[1])
        # if std <= 15: # 计算标准差，以便选取更为鲜艳的颜色
        #     if not (outnum >= palette_num):
        #         if not color_palette[outnum][0] < 0.1:
        #             continue
        # mean = np.mean(single_color[1])
        # if not mean > 0: # 防止纯黑以至分母乘 0
        #     single_color[1] = (1,1,1)
        #     mean = 1
        # light_adjust = light_mean / mean
        # dark_adjust = dark_mean / mean
        # light_color = adjust_brightness(single_color[1],light_adjust)
        # dark_color = adjust_brightness(single_color[1],dark_adjust)
        outnum += 1
        hsl = rgb2hsl(single_color[1])
        if hsl[1] < 0.25:
            if not (outnum >= palette_num):
                if not color_palette[outnum][0] < 0.15:
                    continue
        light_color = f'({hsl[0]},{hsl[1]*100}%,75%)'
        dark_color = f'({hsl[0]},{hsl[1]*100}%,35%)'
        return [ light_color , dark_color ]

def rgb2hsl(rgb):
    hls = colorsys.rgb_to_hls(rgb[0] / 255,rgb[1] / 255,rgb[2] / 255)
    hsl = (hls[0] * 360, hls[2] , hls[1])
    return hsl

def adjust_brightness(rgb,scale):
    return ( rgb[0] * scale , rgb[1] * scale , rgb[2] * scale )

def std_judge(rgb):
    std = np.std(rgb)
    return std

def check_dir():
    dirpaths = ["avatar","cover","data",
            "fast_view","log","option",
            "output","output/clip","output/final",
            "video","cookies","temp","option/ads"]
    for dirpath in dirpaths:
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)
    if not os.path.exists("./option/blacklist.csv"):
        # 预先黑名单
        with open("option/blacklist.csv","w",encoding="utf-8-sig",newline='') as blackfile:
            header = ["aid","title"]
            blackInfo = csv.DictWriter(blackfile,header)
            blackInfo.writeheader()
    if not os.path.exists("./option/adjust.csv"):
        # 预先内容系数调整
        with open("option/adjust.csv","w",encoding="utf-8-sig",newline='') as adjustfile:
            header = ["name","uid","adjust_scale"]
            adjustInfo = csv.DictWriter(adjustfile,header)
            adjustInfo.writeheader()

def html_unescape(dict):
    out_dict = {}
    for key,value in dict.items():
        out_dict.update({ key: html.unescape(str(value)) })
    return out_dict