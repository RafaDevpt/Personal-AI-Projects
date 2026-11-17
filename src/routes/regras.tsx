import { createFileRoute } from "@tanstack/react-router";
import { CATALOGO_REGRAS } from "@/lib/fiscal/rules2026";

export const Route = createFileRoute("/regras")({
  component: Regras,
});

function Regras() {
  const grupos = Array.from(new Set(CATALOGO_REGRAS.map((r) => r.grupo)));
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header className="space-y-3">
        <h1 className="font-display text-4xl font-semibold tracking-normal">Regras 2026</h1>
        <p className="text-base leading-relaxed text-muted-foreground">
          Estes são todos os valores usados pela aplicação, cada um com a sua fonte legal. Âmbito: trabalho por conta de outrem (categoria A), residente no Continente.
        </p>
      </header>
      {grupos.map((g) => (
        <section key={g} className="card-surface overflow-hidden" aria-labelledby={`g-${g}`}>
          <h2 id={`g-${g}`} className="border-b border-border bg-muted/60 px-5 py-3 text-lg font-semibold">
            {g}
          </h2>
          <dl className="divide-y divide-border">
            {CATALOGO_REGRAS.filter((r) => r.grupo === g).map((r) => (
              <div key={r.nome} className="grid gap-1 px-5 py-4 sm:grid-cols-[1fr_1.2fr] sm:gap-6">
                <dt className="font-semibold">{r.nome}</dt>
                <dd className="space-y-1">
                  <p className="num text-sm leading-relaxed">{r.valor}</p>
                  <p className="text-[13px] text-muted-foreground">Fonte: {r.fonte}</p>
                </dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
    </div>
  );
}
