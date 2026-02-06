from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field
import marshal
import datetime

class Mid:
    mid: int
    s1: float
    s2: float
    video_aids: List[int]
    s1_bias: float
    def __init__(self, mid: int):
        self.video_aids = []
        self.mid = mid
        self.s1, self.s2 = 0., 0.
        self.s1_bias = 0.
        
    def add_video_aid(self, video_aid: int):
        self.video_aids.append(video_aid)
    
    @staticmethod
    def serialize_mid(mid_list: Dict[int, 'Mid'], file_path: str) -> None:
        serialized: List[Tuple[int, float, float, List[int]]] = []
        for mid in mid_list:
            serialized.append((mid, mid_list[mid].s1+mid_list[mid].s1_bias, mid_list[mid].s2, mid_list[mid].video_aids))
        marshal.dump(serialized, open(file_path, "wb"))
    @staticmethod
    def deserialize_mid(file_path: str) -> Dict[int, 'Mid']:
        serialized: List[Tuple[int, float, float, List[int]]] = marshal.load(open(file_path, "rb"))
        mid_list: Dict[int, Mid] = {}
        for pack in serialized:
            # if len(pack)==5:
            #     mid, s1, s1_bias, s2, video_aids = pack
            # elif len(pack)==4:
            mid, s1, s2, video_aids = pack
            #     s1_bias = 1
            mid_list[mid] = Mid(mid)
            mid_list[mid].s1 = s1
            mid_list[mid].s2 = s2
            mid_list[mid].video_aids = video_aids
        return mid_list
    @staticmethod
    def deserialize_mid_oldstyle(file_path: str) -> Dict[int, 'Mid']:
        serialized: Dict[int, Dict[str, Any]] = marshal.load(open(file_path, "rb"))
        mid_list: Dict[int, Mid] = {}
        for mid, video_dict in serialized.items():
            mid_list[mid] = Mid(mid)
            mid_list[mid].s1 = video_dict['s1']
            mid_list[mid].s2 = video_dict['s2']
            mid_list[mid].video_aids = []
        return mid_list

    def mix_weight(self, b: Optional['Mid'], self_w: float) -> 'Mid':
        self.s1 *= self_w
        self.s2 *= self_w
        if b:
            self.s1 += b.s1 * (1 - self_w)
            self.s2 += b.s2 * (1 - self_w)
            self.video_aids += [aid for aid in b.video_aids if aid not in self.video_aids]
        return self

class DateYield:
    """ 日期迭代器
    在指定日期范围内，如果范围小于一个月，则直接 yield 这个范围；否则将每个月倒序分开 yield。
    如指定了 23-07-25 到 23-09-25，则 yield 结果将会是 ("230901", "240925") ("230801", "230831") ("230725", "230731")
    """
    src_date: datetime.datetime
    dst_date: datetime.datetime
    src_date_str: str
    dst_date_str: str
    def __init__(self, src_date: datetime.datetime, dst_date: datetime.datetime):
        self.src_date = src_date
        self.dst_date = dst_date
        self.src_date_str = src_date.strftime("%Y%m%d")
        self.dst_date_str = dst_date.strftime("%Y%m%d")
    
    def __iter__(self):
        if self.dst_date-self.src_date <= datetime.timedelta(days=30):
            yield (self.src_date.strftime("%Y%m%d"),
                   self.dst_date.strftime("%Y%m%d"))
        else:
            dst_yielding = self.dst_date
            src_yielding = self.dst_date.replace(day=1)
            while src_yielding >= self.src_date and dst_yielding >= self.src_date:
                yield (src_yielding.strftime("%Y%m%d"),
                       dst_yielding.strftime("%Y%m%d"))
                dst_yielding = src_yielding + datetime.timedelta(days=-1)
                src_yielding = dst_yielding.replace(day=1)
                if src_yielding < self.src_date:
                    src_yielding = self.src_date
