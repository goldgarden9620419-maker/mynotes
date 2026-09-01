/* ───────── 힉스필드 직접 생성 (window.claude.mcp) — 공용 헬퍼 ───────── */
export const HF_SERVER = "Higgsfield";
export function hfReady() { return typeof window !== "undefined" && window.claude && window.claude.mcp !== undefined; }
export function hfErrMsg(e) {
  const code = e && e.code;
  if (code === "needs_reauth") return "Higgsfield 재연결 필요 — claude.ai 설정 → 커넥터에서 다시 연결해주세요.";
  if (code === "server_not_connected") return "Higgsfield 커넥터가 연결돼 있지 않습니다 — claude.ai 설정 → 커넥터에서 추가해주세요.";
  if (code === "selection_required") return "Higgsfield 커넥터가 여러 개 연결돼 있습니다 — 상단 안내에서 하나를 선택해주세요.";
  if (code === "not_granted" || code === "capability_disabled" || code === "capability_removed") return "이 페이지에 힉스필드 호출 권한이 없습니다 — 새로고침 후 권한을 허용해주세요.";
  if (code === "approval_required" || code === "blocked_by_policy") return "조직 정책상 이 도구 호출이 차단되어 있습니다.";
  if (code === "tool_error") return "힉스필드 오류: " + ((e && e.message) || "생성 실패");
  return "호출 실패" + (code ? " (" + code + ")" : "") + (e && e.message ? ": " + e.message : "");
}
export async function hfCall(tool, input) {
  const r = await window.claude.mcp.callTool(HF_SERVER, tool, input, { cache: false });
  let p = r.payload;
  if (typeof p === "string") { try { p = JSON.parse(p); } catch (err) {} }
  return p;
}
export async function hfWaitJob(jobId) {
  const started = Date.now();
  while (Date.now() - started < 10 * 60 * 1000) {
    const p = await hfCall("jobs_wait", { jobs: [{ index: 0, job_id: jobId }], timeout_seconds: 15 });
    const j = p && p.jobs && p.jobs[0];
    if (j && j.status === "completed") return j;
    if (j && (j.status === "failed" || j.status === "canceled" || j.status === "error")) throw new Error("생성 실패 (" + j.status + ")");
    await new Promise((res) => setTimeout(res, 4000));
  }
  throw new Error("대기 시간 초과 — 힉스필드 사이트에서 결과를 확인해주세요");
}
export const UUID_RE = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;
export function isUuid(v) { return UUID_RE.test((v || "").trim()); }
export function refMedias(ids, role) {
  return (ids || []).filter(Boolean).map((v) => ({ value: v.trim(), role: role || "image" })).filter((m) => m.value);
}
// 참조 ID 형식 검사 — 잘린 ID로 생성 요청이 나가는 것을 사전 차단
export function badRefs(params) {
  return ((params.medias || []).map((m) => m.value).filter((v) => v && !isUuid(v)));
}
// 프리셋 추천 자동 거절 + unlim 질문을 상위로 전달하는 공용 생성 호출
export async function hfGenerate(tool, params) {
  let p = await hfCall(tool, { params });
  if (p && p.notice && p.notice.data && p.notice.data.retry_literal_with) {
    p = await hfCall(tool, { params: { ...params, ...p.notice.data.retry_literal_with } });
  }
  return p;
}
