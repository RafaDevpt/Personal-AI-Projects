import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { formatEUR, formatPct } from "@/lib/format";
import type { Passo } from "@/lib/fiscal/salario";
import { cn } from "@/lib/utils";

export interface BarSegment {
  label: string;
  value: number;
  className: string;
}

export function StackedBar({ segments, label }: { segments: BarSegment[]; label: string }) {
  const total = segments.reduce((s, x) => s + Math.max(0, x.value), 0);
  return (
    <figure className="space-y-3">
      <div
        role="img"
        aria-label={`${label}: ${segments.map((s) => `${s.label} ${total ? formatPct(s.value / total) : "0%"}`).join(", ")}`}
        className="flex h-4 w-full overflow-hidden rounded-full bg-muted"
      >
        {segments.map((s) =>
          s.value > 0 && total > 0 ? (
            <div key={s.label} className={cn("h-full transition-all duration-500", s.className)} style={{ width: `${(s.value / total) * 100}%` }} />
          ) : null,
        )}
      </div>
      <figcaption>
        <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
          {segments.map((s) => (
            <li key={s.label} className="flex items-center gap-2 whitespace-nowrap">
              <span aria-hidden className={cn("size-3 shrink-0 rounded-sm", s.className)} />
              <span className="text-muted-foreground">{s.label}</span>
              <span className="num font-semibold">{total ? formatPct(s.value / total) : "0%"}</span>
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}

export function Steps({ passos, title = "Como chegámos aqui" }: { passos: Passo[]; title?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <Collapsible open={open} onOpenChange={setOpen} className="rounded-2xl bg-muted/50 print:border-0">
      <CollapsibleTrigger className="flex min-h-12 w-full items-center justify-between rounded-2xl px-4 text-left text-[15px] font-semibold print:hidden">
        {title}
        <ChevronDown className={cn("size-5 transition-transform", open && "rotate-180")} aria-hidden />
      </CollapsibleTrigger>
      <CollapsibleContent forceMount className="data-[state=closed]:hidden print:!block">
        <ol className="divide-y divide-border border-t border-border px-4">
          {passos.map((p, i) => (
            <li key={i} className={cn("flex items-start gap-3 py-3 text-sm", p.sinal === "=" && "font-semibold")}>
              <span aria-hidden className="num w-4 shrink-0 pt-px text-center font-bold text-muted-foreground">
                {p.sinal ?? ""}
              </span>
              <span className="flex-1">
                {p.titulo}
                {p.detalhe && <span className="mt-0.5 block text-[13px] font-normal text-muted-foreground">{p.detalhe}</span>}
              </span>
              {p.valor !== undefined && <span className="num shrink-0 whitespace-nowrap">{formatEUR(p.valor)}</span>}
            </li>
          ))}
        </ol>
      </CollapsibleContent>
    </Collapsible>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-2xl bg-muted/70 p-4">
      <p className="text-[13px] font-medium text-muted-foreground">{label}</p>
      <p className="num mt-1 text-lg font-bold leading-tight">{value}</p>
      {hint && <p className="mt-1 text-[13px] leading-snug text-muted-foreground">{hint}</p>}
    </div>
  );
}

export function SectionCard({ children, className, title, description }: { children: ReactNode; className?: string; title?: string; description?: string }) {
  return (
    <section className={cn("card-surface space-y-5 p-5 sm:p-6", className)}>
      {title && (
        <div className="space-y-1">
          <h2 className="text-xl font-semibold tracking-normal">{title}</h2>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </div>
      )}
      {children}
    </section>
  );
}
