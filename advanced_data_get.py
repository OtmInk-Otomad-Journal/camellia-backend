import csv
import logging
from config import *
from get_video_info_score import aid_to_score_norm, selected_video_stat, all_video_info
from program_function import check_dir , get_img , get_video , calc_color , exactVideoLength , html_unescape
from danmuku_time import danmuku_time

# 新建不存在的文件夹
check_dir()

# 预先黑名单
blackArr = []
with open("option/blacklist.csv",encoding="utf-8-sig",newline='') as blackfile:
    blackInfo = csv.DictReader(blackfile)
    for bl in blackInfo:
        blackArr.append(int(bl["aid"]))

# 预先内容系数调整
adjust_dic = {}
with open("option/adjust.csv",encoding="utf-8-sig",newline='') as adjustfile:
    adjustInfo = csv.DictReader(adjustfile)
    for adj in adjustInfo:
        adjust_dic[int(adj["uid"])] = adj["adjust_scale"]

co_header = ['ranking','score',
             'aid','bvid',
             'title','uploader','copyright',
             'play','like','coin','star',
             'pubtime',
             'adjust_scale',
             'part','duration','start_time','full_time',
             'web_prefix','video_src','cover_src','avatar_src',
             'light_color', 'dark_color']

logging.info('生成 CSV 信息表格')

with open("data/data.csv","w",encoding="utf-8-sig",newline='') as csvfile:
    writer = csv.DictWriter(csvfile,co_header)
    writer.writeheader()
    vid_list = []
    for video_aid, video_info in all_video_info.items():
        video_stat = selected_video_stat.get(video_aid, {})
        if int(video_aid) in blackArr:
            continue
        normk = adjust_dic.get(int(video_info["mid"]), 1)
        norm_score = float('%.3f' % (aid_to_score_norm[video_aid] * float(normk)))
        vid_list.append({
            "score": norm_score,
            "aid": str(video_aid),
            "bvid": str(video_info["bvid"]),
            "title": str(video_info["title"]),
            "uploader": str(video_info["author"]),
            "copyright": str(video_stat.get("copyright","未取得")),
            "play": str(video_info["play"]),
            "like": str(video_stat.get("like", "未取得")),
            "coin": str(video_stat.get("coin", "未取得")),
            "star": str(video_info["favorites"]),
            "pubtime": str(video_info["pubdate"]),
            "adjust_scale": str(normk),
            "part": '1',
            "duration": '未取得',
            "start_time": '未取得',
            "full_time": '未取得',
            "web_prefix": '未取得',
            "video_src": '未取得',
            "avatar_src": '未取得',
            "cover_src": '未取得', #str(video_info["pic"]),
            "light_color": '未取得',
            "dark_color": '未取得'
        })
    vid_list = sorted(vid_list,key=lambda x:float(x["score"]),reverse=True) # 排序
    ranking = 0
    ranked_list = []
    for vid in vid_list:
        vid = html_unescape(vid)
        ranking += 1
        after_dict = { "ranking": ranking }
        if ranking <= main_end + side_end + 15:
            try:
                pic_src = get_img(vid["aid"]) # 存在获取失败的可能，于是可以选择跳过。
            except:
                ranking -= 1
                continue
            color_rgb = calc_color(pic_src["cover"])
            after_dict.update({
                "avatar_src": pic_src["avatar"],
                "cover_src": pic_src["cover"],
                "light_color": str(color_rgb[0]),
                "dark_color": str(color_rgb[1]),
                "web_prefix": web_prefix
                })
            if ranking <= main_end + 5:
                vid_src = get_video(vid["aid"])
                exact_time = exactVideoLength(vid_src)
                full = False
                if ranking == 1:
                    full = True
                start_time , full_time = danmuku_time(vid["aid"],exact_time,sep_time,full=full)
                after_dict.update({ "video_src" : vid_src,
                                    "duration" : full_time,
                                    "start_time": start_time,
                                    "full_time" : full_time})
        vid.update(after_dict)
        ranked_list.append(vid)
    print(ranked_list)
    writer.writerows(ranked_list)