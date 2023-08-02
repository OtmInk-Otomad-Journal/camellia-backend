from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import random
import logging
import threading
import os
import time
import ffmpeg
import json
from tqdm import tqdm
from config import *

def render_video(data,url,audio = None):
    start_time = data["start_time"]
    full_duration = data["full_time"]
    if audio != None:
        audio_file = data["audio_src"]
    video_file = data["video_src"]
    output_file = data["output_src"]
    identify_code = str(random.randint(0,99999)).zfill(5)

    logging.info(f"启动进程 {identify_code}")

    max_threading_count = 2

    all_frame = int(float(full_duration)) * fps

    render_quene = []

    json_info = json.dumps(data)
    with tqdm(total=all_frame) as render_progress:
        def split_list_n_list(origin_list, n):
            if len(origin_list) % n == 0:
                cnt = len(origin_list) // n
            else:
                cnt = len(origin_list) // n + 1
            for i in range(0, n):
                yield origin_list[i*cnt:(i+1)*cnt]

        def render_frame(frames):
            opt = webdriver.ChromeOptions()
            opt.add_argument("--headless")
            opt.add_argument("--enable-webgl")
            opt.add_argument("--allow-file-access-from-files")
            opt.add_argument("--disable-extensions")
            opt.add_argument("--disable-software-rasterizer")
            opt.add_argument('--no-sandbox')
            opt.add_argument('--ignore-certificate-errors')
            opt.add_argument('--allow-running-insecure-content')
            # ChromeDriverManager().install()
            driver = webdriver.Edge(service=ChromeService(),options=opt)
            driver.get(url)
            driver.set_window_size(screen_size[0],screen_size[1])
            time.sleep(2)
            driver.execute_script(f"inject({json_info})")
            driver.execute_script(f"seek_frame({frames[0]},{fps},{start_time})")
            time.sleep(7.5)
            for s_frame in frames:
                driver.execute_script(f"seek_frame({s_frame},{fps},{start_time})")
                # time.sleep(0.1)
                # driver.execute_script(f"myVideo.currentTime = {frame / fps}")
                driver.get_screenshot_as_file(f"./temp/{identify_code}_{str(s_frame).zfill(sequence_num_width)}.png")
                render_progress.update(1)

        # 逐帧截图以获取序列
        for frame_list in split_list_n_list(range(all_frame),max_threading_count):
            render_single = threading.Thread(target=render_frame,args=[frame_list])
            render_single.start()
            render_quene.append(render_single)

        for pause in render_quene:
            pause.join()
        # 序列合成为视频

    logging.info("视频序列合成完成")

    sequence_video = ffmpeg.input(f"temp/{identify_code}_%0{sequence_num_width}d.png",framerate=fps)
    if audio != None:
        sequence_audio = ffmpeg.input(audio_file,t=full_duration)
    else:
        sequence_audio = ffmpeg.input(video_file,ss=start_time,t=full_duration).audio
    ffmpeg.output(sequence_video,sequence_audio,output_file,**render_format).run()

    logging.info("视频渲染完成")

    for remove_num in range(all_frame):
        os.remove(f"./temp/{identify_code}_{str(remove_num).zfill(sequence_num_width)}.png")

    muitl_limit.release()

# # 临时用作测试用。
# render_video(data={'score': 3.531, 'aid': '273559420', 'bvid': 'BV1UF411Q7WN', 'title': '道化師協奏会 ～Concert of McDonald～', 'uploader': 'yumeki335', 'copyright': '1', 'play': '3883', 'like': '738', 'coin': '370', 'star': '573', 'pubtime': '2023-07-19 23:30:00', 'adjust_scale': '1', 'part': '1', 'duration': 20, 'start_time': 387.0333125, 'full_time': 20, 'web_prefix': 'http://localhost:7213/', 'video_src': './video/273559420.mp4', 'avatar_src': './avatar/273559420.png', 'cover_src': './cover/273559420.png', 'theme_color': '(239, 73, 47)', 'theme_brightness': 'dark', 'ranking': 8 ,'output_src': 'MainRank_3.mp4'},url="http://127.0.0.1:5173/main")