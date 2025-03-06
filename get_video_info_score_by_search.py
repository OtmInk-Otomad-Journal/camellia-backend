import logging
import time
import aiohttp
import asyncio
import datetime

import urllib

from get_video_info_score_struct import DateYield

time_wait = 2


async def fetch(
    session, keyword: str, page, begin, end, cookie_raw: str, attempt=False
):

    query_url = """https://api.bilibili.com/x/web-interface/search/type?category_id=&search_type=video&ad_resource=5654&__refresh__=true&_extra=&context=&page={}&page_size=50&order=pubdate&pubtime_begin_s={}&pubtime_end_s={}&from_source=&from_spmid=333.337&platform=pc&highlight=1&single_column=0&keyword={}&source_tag=3&gaia_vtoken=&dynamic_offset=30&page_exp=0"""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Cookie": cookie_raw,
    }

    for retry in range(10):
        try:
            async with session.get(
                query_url.format(page, begin, end, urllib.parse.quote(keyword)),
                headers=headers,
            ) as response:
                result = await response.json()
            if "v_voucher" in result["data"] or (
                not attempt and "result" not in result["data"]
            ):
                logging.warning(f"数据获取失败，第 { retry } 次重试")
                await asyncio.sleep(60)
                continue
            return result["data"]
        except Exception as e:
            logging.error(e)
            logging.warning(f"数据获取失败，第 { retry } 次重试")
            await asyncio.sleep(60)
            continue
    return None


async def get_data_by_search(
    search_list: list, data_yield: DateYield, cookie_raw: str
) -> list:
    data = []
    logging.info("依据搜索结果拉取数据")

    async with aiohttp.ClientSession() as session:
        for keyword in search_list:
            logging.info(f"拉取 { keyword } 搜索结果")
            for src_date_str, dst_date_str in data_yield:
                logging.info(f"正在拉取 {src_date_str} ~ {dst_date_str} 的数据...")
                begin = int(
                    datetime.datetime.strptime(src_date_str, "%Y%m%d").timestamp()
                )
                end = int(
                    (
                        datetime.datetime.strptime(dst_date_str, "%Y%m%d")
                        + datetime.timedelta(days=1)
                    ).timestamp()
                )
                pages = (
                    await fetch(session, keyword, 1, begin, end, cookie_raw, True)
                )["numPages"]
                await asyncio.sleep(time_wait)

                for page in range(1, pages + 1):
                    result = await fetch(session, keyword, page, begin, end, cookie_raw)
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
