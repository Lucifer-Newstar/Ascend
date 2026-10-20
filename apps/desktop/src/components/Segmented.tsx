/** Segmented control: a radio group styled as connected buttons (keyboard: arrows via native radios). */
export function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
  disabled,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  disabled?: boolean;
}) {
  return (
    <fieldset className="min-w-0" disabled={disabled}>
      <legend className="sr-only">{label}</legend>
      <div className="inline-flex rounded-lg border border-line-2 bg-panel-2 p-0.5">
        {options.map((o) => {
          const checked = o.value === value;
          return (
            <label
              key={o.value}
              className={`cursor-pointer rounded-md px-3 py-1.5 text-xs font-medium transition-colors has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent ${
                checked ? "bg-accent text-on-accent" : "text-muted hover:text-ink"
              }`}
            >
              <input
                type="radio"
                className="sr-only"
                name={label}
                value={o.value}
                checked={checked}
                onChange={() => onChange(o.value)}
              />
              {o.label}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
