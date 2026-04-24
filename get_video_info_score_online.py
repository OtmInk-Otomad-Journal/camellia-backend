import os
import asyncio
import datetime
import logging
from typing import Dict, Any, List

import aiohttp

from config import delta_days, range_days

logging.basicConfig(
	level=logging.DEBUG,
	format="[%(asctime)s] %(levelname)s@%(funcName)s: %(message)s",
	encoding="utf-8",
)


def _to_tag_list(raw_tags: Any) -> List[str]:
	if isinstance(raw_tags, list):
		return [str(tag).strip().lower() for tag in raw_tags if str(tag).strip()]
	if isinstance(raw_tags, str):
		return [tag.strip().lower() for tag in raw_tags.split(",") if tag.strip()]
	return []


def _normalize_video(video: Dict[str, Any]) -> Dict[str, Any]:
	item = dict(video)
	if "tag" not in item and "tags" in item:
		item["tag"] = _to_tag_list(item.get("tags"))
	elif "tag" in item:
		item["tag"] = _to_tag_list(item.get("tag"))
	else:
		item["tag"] = []
	
	# review 字段可能为 null
	if "review" in item and item["review"] is None:
		item["review"] = 0

	# favorites 字段可能为 null
	if "favorites" in item and item["favorites"] is None:
		item["favorites"] = 0

	# aid 设为 id
	if "aid" in item and "id" not in item:
		item["id"] = item["aid"]

	# created_at 从 2026-03-09T21:13:25.000Z 转为 YYYY-MM-DD HH:MM:SS 格式
	if "created_at" in item and isinstance(item["created_at"], str):
		try:
			created_at_dt = datetime.datetime.fromisoformat(item["created_at"].rstrip("Z"))
			item["created_at"] = created_at_dt.strftime("%Y-%m-%d %H:%M:%S")
		except ValueError:
			logging.warning(f"无法解析 created_at 字段: {item['created_at']}")

	return item


async def _fetch_one_page(
	session: aiohttp.ClientSession,
	url: str,
	from_time: str,
	to_time: str,
	key: str,
	page: int,
	page_size: int,
) -> Dict[str, Any]:
	params = {
		"from_time": from_time,
		"to_time": to_time,
		"key": key,
		"page": page,
		"pageSize": page_size,
	}
	async with session.get(url, params=params) as response:
		response.raise_for_status()
		return await response.json(content_type=None)


async def _fetch_all_video_info() -> Dict[int, Dict[str, Any]]:
	scrape_url = os.getenv("ONLINE_SCRAPE_URL", "").strip().strip('"').strip("'")
	if not scrape_url:
		raise ValueError("ONLINE_SCRAPE_URL 未配置")

	scrape_key = os.getenv("ONLINE_AUTH_KEY", os.getenv("ONLINE_AUTH_KEY", ""))
	page_size = 200

	now_date = datetime.datetime.now()
	src_date = now_date + datetime.timedelta(days=-delta_days)
	dst_date = src_date + datetime.timedelta(days=+range_days)
	from_time = src_date.strftime("%Y%m%d")
	to_time = dst_date.strftime("%Y%m%d")

	all_items: Dict[int, Dict[str, Any]] = {}
	timeout = aiohttp.ClientTimeout(total=60)

	async with aiohttp.ClientSession(timeout=timeout) as session:
		page = 1
		total_pages = 1
		while page <= total_pages:
			payload = await _fetch_one_page(
				session=session,
				url=scrape_url,
				from_time=from_time,
				to_time=to_time,
				key=scrape_key,
				page=page,
				page_size=page_size,
			)

			if not payload.get("success", False):
				raise RuntimeError(f"抓取已有数据库接口返回失败: page={page}, payload={payload}")

			data = payload.get("data", [])
			pagination = payload.get("pagination", {})
			total_pages = int(pagination.get("totalPages", total_pages or 1) or 1)

			for video in data:
				normalized = _normalize_video(video)
				video_id = normalized.get("aid")
				if video_id is None:
					continue
				all_items[int(video_id)] = normalized

			logging.info(
				f"抓取已有数据库完成第 {page}/{total_pages} 页，累计视频数 {len(all_items)}"
			)
			page += 1

	return all_items


all_video_info: Dict[int, Dict[str, Any]] = asyncio.run(_fetch_all_video_info())

