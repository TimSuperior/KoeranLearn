export function Segmented<T extends string>({
  value,
  options,
  onChange
}: {
  value: T;
  options: Array<{ value: T; label: string }>;
  onChange: (value: T) => void;
}) {
  return (
    <div className="grid rounded-app border border-line bg-white p-1" style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`h-9 rounded-app text-sm ${option.value === value ? "bg-ink text-white" : "text-ink/65"}`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
