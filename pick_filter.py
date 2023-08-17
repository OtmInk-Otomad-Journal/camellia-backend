import csv
import webbrowser
import tkinter
import datetime
import os
import shutil
from program_function import turnAid



with open("./data/pick.csv","r",encoding="utf-8-sig",newline='') as csvfile:
    listed = csv.DictReader(csvfile)
    min_time = datetime.datetime.today() + datetime.timedelta(days=-8)
    with open("./data/pick_filtered.csv","w",encoding="utf-8-sig",newline='') as csvwrite:
        writeheader = ["aid","reason","picker","owner"]
        writefile = csv.DictWriter(csvwrite,writeheader)
        writefile.writeheader()
        # PICK UP 获取
        for item in listed:
            time = item["提交时间（自动）"]
            realtime = datetime.datetime.strptime(time,"%Y/%m/%d %H:%M:%S")
            if realtime < min_time:
                continue
            aid = turnAid(str(item["推荐作品 av 号 / BV 号（必填）"]))
            picker = item["推荐人"]
            if picker == "":
                picker = "神秘人"
            url = f"https://www.bilibili.com/video/av{aid}"

            webbrowser.open(url, new=0, autoraise=True) # 启动浏览器以浏览

            top = tkinter.Tk()
            top.title("音之墨小周刊 Pick Up 简要过滤")
            def tickCommand(root):
                writefile.writerow({
                    "aid": aid,
                    "reason": text,
                    "picker": picker
                })
                root.destroy()
            def noCommand(root):
                root.destroy()
            # 推荐标题
            text_title = tkinter.Label(text=picker,font=("HarmonyOS Sans SC Bold",20),justify='left',pady=10)
            text_title.pack()
            # 推荐理由显示
            text = item["推荐理由（必填）"]
            textShow = tkinter.Text(font=("HarmonyOS Sans SC",12))
            textShow.insert('1.0',f"{text}")
            textShow.pack()
            tickButton = tkinter.Button(text="选择",font=("HarmonyOS Sans SC",20),command = lambda: tickCommand(top))
            noButton = tkinter.Button(text="废弃",font=("HarmonyOS Sans SC",20),command = lambda: noCommand(top))
            tickButton.pack(side='left',padx=50,pady=10)
            noButton.pack(side='right',padx=50,pady=10)
            top.mainloop()

os.system("python advanced_resource_get.py")