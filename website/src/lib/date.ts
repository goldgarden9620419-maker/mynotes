const KST_OFFSET_MS = 9 * 60 * 60 * 1000;

function toKstDateOnly(ms: number): number {
  const kst = new Date(ms + KST_OFFSET_MS);
  return Date.UTC(kst.getUTCFullYear(), kst.getUTCMonth(), kst.getUTCDate());
}

/** Days elapsed since `startDateStr` (YYYY-MM-DD, KST), counting the start date itself as day 1. */
export function daysSinceKst(startDateStr: string): number {
  const start = toKstDateOnly(Date.parse(`${startDateStr}T00:00:00Z`));
  const now = toKstDateOnly(Date.now());
  return Math.floor((now - start) / 86_400_000) + 1;
}

/** Stable index into an array of length `length`, changing once per KST calendar day. */
export function todayIndex(length: number): number {
  const epochDay = Math.floor(toKstDateOnly(Date.now()) / 86_400_000);
  return ((epochDay % length) + length) % length;
}
