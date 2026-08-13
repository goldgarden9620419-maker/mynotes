"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";
import { AnimatePresence, motion } from "framer-motion";

const FOOD_TYPES = [
  { label: "한식", keyword: "한식", emoji: "🍚" },
  { label: "중식", keyword: "중식", emoji: "🥟" },
  { label: "일식", keyword: "일식", emoji: "🍣" },
  { label: "양식", keyword: "양식", emoji: "🍝" },
  { label: "고기/구이", keyword: "고기집", emoji: "🥩" },
  { label: "분식", keyword: "분식", emoji: "🍢" },
  { label: "술집", keyword: "술집", emoji: "🍻" },
  { label: "카페/디저트", keyword: "카페", emoji: "☕" },
] as const;

const OCCASIONS = [
  { label: "가족 모임", copy: "가족과 함께 가기 좋은", emoji: "👨‍👩‍👧" },
  { label: "친구 모임", copy: "친구들과 편하게 가기 좋은", emoji: "🧑‍🤝‍🧑" },
  { label: "데이트", copy: "분위기 좋은 데이트하기 좋은", emoji: "💕" },
  { label: "회식", copy: "다같이 회식하기 좋은", emoji: "🍺" },
  { label: "혼밥", copy: "혼자서도 편하게 갈 수 있는", emoji: "🧑" },
] as const;

const AGE_GROUPS = ["10대", "20대", "30대", "40대", "50대", "60대 이상"] as const;

const PURPOSES = [
  { label: "식사", emoji: "🍽️", keyword: "맛집" },
  { label: "음주", emoji: "🍻", keyword: "술집" },
] as const;

const RADIUS_OPTIONS = [
  { label: "도보 5분", meters: 400 },
  { label: "도보 15분", meters: 1200 },
  { label: "차로 5분", meters: 2500 },
  { label: "차로 15분", meters: 6000 },
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

function PillButton({
  active,
  onClick,
  children,
}: Readonly<{ active: boolean; onClick: () => void; children: React.ReactNode }>) {
  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.06 }}
      whileTap={{ scale: 0.94 }}
      transition={{ type: "spring", stiffness: 400, damping: 20 }}
      className={`rounded-full px-4 py-2 text-sm transition-colors ${
        active
          ? "bg-accent text-white shadow-sm shadow-accent/30"
          : "border border-border text-foreground hover:border-accent"
      }`}
    >
      {children}
    </motion.button>
  );
}

function Stepper({
  label,
  value,
  onChange,
  min = 0,
  max = 20,
}: Readonly<{
  label: string;
  value: number;
  onChange: (n: number) => void;
  min?: number;
  max?: number;
}>) {
  return (
    <div className="flex flex-col items-center gap-1.5 rounded-xl border border-border px-3 py-2.5">
      <span className="text-xs text-muted">{label}</span>
      <div className="flex items-center gap-2.5">
        <motion.button
          type="button"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => onChange(Math.max(min, value - 1))}
          className="h-7 w-7 rounded-full border border-border text-sm hover:border-accent"
        >
          −
        </motion.button>
        <motion.span
          key={value}
          initial={{ scale: 1.3, opacity: 0.5 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 500, damping: 15 }}
          className="w-5 text-center text-sm font-semibold"
        >
          {value}
        </motion.span>
        <motion.button
          type="button"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => onChange(Math.min(max, value + 1))}
          className="h-7 w-7 rounded-full border border-border text-sm hover:border-accent"
        >
          +
        </motion.button>
      </div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <motion.div
      className="mx-auto h-8 w-8 rounded-full border-[3px] border-accent/20 border-t-accent"
      animate={{ rotate: 360 }}
      transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
    />
  );
}

export default function MatjipFinder() {
  const [sdkReady, setSdkReady] = useState(false);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);

  const [adults, setAdults] = useState(2);
  const [teens, setTeens] = useState(0);
  const [children, setChildren] = useState(0);
  const [ageGroupIdx, setAgeGroupIdx] = useState(1);
  const [occasionIdx, setOccasionIdx] = useState(0);
  const [purposeIdx, setPurposeIdx] = useState(0);
  const [foodIdx, setFoodIdx] = useState(0);
  const [radiusIdx, setRadiusIdx] = useState(2);

  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [results, setResults] = useState<Place[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);

  const placesRef = useRef<any>(null);

  const totalPeople = adults + teens + children;

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
    if (totalPeople < 1) {
      setLocationError("인원수를 1명 이상으로 설정해주세요.");
      return;
    }

    setLoading(true);
    setSearched(true);
    setSearchError(null);
    setResults([]);

    const foodKeyword = FOOD_TYPES[foodIdx].keyword;
    const purpose = PURPOSES[purposeIdx];
    // 음식 종류가 이미 "술집"이면 목적 키워드를 중복으로 덧붙이지 않음
    const suffix = foodKeyword === purpose.keyword ? "" : ` ${purpose.keyword}`;
    const keyword = `${foodKeyword}${suffix}`;
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
        radius: RADIUS_OPTIONS[radiusIdx].meters,
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

      <div className="relative w-full max-w-xl">
        {/* 배경 장식 블러 블롭 */}
        <div
          aria-hidden
          className="pointer-events-none absolute -top-16 -right-10 -z-10 h-56 w-56 rounded-full bg-accent/20 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-10 -left-10 -z-10 h-48 w-48 rounded-full bg-accent/10 blur-3xl"
        />

        <div className="rounded-3xl border border-border bg-card p-6 shadow-sm sm:p-8">
          {/* 위치 확인 */}
          <div className="mb-6">
            <div className="mb-2 text-sm font-medium text-muted">1. 현재 위치</div>
            {coords ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center justify-between rounded-xl bg-accent/10 px-4 py-3 text-sm"
              >
                <span className="flex items-center gap-1.5 font-medium text-accent">
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 500, damping: 15 }}
                  >
                    📍
                  </motion.span>
                  위치 확인 완료
                </span>
                <button
                  onClick={requestLocation}
                  className="text-xs text-muted underline underline-offset-2 hover:text-accent"
                >
                  다시 확인
                </button>
              </motion.div>
            ) : (
              <motion.button
                onClick={requestLocation}
                disabled={locating}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm font-medium hover:border-accent disabled:opacity-60"
              >
                {locating ? (
                  <span className="inline-flex items-center gap-2">
                    <motion.span
                      className="h-3.5 w-3.5 rounded-full border-2 border-accent/30 border-t-accent"
                      animate={{ rotate: 360 }}
                      transition={{ repeat: Infinity, duration: 0.7, ease: "linear" }}
                    />
                    위치 확인 중...
                  </span>
                ) : (
                  "📍 내 위치 확인하기"
                )}
              </motion.button>
            )}
            {locationError && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-2 text-xs text-red-500"
              >
                {locationError}
              </motion.p>
            )}
          </div>

          {/* 인원 구성 */}
          <div className="mb-6">
            <div className="mb-2 text-sm font-medium text-muted">
              2. 인원 구성 <span className="text-accent">· 총 {totalPeople}명</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <Stepper label="성인" value={adults} onChange={setAdults} min={0} />
              <Stepper label="청소년" value={teens} onChange={setTeens} min={0} />
              <Stepper label="어린이" value={children} onChange={setChildren} min={0} />
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {AGE_GROUPS.map((label, i) => (
                <PillButton key={label} active={ageGroupIdx === i} onClick={() => setAgeGroupIdx(i)}>
                  {label}
                </PillButton>
              ))}
            </div>
          </div>

          {/* 모임 성격 */}
          <div className="mb-6">
            <div className="mb-2 text-sm font-medium text-muted">3. 모임 성격</div>
            <div className="flex flex-wrap gap-2">
              {OCCASIONS.map((o, i) => (
                <PillButton key={o.label} active={occasionIdx === i} onClick={() => setOccasionIdx(i)}>
                  <span className="mr-1">{o.emoji}</span>
                  {o.label}
                </PillButton>
              ))}
            </div>
          </div>

          {/* 목적: 식사/음주 */}
          <div className="mb-6">
            <div className="mb-2 text-sm font-medium text-muted">4. 목적</div>
            <div className="flex flex-wrap gap-2">
              {PURPOSES.map((p, i) => (
                <PillButton key={p.label} active={purposeIdx === i} onClick={() => setPurposeIdx(i)}>
                  <span className="mr-1">{p.emoji}</span>
                  {p.label}
                </PillButton>
              ))}
            </div>
          </div>

          {/* 음식 종류 */}
          <div className="mb-6">
            <div className="mb-2 text-sm font-medium text-muted">5. 먹고 싶은 음식</div>
            <div className="flex flex-wrap gap-2">
              {FOOD_TYPES.map((f, i) => (
                <PillButton key={f.label} active={foodIdx === i} onClick={() => setFoodIdx(i)}>
                  <span className="mr-1">{f.emoji}</span>
                  {f.label}
                </PillButton>
              ))}
            </div>
          </div>

          {/* 검색 반경 */}
          <div className="mb-8">
            <div className="mb-2 text-sm font-medium text-muted">6. 검색 반경</div>
            <div className="flex flex-wrap gap-2">
              {RADIUS_OPTIONS.map((r, i) => (
                <PillButton key={r.label} active={radiusIdx === i} onClick={() => setRadiusIdx(i)}>
                  {r.label}
                </PillButton>
              ))}
            </div>
          </div>

          <motion.button
            onClick={handleSearch}
            disabled={!sdkReady || loading}
            whileHover={sdkReady && !loading ? { scale: 1.02 } : undefined}
            whileTap={sdkReady && !loading ? { scale: 0.98 } : undefined}
            className="w-full rounded-xl bg-accent px-4 py-3.5 text-base font-semibold text-white shadow-md shadow-accent/25 transition hover:opacity-90 disabled:opacity-50"
          >
            {loading ? (
              <span className="inline-flex items-center justify-center gap-2">
                <motion.span
                  className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white"
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.7, ease: "linear" }}
                />
                숨은 맛집 찾는 중...
              </span>
            ) : (
              "숨은 맛집 찾기"
            )}
          </motion.button>
        </div>
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
              <div className="flex flex-col items-center gap-4 py-10 text-center text-sm text-muted">
                <LoadingSpinner />
                {OCCASIONS[occasionIdx].copy} {FOOD_TYPES[foodIdx].label} {PURPOSES[purposeIdx].keyword}을
                찾고 있어요...
              </div>
            )}

            {!loading && searchError && (
              <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">
                {searchError}
              </p>
            )}

            {!loading && !searchError && results.length === 0 && (
              <p className="rounded-xl bg-background px-4 py-6 text-center text-sm text-muted">
                근처 {RADIUS_OPTIONS[radiusIdx].label} 거리 안에서는 조건에 맞는 곳을 찾지 못했어요. 검색
                반경을 넓히거나 다른 음식 종류로 시도해보세요.
              </p>
            )}

            {!loading && results.length > 0 && (
              <>
                <h2 className="mb-2 text-lg font-bold">
                  {totalPeople}명이서 {OCCASIONS[occasionIdx].copy} 숨은 {FOOD_TYPES[foodIdx].label}{" "}
                  {PURPOSES[purposeIdx].keyword}
                </h2>
                <div className="mb-4 flex flex-wrap gap-1.5 text-xs text-muted">
                  {adults > 0 && (
                    <span className="rounded-full bg-secondary px-2.5 py-1">성인 {adults}</span>
                  )}
                  {teens > 0 && (
                    <span className="rounded-full bg-secondary px-2.5 py-1">청소년 {teens}</span>
                  )}
                  {children > 0 && (
                    <span className="rounded-full bg-secondary px-2.5 py-1">어린이 {children}</span>
                  )}
                  <span className="rounded-full bg-secondary px-2.5 py-1">{AGE_GROUPS[ageGroupIdx]}</span>
                  <span className="rounded-full bg-secondary px-2.5 py-1">{RADIUS_OPTIONS[radiusIdx].label} 이내</span>
                </div>
                <div className="flex flex-col gap-3">
                  {results.map((p, i) => (
                    <motion.a
                      key={p.id}
                      href={p.place_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      initial={{ opacity: 0, y: 14 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.06, type: "spring", stiffness: 300, damping: 26 }}
                      whileHover={{ y: -3, scale: 1.01 }}
                      className="block rounded-2xl border border-border bg-card p-4 shadow-sm transition-colors hover:border-accent hover:shadow-lg hover:shadow-accent/10"
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
