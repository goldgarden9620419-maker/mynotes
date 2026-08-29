import type { ReactNode } from "react";

const UNDERLINE_PATTERN = /\[u\](.*?)\[\/u\]/gs;

export function renderUnderlinedText(text: string): ReactNode[] {
  return text
    .split(UNDERLINE_PATTERN)
    .map((part, i) =>
      i % 2 === 1 ? (
        <span key={`u-${i}`} className="underline decoration-2 underline-offset-[3px] font-semibold">
          {part}
        </span>
      ) : (
        part
      ),
    );
}
