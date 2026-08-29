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
    <div className="w-full max-w-md rounded-2xl border border-border bg-card px-6 py-8 text-center">
      <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center">
        <svg viewBox="0 0 100 50" className="h-8 w-14" fill="none">
          <polygon points="50,8 90,25 50,42 10,25" fill="var(--accent)" />
          <rect x="35" y="27" width="30" height="14" rx="3" fill="var(--accent)" />
        </svg>
      </div>
      <span className="text-xs font-semibold uppercase tracking-wide text-muted">
        오늘의 확언
      </span>
      <p className="mt-3 text-2xl font-extrabold leading-snug">
        {affirmation.main.map((line, i) => (
          <span key={i}>
            {line}
            {i < affirmation.main.length - 1 && <br />}
          </span>
        ))}
      </p>
      <p className="mt-2 text-sm text-muted">{affirmation.sub}</p>
      <div className="mx-auto mt-4 h-0.5 w-10 rounded-full bg-accent" />
    </div>
  );
}
