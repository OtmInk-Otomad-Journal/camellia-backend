import csv
import asyncio
import logging
from bilibili_api import video
from program_function import get_img , convert_csv , extract_single_column , get_video , exactVideoLength , average_image_color , brightness_judge
from danmuku_time import danmuku_time
# 声明变量
from config import *

# 获取数据
ranked_list = convert_csv("./data/data.csv")
mainArr = extract_single_column(ranked_list,"aid",main_end)

# 导航导出
ranks = 0
for ranked in ranked_list:
    ranks += 1
    if ranks > main_end + side_end:
        break
    with open(f"./fast_view/bili_{usedTime}.txt","a",encoding="utf-8-sig") as fast:
        fast.write("主榜\n")
        fast.write(f"{ranked['ranking']}\t{ranked['bvid']}\n")
    with open(f"./fast_view/wiki_{usedTime}.txt","a",encoding="utf-8-sig") as fast:
        fast.write("{{"+f'''OtmRanking/brick
                   |ranking={ranked["ranking"]}
                   |title={ranked["title"]}
                   |score={ranked["score"]}
                   |aid={ranked["aid"]}'''+"\n}}\n")
# Pick Up
allArr = []
pickHeader = ["aid","bvid",
              "title","reason","uploader",
              "part","copyright",
              "pubtime","picker",
              'start_time','full_time',
              'web_prefix','video_src','cover_src','avatar_src',
              'theme_color', 'theme_brightness']

with open(f"./data/picked.csv",'w',encoding="utf-8-sig", newline='') as csvWrites:
    writer = csv.DictWriter(csvWrites,pickHeader)
    writer.writeheader()
    async def getInfo(aid,reason,picker):
        pickAllInfo = video.Video(aid=int(aid))
        picked = await pickAllInfo.get_info()
        vid_src = get_video(picked["aid"])
        exact_time = exactVideoLength(vid_src)
        start_time , full_time = danmuku_time(picked["aid"],exact_time,sep_time)
        pic_src = get_img(picked["aid"])
        color_rgb = average_image_color(pic_src["cover"])
        oneArr = {
                "aid": picked["aid"],
                "bvid": picked["bvid"],
                "title": picked["title"],
                "reason": reason,
                "uploader": picked["owner"]["name"],
                "copyright": picked["copyright"],
                "pubtime": time.strftime("%Y/%m/%d %H:%M:%S",time.localtime(int(picked["pubdate"]))),
                "picker": picker,
                'start_time': start_time,
                'full_time': full_time,
                'web_prefix': web_prefix,
                'video_src': vid_src,
                'cover_src': pic_src["cover"],
                'avatar_src': pic_src["avatar"],
                'theme_color': str(color_rgb),
                'theme_brightness': brightness_judge(color_rgb)
                }
        allArr.append(oneArr)
        writer.writerows(oneArr)
        logging.info("一个 Pick Up 作品已记录")
    if os.path.exists("./data/pick.csv"):
        with open("./data/pick.csv",encoding="utf-8-sig",newline='') as csvfile:
            pickInfo = csv.DictReader(csvfile)
            for pick in pickInfo:
                if str(pick["aid"]) in mainArr: # 判断主榜是否已经存在 Pick Up 作品
                    continue
                asyncio.get_event_loop().run_until_complete(getInfo(pick["aid"],
                                                                    pick["reason"],
                                                                    pick["picker"]))
if len(allArr) == 0:
    os.remove(f"./data/picked.csv")

# PICK UP 快速导航
picks = 0
for pickOne in allArr:
    picks += 1
    with open(f"./fast_view/bili_{usedTime}.txt","a",encoding="utf-8-sig") as fast:
        fast.write("Pick Up\n")
        fast.write(f"{picks}\t{pickOne[1]}\n")
    with open(f"./fast_view/wiki_{usedTime}.txt","a",encoding="utf-8-sig") as fast:
        fast.write("{{"+f'''OtmRanking/brick
                   |ranking={picks}
                   |title={pickOne[2]}
                   |score=PICK UP
                   |aid={pickOne[0]}'''+"\n}}\n")