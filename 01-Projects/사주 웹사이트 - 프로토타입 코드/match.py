# -*- coding: utf-8 -*-
"""
사주 웹사이트 - 유명인 매칭 로직 (DB를 JSON 파일로 분리한 버전)
필요 파일: celebrities.json, ohang_copy.json (같은 디렉터리)
"""
import json
import random
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from lunar_python import Solar

BASE_DIR = Path(__file__).parent

STEM_TO_OHANG = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}


@dataclass
class Celebrity:
    name: str
    ilju: str
    story: str
    habit: str
    motto: str
    ohang: str = field(init=False)

    def __post_init__(self):
        self.ohang = STEM_TO_OHANG[self.ilju[0]]


def load_celebrities(path: Path = None) -> list[Celebrity]:
    path = path or BASE_DIR / "celebrities.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [Celebrity(**item) for item in raw]


def load_ohang_copy(path: Path = None) -> dict:
    path = path or BASE_DIR / "ohang_copy.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


CELEBRITY_DB = load_celebrities()
OHANG_COPY = load_ohang_copy()

ILJU_INDEX = {}
for c in CELEBRITY_DB:
    ILJU_INDEX.setdefault(c.ilju, []).append(c)

OHANG_INDEX = {}
for c in CELEBRITY_DB:
    OHANG_INDEX.setdefault(c.ohang, []).append(c)


def get_ilju(year: int, month: int, day: int) -> str:
    solar = Solar.fromYmd(year, month, day)
    return solar.getLunar().getEightChar().getDay()


def match(year: int, month: int, day: int, max_results: int = 3) -> dict:
    ilju = get_ilju(year, month, day)
    ohang = STEM_TO_OHANG[ilju[0]]
    exact = ILJU_INDEX.get(ilju, [])

    if exact:
        return {
            "match_type": "exact",
            "ilju": ilju,
            "ohang": ohang,
            "celebrities": exact[:max_results],
            "ohang_copy": OHANG_COPY[ohang],
        }

    pool = OHANG_INDEX.get(ohang, [])
    seed_str = f"{year:04d}-{month:02d}-{day:02d}"
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
    rng = random.Random(seed)
    picks = rng.sample(pool, k=min(max_results, len(pool)))
    return {
        "match_type": "fallback_ohang",
        "ilju": ilju,
        "ohang": ohang,
        "celebrities": picks,
        "ohang_copy": OHANG_COPY[ohang],
    }


if __name__ == "__main__":
    print(f"DB 로드 확인: {len(CELEBRITY_DB)}명")
    for y, m, d in [(1955, 2, 24), (1990, 3, 15), (1990, 3, 15), (2000, 1, 1)]:
        r = match(y, m, d)
        print(f"{y}-{m:02d}-{d:02d} -> {r['match_type']} / {r['ilju']}({r['ohang']}) -> {[c.name for c in r['celebrities']]}")
