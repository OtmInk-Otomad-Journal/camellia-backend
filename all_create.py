import logging
from moviepy import *
import os
import shutil
import ffmpeg
import csv

from config import read_format, usedTime, render_format, insert_count, all_render_format

tempPath = f"./temp"


def duration(file, offset):
    return float(ffmpeg.probe(file)["streams"][0]["duration"]) + offset


def ffVideo(file):
    vi = ffmpeg.input(file, **read_format)
    viv = vi.video
    aud = vi.audio
    return [viv, aud]


def inVideo(file):
    name = file.split("/")[-1]
    vi = ffmpeg.input(file, **read_format)
    viv = vi.filter("fade", st=0, d=0.5)
    if not os.path.exists(f"{tempPath}/{name}"):
        ffmpeg.output(viv, f"{tempPath}/{name}", **render_format).run()
    viw = ffmpeg.input(f"{tempPath}/{name}", **read_format)
    aud = vi.audio
    return [viw, aud]


def inoutVideo(file):
    name = file.split("/")[-1]
    vi = ffmpeg.input(file, **read_format)
    viv = vi.filter("fade", st=0, d=0.5)
    viv = viv.filter("fade", t="out", st=duration(file, -0.5), d=0.5)
    if not os.path.exists(f"{tempPath}/{name}"):
        ffmpeg.output(viv, f"{tempPath}/{name}", **render_format).run()
    viw = ffmpeg.input(f"{tempPath}/{name}", **read_format)
    aud = vi.audio
    return [viw, aud]


def outVideo(file):
    name = file.split("/")[-1]
    vi = ffmpeg.input(file, **read_format)
    viv = vi.filter("fade", t="out", st=duration(file, -0.5), d=0.5)
    if not os.path.exists(f"{tempPath}/{name}"):
        ffmpeg.output(viv, f"{tempPath}/{name}", **render_format).run()
    viw = ffmpeg.input(f"{tempPath}/{name}", **read_format)
    aud = vi.audio
    return [viw, aud]


def AllVideo(main_end, pickArr):
    logging.info(f"进入视频总合成环节")
    filePath = f"./output/clip/{usedTime}"

    if not os.path.exists(filePath):
        os.mkdir(filePath)
    else:
        times = 2
        while os.path.exists(filePath + "_" + str(times)):
            times += 1
        filePath = filePath + "_" + str(times)
        os.mkdir(filePath)
    with open("./data/data.csv", "r", encoding="utf-8-sig") as csvfile:
        reader = csv.reader(csvfile)
        main_rank_column = [row[0] for row in reader]
    AllArr = []
    trueFiles = []
    for curDir, dirs, files in os.walk("./option/ads"):
        for ads in files:
            AllArr.append(inoutVideo(f"./option/ads/{ads}"))
            trueFiles.append(ads)

    AllArr.append(inoutVideo("./output/clip/Calendar.mp4"))

    AllArr.append(ffVideo("./template/opening/opening.mp4"))

    AllArr.append(inVideo("./template/pass/passMain.mp4"))

    for clips in range(main_end, insert_count + 1, -1):
        rank_src = main_rank_column[clips]
        AllArr.append(ffVideo(f"./output/clip/MainRank_{rank_src}.mp4"))
        AllArr.append(ffVideo("./template/pass/pass.mp4"))
    rank_src = main_rank_column[insert_count + 1]
    AllArr.append(ffVideo(f"./output/clip/MainRank_{rank_src}.mp4"))

    # Pick Up

    if pickArr != []:
        AllArr.append(ffVideo("./template/pass/passPick.mp4"))
        for clipsto in range(1, len(pickArr)):
            AllArr.append(ffVideo(f"./output/clip/PickRank_{clipsto}.mp4"))
            AllArr.append(ffVideo("./template/pass/pass.mp4"))
    if os.path.exists("./option/canbin.mp4"):
        if len(pickArr) != 0:
            AllArr.append(outVideo(f"./output/clip/PickRank_{len(pickArr)}.mp4"))
        else:
            # AllArr[-1] = ffmpeg.filter(AllArr[-1],"fade",t="out",st="d-0.5",d=0.5,alpha=1)
            pass
        AllArr.append(inoutVideo("./template/pass/passCanbin.mp4"))
        AllArr.append(inoutVideo("./option/canbin.mp4"))
        AllArr.append(inVideo("./template/pass/passMain.mp4"))
    else:
        if pickArr != []:
            AllArr.append(ffVideo(f"./output/clip/PickRank_{len(pickArr)}.mp4"))
            AllArr.append(ffVideo("./template/pass/passMain.mp4"))
        else:
            AllArr.append(ffVideo("./template/pass/pass.mp4"))

    # 倒数主榜

    for clips in range(insert_count, 1, -1):
        rank_src = main_rank_column[clips]
        AllArr.append(ffVideo(f"./output/clip/MainRank_{rank_src}.mp4"))
        AllArr.append(ffVideo("./template/pass/pass.mp4"))
    rank_src = main_rank_column[1]
    AllArr.append(ffVideo(f"./output/clip/MainRank_{rank_src}.mp4"))

    onum = 0
    for items in AllArr:
        onum += 1
        if onum == 1:
            combVideo = items
            continue
        combVideo = ffmpeg.concat(
            combVideo[0], combVideo[1], items[0], items[1], v=1, a=1
        ).node

    if os.path.exists(f"./output/final/Rank_{usedTime}.mp4"):
        logging.warning(f"Rank_{usedTime}.mp4 已存在，本次合成将覆盖该文件。")
        os.remove(f"./output/final/Rank_{usedTime}.mp4")

    logging.info(f"正在渲染 Rank_{usedTime}.mp4 ...")
    ffmpeg.output(
        combVideo[0],
        combVideo[1],
        f"./output/final/Rank_{usedTime}.mp4",
        **all_render_format,
    ).run()
    logging.info(f"Rank_{usedTime}.mp4 渲染完成！")
    logging.info(f"正在转移文件至 {usedTime} 文件夹中...")
    if os.path.exists("./option/canbin.mp4"):
        shutil.move("./option/canbin.mp4", f"{filePath}/canbin_{usedTime}.mp4")
    for clips in range(main_end, 0, -1):
        rank_src = main_rank_column[clips]
        shutil.move(
            f"./output/clip/MainRank_{rank_src}.mp4",
            f"{filePath}/MainRank_{rank_src}.mp4",
        )
    for clipsto in range(1, len(pickArr) + 1):
        shutil.move(
            f"./output/clip/PickRank_{clipsto}.mp4",
            f"{filePath}/PickRank_{clipsto}.mp4",
        )
    shutil.move("./output/clip/Calendar.mp4", f"{filePath}/Calendar.mp4")
    logging.info(f"转移完成！")
    logging.info(f"正在清理文件...")
    for curDir, dirs, files in os.walk(f"{tempPath}"):
        for temp_f in files:
            os.remove(f"{tempPath}/{temp_f}")
    # os.remove("./time.txt")
    if os.path.exists("./data/picked.csv"):
        os.remove("./data/picked.csv")
        logging.warning("没有检测到 picked.csv 文件，请确认是否遗漏了 Pick Up 环节！")
    logging.info(f"文件清理完毕！")
