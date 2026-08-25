import { todayIndex } from "./date";

const AFFIRMATIONS = [
  "나는 매일 조금씩 더 나은 사람이 되고 있다",
  "돈은 나를 좋아하고, 나는 돈을 존중한다",
  "오늘의 작은 습관이 내일의 큰 변화를 만든다",
  "나는 흔들려도 다시 새벽에 일어난다",
  "조용히, 그러나 꾸준히 나는 원하는 삶에 가까워지고 있다",
  "나는 내 시간과 에너지를 소중히 쓴다",
  "나는 이미 변화하고 있는 사람이다",
  "작은 확신이 쌓여 나의 하루를 만든다",
];

export function getTodayAffirmation(): string {
  return AFFIRMATIONS[todayIndex(AFFIRMATIONS.length)];
}
