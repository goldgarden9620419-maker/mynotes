type TeacherProps = {
  message: string;
  size?: "lg" | "sm";
};

export default function Teacher({ message, size = "lg" }: TeacherProps) {
  const isLg = size === "lg";
  return (
    <div className={`flex items-start gap-3 ${isLg ? "" : "gap-2"}`}>
      <div
        className={`flex shrink-0 items-center justify-center rounded-full border-2 border-accent bg-secondary ${
          isLg ? "h-14 w-14 text-2xl" : "h-9 w-9 text-base"
        }`}
      >
        👩‍🏫
      </div>
      <div
        className={`relative rounded-2xl rounded-tl-sm border border-border bg-card ${
          isLg ? "px-4 py-3 text-sm" : "px-3 py-2 text-xs"
        }`}
      >
        {message}
      </div>
    </div>
  );
}
