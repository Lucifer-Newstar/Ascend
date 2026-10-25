/**
 * Sources under a knowledge-base answer in the trainer chat (ml-v1). Each line names the
 * passage, who published it and its licence; the link opens in the system browser.
 */
import type { ChatCitation } from "@ascend/shared";

export function Citations({ items }: { items: ChatCitation[] | undefined }) {
  if (!items?.length) return null;
  return (
    <div className="mt-2 border-t border-line pt-1.5" data-testid="citations">
      <p className="text-[10px] uppercase tracking-wider text-muted">Source{items.length > 1 ? "s" : ""}</p>
      <ul className="mt-0.5 space-y-0.5">
        {items.map((c) => (
          <li key={c.passage_id} className="text-[11px] leading-snug text-muted">
            <a href={c.url} target="_blank" rel="noreferrer" className="text-accent hover:underline">{c.title}</a>
            {" · "}
            {c.source}
            {c.ref && c.ref !== c.passage_id ? `, ${c.ref}` : ""} · {c.licence}
          </li>
        ))}
      </ul>
    </div>
  );
}
