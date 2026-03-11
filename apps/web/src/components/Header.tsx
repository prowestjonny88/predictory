interface Props {
  title: string;
  date?: string;
  children?: React.ReactNode;
}

export default function Header({ title, date, children }: Props) {
  return (
    <header className="sticky top-0 z-20 bg-white/80 backdrop-blur border-b border-neutral-200 px-6 py-4 flex items-center justify-between gap-4">
      <div>
        <h1 className="text-lg font-bold text-neutral-900">{title}</h1>
        {date && (
          <p className="text-xs text-neutral-400 mt-0.5">
            Plan date: <span className="font-medium text-neutral-600">{date}</span>
          </p>
        )}
      </div>
      {children && <div className="flex items-center gap-3">{children}</div>}
    </header>
  );
}
