import os
import subprocess
import hashlib
import json
import logging
from program_function import VideoChunk, audio_process, video_cut, video_merge
from config import muitl_limit

def render_video(data, url, audio=None, fast=False):
    with muitl_limit:
        start_time = data["start_time"]
        full_duration = data["full_time"]
        if not fast:
            logging.info(f"正在裁剪 av{data['aid']} 视频...")
            video_chunks = video_cut(data["aid"], float(start_time), float(full_duration))
        else:
            video_chunks = [VideoChunk(
                start_time=float(start_time),
                render_start_time=0,
                duration=float(full_duration),
                front_reserved_time=0,
                back_reserved_time=0,
                filepath=""
            )]
        logging.info("正在处理音频...")
        audio_file = audio_process(
            data["aid"], float(start_time) * 1000, float(full_duration) * 1000, audio
        )

        merge_list: list[VideoChunk] = []

        final_output_src = data["output_src"]

        for vid_chunk in video_chunks:
            output_src = final_output_src.replace(".mp4", f"_part_{int(vid_chunk.render_start_time)}.mp4")
            logging.info(f"裁剪视频片段: {vid_chunk.filepath} (渲染起始时间: {vid_chunk.render_start_time}, 时长: {vid_chunk.duration}), 输出至: {output_src}")
            data.update({
                         "url": url,
                         "video_src": vid_chunk.filepath,
                         "start_time": vid_chunk.render_start_time,
                         "chunk_time": vid_chunk.duration,
                         "front_reserved_time": vid_chunk.front_reserved_time,
                         "back_reserved_time": vid_chunk.back_reserved_time,
                         "output_src": output_src
                        })

            identify_code = hashlib.md5(str(data).encode()).hexdigest()
            json_name = f"./temp/{identify_code}.json"
            with open(json_name, "w", encoding="utf-8-sig") as temp_json:
                json.dump(data, temp_json)
            if os.path.exists(output_src):
                os.remove(output_src)  # 必须重新生成，防止出错
            command = ["node", "wvc_render.js", json_name]
            logging.info("转交 Node.js 渲染")

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                text=True,
                encoding="utf-8-sig",
            )

            for info in iter(process.stdout.readline, "b"):
                if process.poll() is not None:
                    break
                if len(info) != 0:
                    logging.info(info.replace("\n", ""))

            merge_list.append(VideoChunk(
                start_time=vid_chunk.start_time,
                render_start_time=vid_chunk.render_start_time,
                duration=vid_chunk.duration,
                front_reserved_time=vid_chunk.front_reserved_time,
                back_reserved_time=vid_chunk.back_reserved_time,
                filepath=output_src))
        
        # 合并音频和视频片段
        logging.info("正在合并视频片段和音频...")
        video_merge(merge_list, audio_file, final_output_src)

        logging.info(f"渲染完成，输出文件: {final_output_src}")

        if not os.path.exists(final_output_src):
            raise Exception(f"{final_output_src} 渲染失败，未生成输出文件，请检查日志。")

        # 清理切片文件
        for merge_chunk in merge_list:
            if os.path.exists(merge_chunk.filepath):
                os.remove(merge_chunk.filepath)
