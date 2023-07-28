import csv
import asyncio
import logging
from bilibili_api import video
from program_function import get_img , convert_csv , extract_single_column

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

# 主榜封面 & 头像下载
ranking = 0
while(ranking < main_end + side_end):
    vid = ranked_list[ranking]
    get_img(vid["aid"])
    ranking += 1

# Pick Up

allArr = []
pickHeader = ["aid","bvid",
              "title","reason","uploader",
              "part","copyright",
              "pubtime","full_time","picker"]

# 此处代码有待商榷！暂时不会考虑 Pick Up 的修改。
# 此处代码有待商榷！暂时不会考虑 Pick Up 的修改。
# 此处代码有待商榷！暂时不会考虑 Pick Up 的修改。

with open(f"./data/picked.csv",'w',encoding="utf-8-sig", newline='') as csvWrites:
    writer = csv.writer(csvWrites)
    writer.writerow(pickHeader)
    async def getInfo(aid,reason,picker):
        pickAllInfo = video.Video(aid=int(aid))
        picked = await pickAllInfo.get_info()
        timed = time.strftime("%Y/%m/%d %H:%M:%S",time.localtime(int(picked["pubdate"])))
        oneArr = [picked["aid"],
                  picked["bvid"],
                  picked["title"],
                  reason,
                  picked["owner"]["name"],
                  "1",
                  picked["copyright"],
                  timed,
                  picked["duration"],
                  picker]
        allArr.append(oneArr)
        writer.writerow(oneArr)
        logging.info("一个 Pick Up 作品已记录")
        # 下载头像
        get_img(picked["aid"])
    if os.path.exists("./custom/pick.csv"):
        with open("custom/pick.csv",encoding="utf-8-sig",newline='') as csvfile:
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