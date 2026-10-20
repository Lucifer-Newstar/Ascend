/** Tabs for the six training sections that share one logger. */
import type { Section } from "@ascend/shared";

export const SECTIONS: { id: Section; label: string }[] = [
  { id: "gym", label: "Gym" },
  { id: "calisthenics", label: "Calisthenics" },
  { id: "cardio", label: "Cardio" },
  { id: "martial_arts", label: "Martial arts" },
  { id: "flexibility", label: "Flexibility" },
  { id: "meditation", label: "Meditation" },
];

export function SectionTabs({ value, onChange }: { value: Section; onChange: (s: Section) => void }) {
  return (
    <div role="tablist" aria-label="Training section" className="flex flex-wrap gap-1 rounded-xl border border-line bg-panel p-1">
      {SECTIONS.map((s) => {
        const selected = s.id === value;
        return (
          <button
            key={s.id}
            role="tab"
            type="button"
            aria-selected={selected}
            onClick={() => onChange(s.id)}
            className={`rounded-lg px-4 py-2 text-sm transition-colors ${selected ? "bg-accent/10 font-medium text-accent" : "text-muted hover:bg-panel-2 hover:text-ink"}`}
          >
            {s.label}
          </button>
        );
      })}
    </div>
  );
}
