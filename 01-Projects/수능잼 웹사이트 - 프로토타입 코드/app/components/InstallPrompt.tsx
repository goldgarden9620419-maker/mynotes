"use client";

import { useEffect, useState } from "react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

export default function InstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    function handler(e: Event) {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    }
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  if (!deferred || dismissed) return null;

  async function install() {
    if (!deferred) return;
    await deferred.prompt();
    await deferred.userChoice;
    setDeferred(null);
  }

  return (
    <div className="mb-5 flex w-full max-w-md items-center justify-between gap-3 rounded-2xl border border-border bg-card px-4 py-3">
      <p className="text-sm">
        📲 <span className="font-semibold">홈 화면에 추가</span>하면 앱처럼 바로 열 수 있어요.
      </p>
      <div className="flex shrink-0 gap-2">
        <button
          onClick={install}
          className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground transition active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          설치
        </button>
        <button
          onClick={() => setDismissed(true)}
          aria-label="닫기"
          className="rounded-lg px-2 py-1.5 text-xs text-muted transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
