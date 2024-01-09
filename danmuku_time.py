import logging
import numpy as np
from config import *
from lxml import etree

def danmuku_time(aid,full_time,sep_time,full = False,cid = None):
    # 全长度判断
    if full:
        if full_time < sep_time:
            return 0,full_time
        if full_time < max_main_duration:
            return 0,full_time
        else:
            high_index = full_time / 3
            if full_time - high_index > max_main_duration:
                return high_index, max_main_duration
            else:
                return high_index, full_time - high_index

    # 弹幕稀疏计算
    high_danmuku_array = []
    high_enerbar = etree.parse(f'./danmaku/{cid}.xml')
    root = high_enerbar.getroot()
    for element in root.iter():
        if(element.tag == "d"):
            dtime = float(element.attrib["p"].split(",")[0])
            high_danmuku_array.append(dtime)
    if(high_danmuku_array != []):
        split_num = np.ptp(high_danmuku_array) // 2
        if split_num <= 0:
            split_num = 1
        hist = np.histogram(high_danmuku_array,bins=int(split_num),density=True)
        high_index = hist[1][np.argmax(hist[0])]
    else:
        high_index = full_time / 2

    logging.info('获取 av' + str(aid) + ' 视频的起始时间为 ' + str(high_index) + " 秒")
    if full_time - high_index < sep_time * 2.5:
        high_index = full_time - sep_time * 2.5
        logging.info('获取 av' + str(aid) + ' 视频的起始时间过短，改为前移')
    if high_index < 0:
        high_index = full_time / 2
        logging.info('获取 av' + str(aid) + ' 视频的起始时间为负，改为中间开始')
    if full_time / 2 < sep_time:
        high_index = 0
        logging.info('获取 av' + str(aid) + ' 视频的起始时间为 0')
        end_index = full_time
    else:
        end_index = sep_time
    logging.info('最终获取 av' + str(aid) + ' 视频的起始时间为 ' + str(high_index) + " 秒")
    return high_index,end_index