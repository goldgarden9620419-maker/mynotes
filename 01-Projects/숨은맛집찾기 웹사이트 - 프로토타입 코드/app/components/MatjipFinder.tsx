"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";
import { AnimatePresence, motion } from "framer-motion";

const FOOD_TYPES = [
  { label: "한식", keyword: "한식" },
  { label: "중식", keyword: "중식" },
  { label: "일식", keyword: "일식" },
  { label: "양식", keyword: "양식" },
  { label: "고기/구이", keyword: "고기집" },
  { label: "분식", keyword: "분식" },
  { label: "술집", keyword: "술집" },
  { label: "카페/디저트", keyword: "카페" },
] as const;

const OCCASIONS = [
  { label: "가족 모임", copy: "가족과 함께 가기 좋은" },
  { label: "친구 모임", copy: "친구들과 편하게 가기 좋은" },
  { label: "데이트", copy: "분위기 좋은 데이트하기 좋은" },
  { label: "회식", copy: "다같이 회식하기 좋은" },
  { label: "혼밥", copy: "혼자서도 편하게 갈 수 있는" },
] as const;

const FRANCHISE_BLOCKLIST = [
  "스타벅스", "이디야", "투썸플레이스", "커피빈", "폴바셋", "빽다방", "메가커피",
  "컴포즈커피", "할리스", "탐앤탐스", "매머드커피", "커피베이", "던킨",
  "맥도날드", "버거킹", "롯데리아", "kfc", "케이에프씨", "맘스터치", "서브웨이",
  "파리바게뜨", "뚜레쥬르", "배스킨라빈스",
  "교촌치킨", "bhc", "bbq", "굽네치킨", "네네치킨", "처갓집", "푸라닭", "또래오래",
  "도미노피자", "피자헛", "미스터피자", "파파존스",
  "아웃백", "빕스", "애슐리", "본죽", "본전다방", "김밥천국",
  "cu", "gs25", "세븐일레븐", "이마트24", "미니스톱",
  "설빙", "공차", "빙그레", "요거트아이스크림의정석",
];

const GEO_RADIUS_M = 2500;

type Place = {
  id: string;
  place_name: string;
  category_name: string;
  category_group_code: string;
  address_name: string;
  road_address_name: string;
  phone: string;
  place_url: string;
  distance: string;
};

function isFranchise(name: string) {
  const normalized = name.toLowerCase().replace(/\s/g, "");
  return FRANCHISE_BLOCKLIST.some((b) => normalized.includes(b.replace(/\s/g, "")));
}

export default function MatjipFinder() {
  const [sdkReady, setSdkReady] = useState(false);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);

  const [peopleCount, setPeopleCount] = useState(2);
  const [occasionIdx, setOccasionIdx] = useState(0);
  const [foodIdx, setFoodIdx] = useState(0);

  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [results, setResults] = useState<Place[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);

  const placesRef = useRef<any>(null);

  useEffect(() => {
    if (sdkReady && window.kakao?.maps) {
      window.kakao.maps.load(() => {
        placesRef.current = new window.kakao.maps.services.Places();
      });
    }
  }, [sdkReady]);

  function requestLocation() {
    setLocating(true);
    setLocationError(null);
    if (!navigator.geolocation) {
      setLocationError("이 브라우저는 위치 확인을 지원하지 않아요.");
      setLocating(false);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setLocating(false);
      },
      () => {
        setLocationError("위치 확인을 허용해주셔야 근처 맛집을 찾을 수 있어요.");
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }

  function handleSearch() {
    if (!coords) {
      setLocationError("먼저 현재 위치를 확인해주세요.");
      return;
    }
    if (!placesRef.current) {
      setSearchError("지도 서비스를 불러오는 중이에요. 잠시 후 다시 시도해주세요.");
      return;
    }

    setLoading(true);
    setSearched(true);
    setSearchError(null);
    setResults([]);

    const keyword = `${FOOD_TYPES[foodIdx].keyword} 맛집`;
    const kakaoLoc = new window.kakao.maps.LatLng(coords.lat, coords.lng);

    placesRef.current.keywordSearch(
      keyword,
      (data: Place[], status: string) => {
        setLoading(false);
        if (status !== window.kakao.maps.services.Status.OK) {
          setSearchError("근처에서 맛집을 찾지 못했어요. 다른 음식 종류로 시도해보세요.");
          return;
        }

        const filtered = data
          .filter((p) => !isFranchise(p.place_name))
          .filter((p) => p.category_group_code !== "CS2")
          .sort((a, b) => Number(a.distance) - Number(b.distance));

        // 상위 2곳은 흔히 아는 곳일 확률이 높아 건너뛰고, 그 다음부터 "숨은" 맛집으로 제안
        const hidden = filtered.length > 4 ? filtered.slice(2) : filtered;

        setResults(hidden.slice(0, 8));
      },
      {
        location: kakaoLoc,
        radius: GEO_RADIUS_M,
        sort: window.kakao.maps.services.SortBy.DISTANCE,
      }
    );
  }

  return (
    <>
      <Script
        src={`https://dapi.kakao.com/v2/maps/sdk.js?appkey=${process.env.NEXT_PUBLIC_KAKAO_JS_KEY}&libraries=services&autoload=false`}
        onReady={() => setSdkReady(true)}
      />

      <div className="w-full max-w-xl rounded-3xl border border-border bg-card p-6 shadow-sm sm:p-8">
        {/* 위치 확인 */}
        <div className="mb-6">
          <div className="mb-2 text-sm font-medium text-muted">1. 현재 위치</div>
          {coords ? (
            <div className="flex items-center justify-between rounded-xl bg-accent/10 px-4 py-3 text-sm">
              <span className="font-medium text-accent">📍 위치 확인 완료</span>
              <button
                onClick={requestLocation}
                className="text-xs text-muted underline underline-offset-2"
              >
                다시 확인
              </button>
            </div>
          ) : (
            <button
              onClick={requestLocation}
              disabled={locating}
              className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm font-medium hover:border-accent disabled:opacity-60"
            >
              {locating ? "위치 확인 중..." : "📍 내 위치 확인하기"}
            </button>
          )}
          {locationError && (
            <p className="mt-2 text-xs text-red-500">{locationError}</p>
          )}
        </div>

        {/* 인원수 */}
        <div className="mb-6">
          <div className="mb-2 text-sm font-medium text-muted">2. 인원수</div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setPeopleCount((n) => Math.max(1, n - 1))}
              className="h-9 w-9 rounded-full border border-border text-lg"
            >
              −
            </button>
            <span className="w-12 text-center text-base font-semibold">
              {peopleCount}명
            </span>
            <button
              onClick={() => setPeopleCount((n) => Math.min(20, n + 1))}
              className="h-9 w-9 rounded-full border border-border text-lg"
            >
              +
            </button>
          </div>
        </div>

        {/* 모임 성격 */}
        <div className="mb-6">
          <div className="mb-2 text-sm font-medium text-muted">3. 모임 성격</div>
          <div className="flex flex-wrap gap-2">
            {OCCASIONS.map((o, i) => (
              <button
                key={o.label}
                onClick={() => setOccasionIdx(i)}
                className={`rounded-full px-4 py-2 text-sm transition ${
                  occasionIdx === i
                    ? "bg-accent text-white"
                    : "border border-border text-foreground"
                }`}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>

        {/* 음식 종류 */}
        <div className="mb-8">
          <div className="mb-2 text-sm font-medium text-muted">4. 먹고 싶은 음식</div>
          <div className="flex flex-wrap gap-2">
            {FOOD_TYPES.map((f, i) => (
              <button
                key={f.label}
                onClick={() => setFoodIdx(i)}
                className={`rounded-full px-4 py-2 text-sm transition ${
                  foodIdx === i
                    ? "bg-accent text-white"
                    : "border border-border text-foreground"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleSearch}
          disabled={!sdkReady || loading}
          className="w-full rounded-xl bg-accent px-4 py-3.5 text-base font-semibold text-white shadow-sm transition hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "숨은 맛집 찾는 중..." : "숨은 맛집 찾기"}
        </button>
      </div>

      {/* 결과 */}
      <AnimatePresence>
        {searched && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-8 w-full max-w-xl"
          >
            {loading && (
              <div className="py-10 text-center text-sm text-muted">
                {OCCASIONS[occasionIdx].copy} {FOOD_TYPES[foodIdx].label} 맛집을 찾고 있어요...
              </div>
            )}

            {!loading && searchError && (
              <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">
                {searchError}
              </p>
            )}

            {!loading && !searchError && results.length === 0 && (
              <p className="rounded-xl bg-background px-4 py-6 text-center text-sm text-muted">
                근처 {GEO_RADIUS_M}m 안에서는 조건에 맞는 곳을 찾지 못했어요. 다른 음식 종류로 시도해보세요.
              </p>
            )}

            {!loading && results.length > 0 && (
              <>
                <h2 className="mb-4 text-lg font-bold">
                  {peopleCount}명이서 {OCCASIONS[occasionIdx].copy} 숨은{" "}
                  {FOOD_TYPES[foodIdx].label} 맛집
                </h2>
                <div className="flex flex-col gap-3">
                  {results.map((p, i) => (
                    <motion.a
                      key={p.id}
                      href={p.place_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="block rounded-2xl border border-border bg-card p-4 transition hover:border-accent hover:shadow-md"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="font-semibold">{p.place_name}</div>
                          <div className="mt-0.5 text-xs text-muted">
                            {p.category_name.split(">").pop()?.trim()}
                          </div>
                        </div>
                        <span className="shrink-0 rounded-full bg-accent/10 px-2.5 py-1 text-xs font-medium text-accent">
                          {p.distance}m
                        </span>
                      </div>
                      <div className="mt-2 text-xs text-muted">
                        {p.road_address_name || p.address_name}
                      </div>
                    </motion.a>
                  ))}
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
