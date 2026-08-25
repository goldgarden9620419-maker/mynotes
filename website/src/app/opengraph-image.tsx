import { ImageResponse } from "next/og";

export const alt = "황금정원 — 새벽 기상과 확언으로 바꾼 삶을 기록하는 블로그";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          backgroundColor: "#0f172a",
          backgroundImage:
            "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(99,102,241,0.35), transparent), linear-gradient(to bottom, #0f172a, #131a30)",
          padding: "80px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 90,
            height: 90,
            borderRadius: 40,
            background: "linear-gradient(135deg, #6366f1, #7c3aed)",
            marginBottom: 40,
          }}
        >
          <div
            style={{
              display: "flex",
              width: 34,
              height: 34,
              borderRadius: 17,
              background: "#0f172a",
              opacity: 0.25,
            }}
          />
        </div>
        <div
          style={{
            display: "flex",
            fontSize: 68,
            fontWeight: 700,
            color: "#ffffff",
            textAlign: "center",
            lineHeight: 1.25,
          }}
        >
          확언 한 줄로, 정말 인생이 바뀔까
        </div>
        <div
          style={{
            display: "flex",
            marginTop: 28,
            fontSize: 30,
            color: "#94a3b8",
            textAlign: "center",
          }}
        >
          새벽 기상과 확언으로 삶을 바꾼 실제 경험, 황금정원
        </div>
      </div>
    ),
    { ...size }
  );
}
