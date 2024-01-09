from moviepy.editor import *
import os
import shutil
import ffmpeg
import csv
from program_function import convert_csv
from config import *

filePath = f"./output/clip/{usedTime}"
tempPath = f"./temp"

def duration(file,offset):
    return float(ffmpeg.probe(file)["streams"][0]["duration"]) + offset

def ffVideo(file):
    vi = ffmpeg.input(file,**read_format)
    viv = vi.video
    aud = vi.audio
    return [viv,aud]

def inVideo(file):
    name = file.split("/")[-1]
    vi = ffmpeg.input(file,**read_format)
    viv = vi.filter("fade",st=0,d=0.5)
    if not os.path.exists(f"{tempPath}/{name}"):
        ffmpeg.output(viv,f"{tempPath}/{name}",**render_format).run()
    viw = ffmpeg.input(f"{tempPath}/{name}",**read_format)
    aud = vi.audio
    return [viw,aud]

def inoutVideo(file):
    name = file.split("/")[-1]
    vi = ffmpeg.input(file,**read_format)
    viv = vi.filter("fade",st=0,d=0.5)
    viv = viv.filter("fade",t="out",st=duration(file,-0.5),d=0.5)
    if not os.path.exists(f"{tempPath}/{name}"):
        ffmpeg.output(viv,f"{tempPath}/{name}",**render_format).run()
    viw = ffmpeg.input(f"{tempPath}/{name}",**read_format)
    aud = vi.audio
    return [viw,aud]

def outVideo(file):
    name = file.split("/")[-1]
    vi = ffmpeg.input(file,**read_format)
    viv = vi.filter("fade",t="out",st=duration(file,-0.5),d=0.5)
    if not os.path.exists(f"{tempPath}/{name}"):
        ffmpeg.output(viv,f"{tempPath}/{name}",**render_format).run()
    viw = ffmpeg.input(f"{tempPath}/{name}",**read_format)
    aud = vi.audio
    return [viw,aud]

def AllVideo(main_end):
    AllArr = []
    AllArr.append(ffVideo("./template/opening/ViewOpening.mp4"))
    if not os.path.exists(filePath):
        os.mkdir(filePath)
    # AllArr.append(inVideo("./template/pass/passMain.mp4"))

    for clips in range(main_end,1,-1):
        AllArr.append(ffVideo(f"./output/clip/ViewRank_{clips}.mp4"))
        AllArr.append(ffVideo("./template/pass/pass.mp4"))
    AllArr.append(ffVideo(f"./output/clip/ViewRank_1.mp4"))
    AllArr.append(ffVideo(f"./template/opening/ViewEnding.mp4"))

    onum = 0
    for items in AllArr:
        onum += 1
        if onum == 1:
            combVideo = items
            continue
        combVideo = ffmpeg.concat(combVideo[0],combVideo[1],items[0],items[1],v=1,a=1).node
    ffmpeg.output(combVideo[0],combVideo[1],f'./output/final/ViewPick_{usedTime}.mp4',**all_render_format).run()
    for clips in range(main_end,0,-1):
        shutil.move(f"./output/clip/ViewRank_{clips}.mp4",f"{filePath}/ViewRank_{clips}.mp4")
    for curDir, dirs, files in os.walk(f"{tempPath}"):
        for temp_f in files:
            os.remove(f"{tempPath}/{temp_f}")

ranked_list = convert_csv("data/viewpicked.csv")

AllVideo(len(ranked_list))