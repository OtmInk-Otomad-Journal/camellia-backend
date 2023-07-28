import logging
import requests
import math
from lxml import html

def danmuku_time(aid,full_time,sep_time):
    high_index = full_time / 2
    logging.info('获取 av' + str(aid) + ' 视频的起始时间为 ' + str(high_index) + " 秒")
    if full_time - high_index < sep_time:
        high_index = full_time - sep_time * 1.35
        logging.info('获取 av' + str(aid) + ' 视频的起始时间过短，改为前移')
    if high_index < 0:
        high_index = 0
        logging.info('获取 av' + str(aid) + ' 视频的起始时间为负，改为 0 秒开始')
    logging.info('最终获取 av' + str(aid) + ' 视频的起始时间为 ' + str(high_index) + " 秒")
    if full_time < sep_time:
        end_index = full_time
    else:
        end_index = sep_time
    return high_index,end_index