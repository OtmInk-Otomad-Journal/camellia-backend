from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
import logging
import threading
import os
import time
import ffmpeg
import json
import hashlib
from tqdm import tqdm
from program_function import audio_process

def pack_video(sv,sa,op,rf):
    ffmpeg.output(sv,sa,op,**rf).run()

def render_video(data,url,audio = None,fast = False):
    from config import render_max_threading_count, fps, screen_size ,sequence_num_width, render_fast_threading_count, slip_second, render_format, muitl_limit

    start_time = data["start_time"]
    full_duration = data["full_time"]
    output_file = data["output_src"]
    identify_code = hashlib.md5(str(data).encode()).hexdigest()
    audio_file = audio_process(data["aid"],float(start_time)*1000,float(full_duration)*1000,audio)

    logging.info(f"启动进程 {identify_code}")
    max_threading_count = render_max_threading_count

    all_frame = int(float(full_duration) * fps)

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
            # opt.add_argument("--disable-extensions")
            # opt.add_argument("--disable-software-rasterizer")
            # opt.add_argument('--no-sandbox')
            # opt.add_argument('--ignore-certificate-errors')
            # opt.add_argument('--allow-running-insecure-content')
            driver = webdriver.Edge(service=ChromeService(executable_path="./driver/chromedriver.exe"),options=opt)
            driver.get(url)
            driver.set_window_size(screen_size[0],screen_size[1])
            time.sleep(2)
            driver.execute_script(f"inject({json_info})")

            # 持续刷新保证视频产出。
            driver.execute_script(f"seek_frame({frames[0]},{fps},{start_time})")
            time.sleep(2)
            for y in range(1):
                for fresh in range(0,len(frames),15):
                    driver.execute_script(f"seek_frame({int(frames[0])+fresh},{fps},{start_time})")
            time.sleep(2)

            for s_frame in frames:
                if not os.path.exists(f"./temp/{identify_code}_{str(s_frame).zfill(sequence_num_width)}.png"): # 断点续渲
                    driver.execute_script(f"seek_frame({s_frame},{fps},{start_time})")
                    # stat = driver.execute_script(f"return check_status()")
                    # while(not stat):
                    #     print(stat)
                    #     time.sleep(0.01)
                    #     driver.execute_script(f"return check_status()")
                    # time.sleep(0.1)
                    # driver.execute_script(f"myVideo.currentTime = {frame / fps}")
                    driver.get_screenshot_as_file(f"./temp/{identify_code}_{str(s_frame).zfill(sequence_num_width)}.png")
                render_progress.update(1)

        # 逐帧截图以获取序列
        if fast:
            threading_count = render_fast_threading_count
        else:
            threading_count = int(float(full_duration) // slip_second) + 1
            if threading_count >= max_threading_count:
                threading_count = max_threading_count
        for frame_list in split_list_n_list(range(all_frame),threading_count):
            render_single = threading.Thread(target=render_frame,args=[frame_list])
            render_single.start()
            render_quene.append(render_single)

        for pause in render_quene:
            pause.join()
        # 序列合成为视频

    logging.info("视频序列合成完成")

    sequence_video = ffmpeg.input(f"temp/{identify_code}_%0{sequence_num_width}d.png",framerate=fps)
    # if audio != None:
    sequence_audio = ffmpeg.input(audio_file)
    # else:
    #     sequence_audio = ffmpeg.input(video_file,ss=start_time,t=full_duration).audio
    #     sequence_audio = sequence_audio.filter("afade",t="in",d=1)
    #     sequence_audio = sequence_audio.filter("afade",t="out",st=float(full_duration)-1,d=1)
    pack_video(sequence_video,sequence_audio,output_file,render_format)

    logging.info("视频渲染完成")

    for remove_num in range(all_frame):
        os.remove(f"./temp/{identify_code}_{str(remove_num).zfill(sequence_num_width)}.png")

    muitl_limit.release()