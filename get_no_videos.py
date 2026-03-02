import os
from program_function import convert_csv

pickInfo = convert_csv("./data/viewpick.csv")

no_list = []

for pick in pickInfo:
    if os.path.exists(f"./video/{pick['aid'].replace('av','')}.mp4"):
        continue
    no_list.append(pick['aid'])

print(no_list)