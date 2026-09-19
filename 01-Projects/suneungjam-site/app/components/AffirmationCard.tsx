import affirmations from "../../data/affirmations.json";

type Affirmation = {
  date: string;
  main: string[];
  sub: string;
};

function todaysAffirmation(): Affirmation {
  const list = affirmations as Affirmation[];
  const todayIso = new Date().toISOString().slice(0, 10);
  return (
    list.find((a) => a.date === todayIso) ??
    list.reduce((latest, a) => (a.date > latest.date ? a : latest), list[0])
  );
}

export default function AffirmationCard() {
  const affirmation = todaysAffirmation();

  return (
    <div className="flex w-full max-w-md items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3">
      <svg viewBox="0 0 100 50" className="h-5 w-9 shrink-0" fill="none">
        <polygon points="50,8 90,25 50,42 10,25" fill="var(--accent)" />
        <rect x="35" y="27" width="30" height="14" rx="3" fill="var(--accent)" />
      </svg>
      <div className="min-w-0 text-left">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-muted">
          오늘의 확언
        </span>
        <p className="truncate text-sm font-bold">{affirmation.main.join(" ")}</p>
      </div>
    </div>
  );
}
