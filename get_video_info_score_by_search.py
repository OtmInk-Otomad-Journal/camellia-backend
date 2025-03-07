import json
import logging
import time
import asyncio
import datetime

from get_video_info_score_struct import DateYield

from bilibili_api import search

time_wait = 2


async def fetch(keyword: str, page, begin, end, attempt=False):

    for retry in range(10):
        try:
            result = await search.search_by_type(
                keyword,
                search.SearchObjectType.VIDEO,
                search.OrderVideo.PUBDATE,
                time_start=begin,
                time_end=end,
                page=page,
            )

            if "v_voucher" in result or (not attempt and "result" not in result):
                logging.warning(f"数据获取失败，第 { retry } 次重试")
                await asyncio.sleep(60)
                continue
            return result
        except Exception as e:
            logging.error(e)
            logging.warning(f"数据获取失败，第 { retry } 次重试")
            await asyncio.sleep(60)
            continue
    return None


async def get_data_by_search(
    search_list: list, src_date_str: str, dst_date_str: str
) -> list:
    data = []
    logging.info("依据搜索结果拉取数据")

    for keyword in search_list:
        logging.info(f"拉取 { keyword } 搜索结果")
        logging.info(f"正在拉取 {src_date_str} ~ {dst_date_str} 的数据...")
        begin = datetime.datetime.strptime(src_date_str, "%Y%m%d").strftime("%Y-%m-%d")
        end = (
            datetime.datetime.strptime(dst_date_str, "%Y%m%d")
            + datetime.timedelta(days=1)
        ).strftime("%Y-%m-%d")
        pages = (await fetch(keyword, 1, begin, end, True))["numPages"]
        await asyncio.sleep(time_wait)

        for page in range(1, pages + 1):
            result = await fetch(keyword, page, begin, end)
            if not result:
                break
            try:
                now = result["result"]
            except Exception as e:
                print(result)
            for video in now:
                video["title"] = (
                    video["title"]
                    .replace('<em class="keyword">', "")
                    .replace("</em>", "")
                )
                video["tid"] = 0
                video["tag"] = video["tag"].lower().split(",")
                video["pubdate"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(video["pubdate"])
                )
            data += now
            logging.info(f"第 {page} 页完成")
            await asyncio.sleep(time_wait)

    return data
