import { useState } from "react";
import { AlertTriangle, Info, Sparkles } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Steps } from "@/components/results/parts";
import { formatEUR, formatPct } from "@/lib/format";
import type { IRSResultado } from "@/lib/fiscal/irs";
import { cn } from "@/lib/utils";

export function ResultadoHero({ r, compact, semRetencoes }: { r: IRSResultado; compact?: boolean; semRetencoes?: boolean | undefined }) {
  const receber = r.resultado >= 0;
  const zero = Math.abs(r.resultado) < 0.005;
  return (
    <div
      aria-live="polite"
      aria-atomic="true"
      className={cn(
        "rounded-2xl min-w-0 p-4 sm:p-5",
        zero ? "bg-muted" : receber ? "bg-receber-soft" : "bg-pagar-soft",
      )}
    >
      <p className="flex flex-wrap items-center gap-2 text-sm font-semibold">
        <span
          aria-hidden
          className={cn("inline-flex size-6 items-center justify-center rounded-full text-sm font-bold", receber ? "bg-receber text-receber-foreground" : "bg-pagar text-pagar-foreground")}
        >
          {receber ? "↓" : "↑"}
        </span>
        {zero ? "Nem recebe nem paga" : receber ? "Vai receber" : "Vai pagar"}
        {semRetencoes && <span className="font-medium text-pagar-ink">(sem retenções indicadas)</span>}
      </p>
      <p
        className={cn(
          "num mt-2 font-bold leading-none tracking-normal",
          compact ? "text-4xl" : "text-4xl sm:text-5xl",
          zero ? "text-foreground" : receber ? "text-receber" : "text-pagar-ink",
        )}
      >
        {formatEUR(Math.abs(r.resultado))}
      </p>
      {!compact && (
        <p className="mt-3 text-sm text-muted-foreground">
          IRS do ano {formatEUR(r.irs)} · já retido {formatEUR(r.ret)} · taxa efetiva {formatPct(r.taxaEfetiva)}
        </p>
      )}
    </div>
  );
}

function Row({ label, value, sinal, strong, muted }: { label: string; value: number; sinal?: string; strong?: boolean; muted?: boolean }) {
  return (
    <tr className={cn("border-b border-border last:border-0", strong && "font-semibold", muted && "text-muted-foreground")}>
      <th scope="row" className={cn("py-2.5 pr-3 text-left", strong ? "font-semibold" : "font-normal")}>{label}</th>
      <td className="num whitespace-nowrap py-2.5 text-right">
        {sinal && value !== 0 ? `${sinal} ` : ""}
        {formatEUR(value)}
      </td>
    </tr>
  );
}

export function TabelaDetalhe({ r }: { r: IRSResultado }) {
  const casado = r.detalhe.length > 1;
  const sum = (k: keyof IRSResultado["detalhe"][number]) => r.detalhe.reduce((s, t) => s + t[k], 0);
  const d = r.deducoes;
  const ded: [string, number][] = (
    [
      ["Dependentes", d.dependentes],
      ["Ascendentes", d.ascendentes],
      ["Incapacidade", d.deficiencia],
      ["Despesas gerais familiares", d.gerais],
      ["Saúde", d.saude],
      ["Educação", d.educacao],
      ["Habitação (rendas)", d.rendas],
      ["Juros crédito habitação", d.juros],
      ["Pensões de alimentos", d.alimentos],
      ["Lares", d.lares],
      ["Trabalho doméstico", d.domestico],
      ["IVA por exigência de fatura", d.iva],
      ["PPR", d.ppr],
    ] as [string, number][]
  ).filter(([, v]) => v > 0);
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <caption className="sr-only">Detalhe do cálculo do IRS</caption>
        <tbody>
          <Row label={casado ? "Rendimento bruto do casal" : "Rendimento bruto"} value={sum("rb")} />
          {sum("excluido") > 0 && <Row label="Rendimento excluído (incapacidade)" value={sum("excluido")} sinal="−" />}
          {sum("isento") > 0 && <Row label="IRS Jovem (isento)" value={sum("isento")} sinal="−" />}
          <Row label="Dedução específica" value={sum("de")} sinal="−" />
          {sum("me") > 0 && <Row label="Mínimo de existência" value={sum("me")} sinal="−" />}
          <Row label="Rendimento coletável" value={sum("rc")} strong />
          <Row label="Coleta (imposto antes de deduções)" value={r.coleta} strong />
          {r.computacoes.some((c) => c.adicional > 0) && (
            <Row label="… inclui adicional de solidariedade" value={r.computacoes.reduce((s, c) => s + c.adicional, 0)} muted />
          )}
          {ded.map(([l, v]) => (
            <Row key={l} label={`Dedução: ${l}`} value={v} sinal="−" />
          ))}
          {d.cortadoLimite > 0.005 && <Row label="Corte pelo limite global de deduções" value={d.cortadoLimite} sinal="+" muted />}
          <Row label="IRS a pagar no ano" value={r.irs} strong />
          <Row label="Retenções na fonte já feitas" value={r.ret} sinal="−" />
          <Row label={r.resultado >= 0 ? "Reembolso" : "A pagar"} value={Math.abs(r.resultado)} strong />
        </tbody>
      </table>
    </div>
  );
}

export function Comparacao({
  conjunta,
  separada,
  recomendado,
  diferenca,
  semRetencoes,
}: {
  conjunta: IRSResultado;
  separada: IRSResultado;
  recomendado: "conjunta" | "separada";
  diferenca: number;
  semRetencoes?: boolean;
}) {
  const [ver, setVer] = useState<"conjunta" | "separada">(recomendado);
  const atual = ver === "conjunta" ? conjunta : separada;
  return (
    <div className="space-y-5">
      <ResultadoHero r={recomendado === "conjunta" ? conjunta : separada} semRetencoes={semRetencoes} />
      <div>
        <h3 className="mb-3 text-[15px] font-semibold">Conjunta ou separada?</h3>
        <div role="radiogroup" aria-label="Ver detalhe da tributação" className="grid grid-cols-2 gap-3">
          {(["conjunta", "separada"] as const).map((m) => {
            const r = m === "conjunta" ? conjunta : separada;
            const sel = ver === m;
            return (
              <button
                key={m}
                type="button"
                role="radio"
                aria-checked={sel}
                onClick={() => setVer(m)}
                className={cn(
                  "relative min-w-0 rounded-2xl border p-3 text-left transition-all",
                  sel ? "border-primary bg-primary-soft ring-1 ring-primary" : "border-border bg-card hover:bg-muted",
                )}
              >
                {recomendado === m && (
                  <span className="mb-2 inline-flex flex-wrap items-center gap-1 rounded-full bg-primary px-2 py-0.5 text-[13px] font-bold text-primary-foreground">
                    <Sparkles className="size-3" aria-hidden /> Recomendado
                  </span>
                )}
                <p className="text-sm font-semibold">{m === "conjunta" ? "Tributação conjunta" : "Tributação separada"}</p>
                <p className={cn("num mt-1 text-lg font-bold", r.resultado >= 0 ? "text-receber" : "text-pagar-ink")}>
                  {r.resultado >= 0 ? "Recebe " : "Paga "}
                  {formatEUR(Math.abs(r.resultado))}
                </p>
              </button>
            );
          })}
        </div>
        <p className="mt-3 text-sm text-muted-foreground">
          {diferenca < 0.01
            ? "As duas opções dão o mesmo resultado."
            : `A opção ${recomendado} é melhor em ${formatEUR(diferenca)}. Pode escolher na declaração.`}
        </p>
      </div>
      <div className="space-y-3">
        <h3 className="text-[15px] font-semibold">Detalhe — tributação {ver}</h3>
        <TabelaDetalhe r={atual} />
        <Steps passos={atual.passos} />
      </div>
    </div>
  );
}

export function Avisos({ avisos }: { avisos: { tipo: "aviso" | "info"; titulo: string; texto: string }[] }) {
  if (!avisos.length) return null;
  return (
    <div className="space-y-3">
      {avisos.map((a) => (
        <Alert key={a.titulo} className={cn("rounded-2xl", a.tipo === "aviso" ? "border-pagar/50 bg-pagar-soft" : "bg-muted")}>
          {a.tipo === "aviso" ? <AlertTriangle className="size-4" aria-hidden /> : <Info className="size-4" aria-hidden />}
          <AlertTitle className="leading-snug">{a.titulo}</AlertTitle>
          <AlertDescription className="text-muted-foreground">{a.texto}</AlertDescription>
        </Alert>
      ))}
    </div>
  );
}
