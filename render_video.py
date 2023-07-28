from selenium import webdriver
from selenium.webdriver.chrome.service import Service as EdgeService
from webdriver_manager.chrome import EdgeDriverManager
import random
import logging
import threading
import os
import time
import ffmpeg
from tqdm import tqdm
from config import *

def render_video(data,url):
    start_time = data["start_time"]
    full_duration = data["full_time"]
    video_file = data["video_src"]
    output_file = data["output_src"]
    identify_code = str(random.randint(0,99999)).zfill(5)

    logging.info(f"启动进程 {identify_code}")

    max_threading_count = 100

    all_frame = full_duration * fps

    render_quene = []
    with tqdm(total=all_frame) as render_progress:
        def split_list_n_list(origin_list, n):
            if len(origin_list) % n == 0:
                cnt = len(origin_list) // n
            else:
                cnt = len(origin_list) // n + 1
            for i in range(0, n):
                yield origin_list[i*cnt:(i+1)*cnt]

        def render_frame(frames):
            global complete_frame
            opt = webdriver.EdgeOptions()
            opt.add_argument("--headless")
            opt.add_argument("--enable-webgl")
            opt.add_argument("--allow-file-access-from-files")
            # ChromeDriverManager().install()
            driver = webdriver.Edge(service=EdgeService(),options=opt)
            driver.get(url)
            driver.set_window_size(screen_size[0],screen_size[1])
            time.sleep(1)
            for s_frame in frames:
                driver.execute_script(f"seek_frame({s_frame},{fps},{start_time})")
                # driver.execute_script(f"myVideo.currentTime = {frame / fps}")
                driver.get_screenshot_as_file(f"./temp/{identify_code}_{str(s_frame).zfill(sequence_num_width)}.png")
                complete_frame += 1
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
    sequence_audio = ffmpeg.input(video_file,ss=start_time,t=full_duration).audio
    ffmpeg.output(sequence_video,sequence_audio,output_file,**render_format).run()

    logging.info("视频渲染完成")

    for remove_num in all_frame:
        os.remove(f"./temp/{identify_code}_{str(remove_num).zfill(sequence_num_width)}.png")