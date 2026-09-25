// 선택지 카탈로그 — kr: UI 표시, en: 프롬프트 조립용
export const o = (kr, en, disp, sub) => ({ kr, en: en || kr, disp, sub });
// 화면 표시용 라벨 (내부값은 유지, UI만 한국어)
export const disp = (catalog, value) => {
  const hit = (catalog || []).find((c) => c.kr === value);
  return hit ? (hit.disp || hit.kr) : value;
};

export const PURPOSES = [o("제품 인지도","product awareness"), o("제품 소개","product introduction"), o("제품 사용법","product usage demonstration"), o("브랜드 이미지","brand image"), o("구매 전환","purchase conversion"), o("SNS 콘텐츠","social media content")];
export const PLATFORMS = [o("Instagram Reels", "Instagram Reels", "인스타그램 릴스"), o("TikTok", "TikTok", "틱톡"), o("YouTube Shorts", "YouTube Shorts", "유튜브 쇼츠"), o("Instagram Feed", "Instagram Feed", "인스타그램 피드"), o("Meta Ads", "Meta Ads", "메타 광고")];
export const RATIOS = [o("9:16"), o("4:5"), o("1:1"), o("16:9")];
export const LENGTHS = [o("6초","6 seconds"), o("10초","10 seconds"), o("15초","15 seconds"), o("20초","20 seconds"), o("30초","30 seconds")];
export const AD_STYLES = [o("Premium Commercial", "Premium Commercial", "프리미엄 광고"), o("Instagram Lifestyle", "Instagram Lifestyle", "인스타 라이프스타일"), o("TikTok UGC", "TikTok UGC", "틱톡 UGC"), o("Korean Beauty", "Korean Beauty", "K-뷰티"), o("Wellness", "Wellness", "웰니스"), o("Cinematic Brand Film", "Cinematic Brand Film", "시네마틱 브랜드 필름"), o("Minimal Luxury", "Minimal Luxury", "미니멀 럭셔리"), o("Emotional Lifestyle", "Emotional Lifestyle", "감성 라이프스타일"), o("Clean & Healthy", "Clean & Healthy", "클린 & 헬시")];
export const COLOR_MOODS = [o("Warm Beige", "warm beige palette", "웜 베이지"), o("Clean White", "clean white palette", "클린 화이트"), o("Natural Green", "natural green palette", "내추럴 그린"), o("Ice Blue", "ice blue palette", "아이스 블루"), o("Soft Pink", "soft pink palette", "소프트 핑크"), o("Black Luxury", "black luxury palette", "블랙 럭셔리"), o("Golden", "golden palette", "골든"), o("Pastel", "pastel palette", "파스텔"), o("Cinematic Neutral", "cinematic neutral palette", "시네마틱 뉴트럴")];

export const GENDERS = [o("여성","female"), o("남성","male")];
export const ETHNICITIES = [o("한국인 / 동아시아인","Korean / East Asian"), o("일본인","Japanese"), o("중국인","Chinese"), o("유럽계","European"), o("동서양 혼혈","Eurasian mixed-heritage")];
export const AGES = [o("20대 초반","early 20s"), o("20대 후반","late 20s"), o("30대 초반","early 30s"), o("30대 후반","late 30s"), o("40대","40s"), o("50대 이상","50s or older")];
export const FACES = [o("계란형","oval face"), o("둥근형","round face"), o("갸름한형","slim tapered face"), o("부드러운 V라인","soft V-line jaw"), o("각진형","angular face")];
export const SKINS = [o("밝은 아이보리","fair ivory skin"), o("웜 아이보리","warm ivory skin"), o("내추럴 베이지","natural beige skin"), o("건강한 웜 베이지","healthy warm-beige skin"), o("태닝","tanned skin")];
export const EYES = [o("자연스러운 아몬드형","natural almond-shaped eyes"), o("크고 또렷한 눈","large clear eyes"), o("부드러운 둥근 눈","soft round eyes"), o("길고 세련된 눈","long elegant eyes")];
export const IRISES = [o("다크 브라운","dark brown irises"), o("브라운","brown irises"), o("라이트 브라운","light brown irises"), o("헤이즐","hazel irises")];
export const HAIR_LENGTHS = [o("숏","short hair"), o("단발","bob-length hair"), o("중간 길이","medium-length hair"), o("긴 머리","long hair")];
export const HAIR_STYLES = [o("스트레이트","straight hair"), o("자연스러운 웨이브","natural loose waves"), o("굵은 웨이브","voluminous waves"), o("소프트 컬","soft curls"), o("포니테일","ponytail"), o("번","bun")];
export const HAIR_COLORS = [o("블랙","black hair"), o("소프트 블랙","soft black hair"), o("다크 브라운","dark brown hair"), o("브라운","brown hair")];
export const MODEL_VIEWS = [o("정면","front-facing view"), o("왼쪽 45도","45-degree left view"), o("오른쪽 45도","45-degree right view"), o("측면","profile view"), o("얼굴 Close-up", "face close-up", "얼굴 클로즈업"), o("상반신","upper-body shot"), o("전신","full-body shot"), o("Character Sheet", "character reference sheet", "캐릭터 시트")];

export const PRODUCT_TYPES = [o("Bottle", "bottle", "병(보틀)"), o("Box", "box", "박스"), o("Pouch", "pouch", "파우치"), o("Tube", "tube", "튜브"), o("Jar", "jar", "크림 용기(자)"), o("Capsule", "capsule", "캡슐"), o("Sachet", "sachet", "스틱(사셰)"), o("기타","product")];
export const PRODUCT_SHOTS = [o("Hero Product", "hero product shot", "히어로 제품샷"), o("Floating Product", "floating product shot", "공중 부유샷"), o("Macro Detail", "macro detail shot", "매크로 디테일"), o("Rotating Product", "rotating product shot", "회전 제품샷"), o("Product + Ingredient", "product with ingredients", "제품 + 원료"), o("Product + Water", "product with water", "제품 + 물"), o("Product + Particles", "product with particles", "제품 + 빛입자"), o("Minimal Luxury", "minimal luxury product shot", "미니멀 럭셔리"), o("Lifestyle Product", "lifestyle product shot", "라이프스타일 제품샷")];
export const PRODUCT_ANGLES = [o("Front", "front angle", "정면"), o("Left 45°", "45-degree left angle", "왼쪽 45도"), o("Right 45°", "45-degree right angle", "오른쪽 45도"), o("Low Angle", "low angle", "로우 앵글"), o("Top View", "top-down view", "탑뷰"), o("Macro", "macro angle", "매크로"), o("Extreme Macro", "extreme macro angle", "익스트림 매크로")];
export const PRODUCT_POSITIONS = [
  o("중앙", "centered in frame", null, "정중앙 배치 — 가장 안정적인 기본"),
  o("하단 중앙", "bottom-center of frame", null, "아래쪽 배치 — 위 공간에 자막/캡션 올리기 좋음 (세로 영상 추천)"),
  o("왼쪽", "left of frame"), o("오른쪽", "right of frame"),
  o("테이블", "on a table surface", null, "테이블 위 — 생활 맥락이 느껴지는 연출")
];
// 실제 크기감 — AI가 제품을 너무 크거나 작게 그리는 오류 방지
export const PRODUCT_SCALES = [
  o("한 손 소형", "small — fits comfortably in one hand (like a phone or small spray bottle)", null, "스프레이·화장품·영양제 등 (기본)"),
  o("양손 중형", "medium-sized — held with both hands (like a cereal box)", null, "박스 세트·대용량 용기 등"),
  o("대형", "large — appliance-scale, sits on the floor or counter", null, "소형가전·생활가전 등"),
  o("지정 안 함", "", null, "사진만 보고 판단하게 둠")
];
export const PRODUCT_BGS = [o("Pure White", "pure white background", "퓨어 화이트"), o("Pure Black", "pure black background", "퓨어 블랙"), o("Warm Beige", "warm beige background", "웜 베이지"), o("Soft Gray", "soft gray background", "소프트 그레이"), o("Pastel", "pastel background", "파스텔"), o("Dark Luxury", "dark luxury background", "다크 럭셔리"), o("Natural", "natural background", "내추럴"), o("Abstract", "abstract background", "추상 배경")];
export const PRODUCT_FX = [o("Water Droplets", "water droplets", "물방울"), o("Splash", "water splash", "물 스플래시"), o("Ice", "ice", "얼음"), o("Ingredient", "scattered ingredients", "원료"), o("Floating Particles", "floating particles", "떠다니는 입자"), o("Mist", "mist", "안개"), o("Reflection", "reflection", "반사"), o("Shadow", "dramatic shadow", "그림자"), o("Glow", "soft glow", "글로우"), o("없음","no added effects")];

export const PLACES = [o("프리미엄 주방","premium kitchen"), o("모던 한국 아파트","modern Korean apartment"), o("미니멀 거실","minimal living room"), o("럭셔리 욕실","luxury bathroom"), o("침실","bedroom"), o("드레스룸","dressing room"), o("Beauty Studio", "beauty studio", "뷰티 스튜디오"), o("Modern Office", "modern office", "모던 오피스"), o("Café", "café", "카페"), o("Fitness Studio", "fitness studio", "피트니스 스튜디오"), o("Park", "park", "공원"), o("City Street", "city street", "도시 거리"), o("Rooftop", "rooftop", "루프탑"), o("Beach", "beach", "해변"), o("Forest", "forest", "숲 / 자연"), o("Luxury Studio", "luxury studio set", "럭셔리 스튜디오"), o("Abstract Commercial Set", "abstract commercial set", "추상 광고 세트")];
export const INTERIORS = [o("Minimal Korean", "minimal Korean interior", "미니멀 코리안"), o("Scandinavian", "Scandinavian interior", "스칸디나비안"), o("Modern Luxury", "modern luxury interior", "모던 럭셔리"), o("Natural Organic", "natural organic interior", "내추럴 오가닉"), o("Clean Wellness", "clean wellness interior", "클린 웰니스"), o("Premium Beauty", "premium beauty interior", "프리미엄 뷰티"), o("Urban Lifestyle", "urban lifestyle interior", "어반 라이프스타일"), o("High Fashion", "high fashion interior", "하이패션"), o("Cinematic", "cinematic interior", "시네마틱"), o("Real Home / UGC", "real home UGC-style interior", "리얼 홈 (UGC)")];
export const TIMES = [o("Sunrise", "sunrise", "일출"), o("Morning", "morning", "아침"), o("Day", "midday", "낮"), o("Afternoon", "afternoon", "오후"), o("Golden Hour", "golden hour", "골든아워"), o("Sunset", "sunset", "일몰"), o("Night", "night", "밤")];
export const ENV_LIGHTS = [o("Soft Window Light", "soft window light", "부드러운 창가 빛"), o("Bright Natural Light", "bright natural light", "밝은 자연광"), o("Warm Morning Light", "warm morning light", "따뜻한 아침 햇살"), o("Diffused Light", "diffused light", "확산광"), o("Golden Sunlight", "golden sunlight", "골든 선라이트"), o("Studio Lighting", "studio lighting", "스튜디오 조명"), o("Moody Cinematic", "moody cinematic lighting", "무디 시네마틱"), o("Neon Urban", "neon urban lighting", "네온 어반")];
export const LOC_LENSES = [
  o("24mm", "24mm lens", "24mm", "공간을 넓게 — 인테리어 전체를 보여주는 설정샷에 적합"),
  o("35mm", "35mm lens", "35mm", "자연스러운 공간감 — 실제로 그 공간에 서 있는 느낌"),
  o("50mm", "50mm lens", "50mm", "왜곡 없는 안정적 구도 — 공간 일부를 차분하게"),
  o("85mm", "85mm lens", "85mm", "공간의 한 부분을 압축해 분위기 있는 디테일 컷으로")
];
export const LOC_CAM_HEIGHTS = [
  o("Eye Level", "eye-level camera", "아이레벨", "그 공간에 서 있는 듯한 자연스러운 시점"),
  o("Table Level", "table-level camera", "테이블 레벨", "테이블·조리대 높이 — 제품을 나중에 올려놓을 자리 중심"),
  o("Low Angle", "low-angle camera", "로우 앵글", "올려다보는 구도 — 천장·창문까지 담겨 공간이 웅장해 보임"),
  o("High Angle", "high-angle camera", "하이 앵글", "내려다보는 구도 — 공간 배치가 한눈에 정리됨"),
  o("Wide Establishing", "wide establishing camera", "와이드 설정샷", "공간 전체를 넓게 — 광고 도입부의 배경 소개 컷")
];

export const LIGHT_DIRS = [o("Camera Left → Right", "light from camera-left to camera-right", "카메라 왼쪽 → 오른쪽"), o("Camera Right → Left", "light from camera-right to camera-left", "카메라 오른쪽 → 왼쪽"), o("Front Soft", "soft frontal light", "정면 소프트"), o("Backlight", "backlight", "역광"), o("Top Light", "top light", "탑 라이트")];
export const LIGHT_TEMPS = [o("Warm", "warm color temperature", "웜 (따뜻하게)"), o("Neutral", "neutral color temperature", "뉴트럴"), o("Cool", "cool color temperature", "쿨 (차갑게)")];
export const LENSES = [
  o("24mm", "24mm lens", "24mm", "넓은 화각 — 공간 전체가 담겨 역동적, 배경 맥락 강조 (가장자리 왜곡 약간)"),
  o("35mm", "35mm lens", "35mm", "자연스러운 시야 — 일상·라이프스타일 광고에 무난한 만능 렌즈"),
  o("50mm", "50mm lens", "50mm", "사람 눈과 비슷한 화각 — 왜곡 없이 안정적, 시네마틱한 기본기"),
  o("85mm", "85mm lens", "85mm", "인물·제품 집중 — 배경이 예쁘게 흐려져(보케) 피사체가 돋보임"),
  o("100mm Macro", "100mm macro lens", "100mm 매크로", "초근접 디테일 — 라벨·질감·물방울 클로즈업 전용")
];
export const CAM_HEIGHTS = [
  o("Eye Level", "eye-level camera height", "아이레벨", "눈높이에서 촬영 — 가장 자연스럽고 친근한 시선, 어떤 광고에도 무난"),
  o("Low", "low camera height", "로우", "아래에서 올려다봄 — 제품·인물이 웅장하고 당당해 보임 (히어로샷)"),
  o("High", "high camera height", "하이", "위에서 내려다봄 — 아담하고 귀여운 느낌, 상황 전체를 정리해서 보여줌"),
  o("Table Level", "table-level camera height", "테이블 레벨", "테이블 높이 시선 — 제품이 놓인 장면에 몰입감, 음식·제품 연출 단골"),
  o("Top View", "top-down camera view", "탑뷰", "수직 부감 — 구성 요소를 한눈에 정리하는 플랫레이, 정돈된 느낌")
];
export const FRAMES = [
  o("Extreme Close-Up", "extreme close-up framing", "익스트림 클로즈업", "화면 가득 초근접 — 라벨 글자·눈동자 등 한 포인트에 강한 임팩트"),
  o("Close-Up", "close-up framing", "클로즈업", "얼굴/제품이 화면 대부분 — 감정·디테일 전달, 첫 훅 컷에 효과적"),
  o("Medium Close-Up", "medium close-up framing", "미디엄 클로즈업", "가슴 위까지 — 표정과 제품을 같이 보여주는 균형 구도"),
  o("Medium Shot", "medium shot framing", "미디엄샷", "허리 위까지 — 제품 사용 동작이 자연스럽게 보이는 만능 구도"),
  o("Full Shot", "full shot framing", "풀샷", "전신이 다 담김 — 모델의 포즈·스타일링·분위기 전체 전달"),
  o("Wide Shot", "wide shot framing", "와이드샷", "인물보다 공간이 큼 — 장소 분위기 중심, 도입/엔딩 컷에 적합"),
  o("Macro", "macro framing", "매크로", "제품 표면 초접사 — 질감·물방울·원료 디테일 강조")
];

export const SCENE_ROLES = [o("Hook", "hook", "훅 (시선 끌기)"), o("Intro", "intro", "인트로"), o("Lifestyle", "lifestyle", "라이프스타일"), o("Model Introduction", "model introduction", "모델 소개"), o("Product Reveal", "product reveal", "제품 등장"), o("Product Detail", "product detail", "제품 디테일"), o("Ingredient", "ingredient", "원료"), o("Benefit", "benefit", "혜택"), o("Usage", "usage", "사용법"), o("Emotional Moment", "emotional moment", "감성 모먼트"), o("Hero Shot", "hero shot", "히어로샷"), o("CTA", "call to action", "CTA (행동 유도)"), o("Brand Ending", "brand ending", "브랜드 엔딩")];
export const SCENE_ASSETS = [o("MODEL", "MODEL", "모델"), o("PRODUCT", "PRODUCT", "제품"), o("LOCATION", "LOCATION", "장소"), o("PROP", "PROP", "소품")];
// 모델 소개형(프레젠터) 영상 전용 연출
export const PRESENT_STYLES = [
  o("친구에게 추천하듯", "speaking casually and genuinely, like recommending a favorite product to a close friend", null, "편하고 진정성 있는 UGC 톤 (틱톡·릴스 기본)"),
  o("활기찬 쇼호스트", "presenting with lively, persuasive home-shopping host energy", null, "텐션 높고 설득력 있는 판매 톤"),
  o("차분한 리뷰어", "explaining in a calm, informative reviewer tone", null, "신뢰감 있는 정보 전달형"),
  o("브이로그 일상톤", "talking naturally as if filming a casual vlog", null, "꾸밈없는 일상 공유 느낌"),
  o("전문가 신뢰톤", "speaking with credible, reassuring professional authority", null, "성분·효능 설명에 어울리는 전문가 느낌")
];
export const PRESENT_GAZES = [
  o("카메라 정면 응시", "looking straight into the camera lens while speaking", null, "시청자와 눈 맞추는 기본 — 몰입도 최고"),
  o("제품 봤다가 카메라로", "glancing down at the product, then back up to the camera", null, "자연스러운 시선 이동 — 리얼한 느낌"),
  o("제품에 집중", "keeping her eyes on the product while explaining it", null, "제품 디테일을 함께 보게 유도"),
  o("화면 밖 인터뷰어", "speaking toward an off-camera interviewer", null, "인터뷰 다큐 느낌 — 신뢰형 광고")
];
export const PRESENT_GESTURES = [
  o("제품 들어 보여주기", "holding the product up toward the camera at chest level", null, "가장 기본이 되는 소개 동작"),
  o("라벨 손끝 포인팅", "pointing at the product label with a fingertip", null, "성분·문구를 강조하고 싶을 때"),
  o("사용 시연하며 설명", "demonstrating how to use the product while talking", null, "스프레이 뿌리기 등 실사용 장면"),
  o("언박싱하며 소개", "unboxing and revealing the product while talking", null, "개봉 리액션 — 후기 톤에 적합"),
  o("손바닥 위에 올려 소개", "presenting the product on an open palm", null, "정갈하고 프리미엄한 느낌"),
  o("양손으로 감싸 강조", "cradling the product with both hands to emphasize it", null, "소중한 물건처럼 — 감성 연출")
];

export const MODEL_ACTIONS = [o("카메라 보기","looking at the camera"), o("미소","smiling naturally"), o("고개 돌리기","turning her head slightly"), o("제품 보기","looking at the product"), o("제품 들기","lifting the product"), o("제품 보여주기","presenting the product to the camera"), o("걷기","walking"), o("앉기","sitting"), o("제품 사용","using the product")];
export const PRODUCT_MOTIONS = [o("Static", "staying still", "정지"), o("Slow Rise", "slowly rising", "천천히 상승"), o("Slow Rotation", "slowly rotating", "천천히 회전"), o("180 Rotation", "rotating 180 degrees", "180도 회전"), o("360 Rotation", "rotating 360 degrees", "360도 회전"), o("Move Toward Camera", "moving toward the camera", "카메라 쪽으로 접근"), o("Slow Fall", "slowly falling", "천천히 낙하"), o("Splash", "triggering a splash", "물 스플래시"), o("Particle Reveal", "revealed through particles", "입자 등장")];
export const CAMERA_MOTIONS = [o("Static", "static camera", "고정"), o("Slow Push-In", "slow push-in", "천천히 다가가기 (푸시인)"), o("Slow Pull-Out", "slow pull-out", "천천히 물러나기 (풀아웃)"), o("Pan Left", "pan left", "왼쪽 팬"), o("Pan Right", "pan right", "오른쪽 팬"), o("Tilt Up", "tilt up", "틸트 업"), o("Tilt Down", "tilt down", "틸트 다운"), o("Orbit Left", "orbit left", "왼쪽 궤도 회전"), o("Orbit Right", "orbit right", "오른쪽 궤도 회전"), o("Dolly", "dolly move", "돌리"), o("Macro Tracking", "macro tracking", "매크로 트래킹"), o("Handheld UGC", "handheld UGC-style movement", "핸드헬드 (UGC)")];
export const SCENE_DURATIONS = [o("1초","1"), o("1.5초","1.5"), o("2초","2"), o("3초","3"), o("4초","4"), o("5초","5")];

export const ORDER_MODES = [o("현재 순서"), o("AI 추천 광고 구조"), o("제품 중심"), o("모델 중심"), o("Story 중심"), o("TikTok Fast Cut", "TikTok Fast Cut", "틱톡 패스트컷"), o("Premium Commercial", "Premium Commercial", "프리미엄 광고형")];
export const TRANSITIONS = [o("Clean Cut", "clean cut", "클린 컷"), o("Match Cut", "match cut", "매치 컷"), o("Motion Match", "motion-matched cut", "모션 매치"), o("Object Match", "object-matched cut", "오브젝트 매치"), o("Camera Match", "camera-matched cut", "카메라 매치"), o("Light Match", "light-matched cut", "조명 매치"), o("Cross Dissolve", "cross dissolve", "크로스 디졸브"), o("Whip Pan", "whip pan", "휩 팬"), o("Push", "push transition", "푸시"), o("Mask", "mask transition", "마스크"), o("Flash", "flash transition", "플래시"), o("Fade", "fade", "페이드"), o("AI Auto", "AI-selected motivated transition", "AI 자동")];
export const FLOW_MODES = [o("원테이크 연결", "one continuous take", "원테이크 연결", "카메라와 인물의 움직임이 씬 경계를 넘어 흐르듯 이어져 한 번에 촬영한 것처럼 보임 (권장)"), o("씬별 컷 편집", "distinct scene cuts", "씬별 컷 편집", "각 씬을 명확한 컷으로 구분 — 정보 전달형·빠른 템포 광고에 적합")];
export const BRIDGE_TYPES = [o("Product Macro", "product macro insert", "제품 매크로"), o("Hand Action", "hand action insert", "손 동작"), o("Environment Detail", "environment detail insert", "배경 디테일"), o("Ingredient Macro", "ingredient macro insert", "원료 매크로"), o("Light Transition", "light transition insert", "조명 전환"), o("Camera Pass", "camera pass insert", "카메라 패스"), o("Abstract Brand", "abstract brand insert", "추상 브랜드")];
export const BRIDGE_DURS = [o("0.3초","0.3"), o("0.5초","0.5"), o("0.8초","0.8"), o("1초","1"), o("1.5초","1.5")];

export const EDIT_STYLES = [o("Slow Luxury", "slow luxury pacing", "슬로우 럭셔리"), o("Smooth Premium", "smooth premium pacing", "스무스 프리미엄"), o("Dynamic Social", "dynamic social pacing", "다이내믹 소셜"), o("Fast TikTok", "fast TikTok pacing", "패스트 틱톡"), o("Cinematic", "cinematic pacing", "시네마틱"), o("Emotional", "emotional pacing", "감성적")];
export const COLOR_GRADES = [o("Warm Premium", "warm premium grade", "웜 프리미엄"), o("Clean White", "clean white grade", "클린 화이트"), o("Natural Wellness", "natural wellness grade", "내추럴 웰니스"), o("Korean Beauty", "Korean beauty grade", "K-뷰티"), o("Soft Pastel", "soft pastel grade", "소프트 파스텔"), o("Golden Lifestyle", "golden lifestyle grade", "골든 라이프스타일"), o("Dark Luxury", "dark luxury grade", "다크 럭셔리"), o("Cinematic Neutral", "cinematic neutral grade", "시네마틱 뉴트럴")];
export const SOUNDS = [o("없음","no sound"), o("Music", "music only", "음악"), o("SFX", "sound effects only", "효과음"), o("Music + SFX", "music and sound effects", "음악 + 효과음"), o("Voice + Music", "voiceover and music", "보이스 + 음악"), o("Voice + Music + SFX", "voiceover, music and sound effects", "보이스 + 음악 + 효과음")];
export const MUSIC_MOODS = [o("Fresh Morning", "fresh morning mood", "프레시 모닝"), o("Premium Minimal", "premium minimal mood", "프리미엄 미니멀"), o("Emotional", "emotional mood", "감성적"), o("Energetic", "energetic mood", "에너제틱"), o("Luxury", "luxury mood", "럭셔리"), o("Wellness", "wellness mood", "웰니스"), o("Beauty", "beauty mood", "뷰티"), o("Modern TikTok", "modern TikTok mood", "모던 틱톡"), o("Cinematic", "cinematic mood", "시네마틱")];
export const SFX_LIST = [o("Product Whoosh", "product whoosh", "제품 휘시 효과음"), o("Soft Impact", "soft impact", "소프트 임팩트"), o("Water", "water", "물소리"), o("Bottle", "bottle", "보틀 소리"), o("Fabric", "fabric", "패브릭 소리"), o("Room Ambience", "room ambience", "룸 앰비언스"), o("Nature", "nature", "자연음"), o("Sparkle", "sparkle", "스파클"), o("Transition Whoosh", "transition whoosh", "전환 휘시")];
export const CAPTION_TYPES = [o("없음","none"), o("Hook", "hook caption", "훅"), o("Product Name", "product name caption", "제품명"), o("Key Benefit", "key benefit caption", "핵심 혜택"), o("Short Caption", "short caption", "짧은 캡션"), o("Brand Slogan", "brand slogan", "브랜드 슬로건"), o("CTA", "CTA caption", "CTA (행동 유도)")];
export const CTAS = [o("제품 알아보기","Learn about the product"), o("지금 확인하기","Check it out now"), o("자세히 보기","See details"), o("구매하기","Shop now"), o("브랜드 만나보기","Meet the brand")];

export const IDENTITY_LOCK_EN = `This is one specific fictional commercial model.
Preserve exactly: facial identity, face shape, eye shape, eye spacing, nose structure, lip shape, jawline, cheekbones, skin tone, hairline, apparent age, overall facial proportions.
Never redesign or reinterpret the person.
Future generations must immediately look like the exact same woman.
No identity drift. No random face changes. No age changes.
Always use the first approved model image as the character reference for every future generation.`;

export const PRODUCT_LOCK_EN = `The uploaded product image is the ABSOLUTE PRODUCT REFERENCE.
Preserve exactly: product shape, package dimensions, container proportions, logo, brand name, product name, label, typography, graphics, cap, materials, colors, surface finish.
Never redesign the product. Never change spelling. Never invent text. Never alter logo or label. Never change packaging proportions.`;

export const VIDEO_NEG_EN = `No face morphing.
No identity drift.
No product deformation.
No logo distortion.
No typography changes.
No flickering.
No random objects.
No sudden camera movement.
No unrealistic physics.
Never generate any new Korean text, English text, subtitles, logos, watermarks, UI elements, or any text inside the video frame. The only text allowed is the existing printed label on the real product.`;

// 최종 통합 영상용 패키지 보존 규칙
export const PACKAGE_PRESERVE_EN = `Preserve every letter and logo that originally exists on the uploaded product package exactly as printed.
Never generate new Korean text, English text, numbers, subtitles, ad copy, logos, watermarks, UI, or any additional text anywhere in the frame.
Never deform, crush, or warp the product package. Never change the spelling of the product name or any printed content on the package.`;

// 이미지·영상 공통 텍스트 생성 금지 규칙 (제품 라벨 원본만 예외)
export const NO_TEXT_EN = `Never generate any new Korean text, English text, subtitles, logos, watermarks, UI elements, or any text inside the image or video frame. The only text allowed is the existing printed label on the real product, reproduced exactly as-is.`;

export const AI_AUTO_NOTE = "Use the previous scene ending and next scene beginning to select the least distracting and most motivated transition. Transition effects should support visual continuity, not call attention to themselves.";

// 쿠팡파트너스 필수 대가성 고지 문구 (공정위 표시광고법 기준)
export const PARTNERS_DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.";
export const PARTNERS_BASE_TAGS = ["쿠팡추천", "쿠팡파트너스", "꿀템추천"];

// 플랫폼별 최적화 프로필 — 영상 편집 지시 + 캡션 스타일이 달라진다
export const PLATFORM_PROFILES = {
  "Instagram Reels": {
    editEn: `PLATFORM ADAPTATION — INSTAGRAM REELS:
Polished, aesthetic, premium feel. Smooth pacing with slightly longer holds on beautiful frames.
Keep all captions, product label moments, and CTA inside Reels safe zones (avoid the top ~15% and bottom ~22% of the frame where the Reels UI overlays).
Color: refined, cohesive, feed-worthy grading. Music: melodic, mood-driven.
The first frame must look good as a static cover thumbnail.`,
    captionNote: "인스타그램용 — 해시태그 넉넉히(8~15개), 줄바꿈으로 가독성, 저장·공유 유도 문구 OK",
    tagCount: 12, tone: "insta", ratio: "9:16"
  },
  "TikTok": {
    editEn: `PLATFORM ADAPTATION — TIKTOK:
Authentic UGC energy. The hook must land within the first 1 second — start mid-action, no slow intro.
Faster cuts, snappier pacing, slightly handheld feel even on product shots.
Keep captions and key visuals inside TikTok safe zones (avoid the right ~12% where buttons stack and the bottom ~25% where the caption overlays).
Color: vivid, high-energy but not oversaturated. Sound: trend-native, beat-synced cuts.
Native, non-ad look performs best — it should feel like a real person's recommendation, not a commercial.`,
    captionNote: "틱톡용 — 짧고 구어체, 해시태그 3~6개만, 첫 줄이 승부처",
    tagCount: 5, tone: "tiktok", ratio: "9:16"
  },
  "YouTube Shorts": {
    editEn: `PLATFORM ADAPTATION — YOUTUBE SHORTS:
Clear narrative flow, strong first 2 seconds. Keep captions inside Shorts safe zones (avoid bottom ~20%).
Slightly more informative tone works well; end screens can hold 0.5s longer for the subscribe/CTA moment.`,
    captionNote: "쇼츠용 — 제목형 첫 줄 + 해시태그 3~5개",
    tagCount: 4, tone: "shorts", ratio: "9:16"
  },
  "Instagram Feed": {
    editEn: `PLATFORM ADAPTATION — INSTAGRAM FEED:
Polished feed aesthetic, works muted (assume no sound). Text overlays must carry the message alone.`,
    captionNote: "피드용 — 저장 가치 있는 정보형 캡션, 해시태그 8~15개",
    tagCount: 12, tone: "insta", ratio: "4:5"
  },
  "Meta Ads": {
    editEn: `PLATFORM ADAPTATION — META ADS:
Direct-response structure: problem → product → proof → CTA. Message must survive muted autoplay.
Front-load the product and benefit within 2 seconds. Clear, readable CTA end card.`,
    captionNote: "광고용 — 혜택 중심 짧은 카피 + 명확한 CTA",
    tagCount: 0, tone: "ads", ratio: "4:5"
  }
};
