import { useId, useRef, useState, type DragEvent, type ReactNode } from "react";
import { AlertTriangle, CircleCheck, FileText, Info, Loader2, Trash2, Upload } from "lucide-react";
import { Field, MoneyInput } from "@/components/form/fields";
import { formatEUR } from "@/lib/format";
import { round2 } from "@/lib/fiscal/money";
import { SS_TRABALHADOR } from "@/lib/fiscal/rules2026";
import { eErroDeclaracao, parseDeclaracao, type DeclaracaoLida } from "@/lib/import/declaracao";
import { cn } from "@/lib/utils";

const ANO_ALVO = 2026;

type Estado = "lendo" | "ok" | "erro_leitura" | "sem_texto" | "nada_encontrado";

interface Item {
  id: number;
  nome: string;
  estado: Estado;
  lida?: DeclaracaoLida;
  rb: number;
  retencoes: number;
  ss: number;
  duplicado: boolean;
}

export interface ValoresDeclaracao {
  sindicais: number;
  rb: number;
  retencoes: number;
  ss: number;
}

const ehPdf = (f: File) => f.type === "application/pdf" || /\.pdf$/i.test(f.name);

export function DeclaracaoImport({ idPrefix, onAplicar }: { idPrefix: string; onAplicar: (v: ValoresDeclaracao) => void }) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const seq = useRef(0);
  const [itens, setItens] = useState<Item[]>([]);
  const [arrastar, setArrastar] = useState(false);
  const [aplicado, setAplicado] = useState(false);

  const patch = (id: number, p: Partial<Item>) => setItens((xs) => xs.map((x) => (x.id === id ? { ...x, ...p } : x)));

  const ler = async (files: File[]) => {
    const pdfs = files.filter(ehPdf);
    if (pdfs.length === 0) return;
    setAplicado(false);
    const novos: Item[] = pdfs.map((f) => ({ id: ++seq.current, nome: f.name, estado: "lendo", rb: 0, retencoes: 0, ss: 0, duplicado: false }));
    setItens((xs) => [...xs, ...novos]);
    let extrair: (f: File) => Promise<string>;
    try {
      ({ extrairTextoPdf: extrair } = await import("@/lib/import/pdfText"));
    } catch {
      novos.forEach((n) => patch(n.id, { estado: "erro_leitura" }));
      return;
    }
    for (let k = 0; k < pdfs.length; k++) {
      const id = novos[k]!.id;
      let texto: string;
      try {
        texto = await extrair(pdfs[k]!);
      } catch {
        patch(id, { estado: "erro_leitura" });
        continue;
      }
      const r = parseDeclaracao(texto, ANO_ALVO);
      if (eErroDeclaracao(r)) {
        patch(id, { estado: r.erro });
        continue;
      }
      setItens((xs) => {
        const duplicado = xs.some(
          (x) => x.id !== id && x.estado === "ok" && !x.duplicado && r.nifEntidade !== null && x.lida?.nifEntidade === r.nifEntidade && x.lida?.rb === r.rb,
        );
        return xs.map((x) =>
          x.id === id
            ? { ...x, estado: "ok", lida: r, rb: r.rb ?? 0, retencoes: r.retencoes ?? 0, ss: r.ss ?? round2((r.rb ?? 0) * SS_TRABALHADOR), duplicado }
            : x,
        );
      });
    }
  };

  const validos = itens.filter((x) => x.estado === "ok" && !x.duplicado);
  const total = validos.reduce((a, x) => ({ rb: a.rb + x.rb, retencoes: a.retencoes + x.retencoes, ss: a.ss + x.ss, sindicais: a.sindicais + (x.lida?.sindicais ?? 0) }), { rb: 0, retencoes: 0, ss: 0, sindicais: 0 });
  const estimativa = validos.some((x) => x.lida?.avisos.includes("ano_diferente"));
  const aLer = itens.some((x) => x.estado === "lendo");

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setArrastar(false);
    void ler(Array.from(e.dataTransfer.files));
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setArrastar(true);
        }}
        onDragLeave={() => setArrastar(false)}
        onDrop={onDrop}
        className={cn(
          "rounded-2xl border-2 border-dashed border-input p-4 text-center transition-colors",
          arrastar && "border-primary bg-primary-soft",
        )}
      >
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className="sr-only"
          onChange={(e) => {
            const fs = Array.from(e.target.files ?? []);
            e.target.value = "";
            void ler(fs);
          }}
        />
        <label
          htmlFor={inputId}
          className="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl bg-card px-4 text-[15px] font-semibold text-primary ring-1 ring-primary/30 hover:bg-primary-soft"
        >
          <Upload className="size-5" aria-hidden /> Carregar declaração de rendimentos (PDF)
        </label>
        <p className="mt-2 text-[13px] text-muted-foreground">
          A declaração anual que a empresa entrega até 20 de janeiro. Pode arrastar o ficheiro para aqui; se teve dois empregadores, carregue as duas.
        </p>
        <p className="mt-1 text-[13px] font-medium text-muted-foreground">O ficheiro é lido só neste dispositivo — não é enviado para lado nenhum.</p>
      </div>

      {aplicado && itens.length === 0 && (
        <p role="status" className="flex items-center gap-2 text-sm font-semibold text-primary">
          <CircleCheck className="size-4" aria-hidden /> Valores da declaração aplicados abaixo. Confirme-os.
        </p>
      )}

      {itens.length > 0 && (
        <div className="space-y-3 rounded-2xl bg-muted/50 p-4" aria-live="polite">
          <p className="text-[15px] font-semibold">Confirme os valores lidos</p>
          {itens.map((it) => (
            <ItemCard
              key={it.id}
              it={it}
              idPrefix={`${idPrefix}-dec-${it.id}`}
              onChange={(p) => patch(it.id, p)}
              onRemover={() => setItens((xs) => xs.filter((x) => x.id !== it.id))}
            />
          ))}

          {validos.length > 1 && (
            <div className="rounded-xl bg-muted p-3 text-sm">
              <p className="font-semibold">Total das {validos.length} declarações</p>
              <p className="num text-muted-foreground">
                Bruto {formatEUR(total.rb)} · IRS retido {formatEUR(total.retencoes)} · Seg. Social {formatEUR(total.ss)}
              </p>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={validos.length === 0 || aLer}
              onClick={() => {
                onAplicar({ rb: round2(total.rb), retencoes: round2(total.retencoes), ss: round2(total.ss), sindicais: round2(total.sindicais) });
                setItens([]);
                setAplicado(true);
              }}
              className="inline-flex min-h-11 flex-1 items-center justify-center rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 sm:flex-none"
            >
              {estimativa ? "Usar como estimativa" : "Aplicar"}
            </button>
            <button
              type="button"
              onClick={() => setItens([])}
              className="inline-flex min-h-11 items-center justify-center rounded-xl border border-input px-5 text-sm font-semibold hover:bg-muted"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export function Aviso({ tipo, children }: { tipo: "amber" | "info"; children: ReactNode }) {
  const Icon = tipo === "amber" ? AlertTriangle : Info;
  return (
    <p className={cn("flex gap-2 rounded-xl p-3 text-sm", tipo === "amber" ? "bg-pagar-soft text-foreground" : "bg-primary-soft text-foreground")}>
      <Icon className={cn("mt-0.5 size-4 shrink-0", tipo === "amber" ? "text-pagar-ink" : "text-primary")} aria-hidden />
      <span>{children}</span>
    </p>
  );
}

function Fonte({ texto }: { texto?: string | undefined }) {
  if (!texto) return <p className="text-[13px] text-muted-foreground">Não encontrado no PDF — escreva o valor.</p>;
  return <p className="break-words text-[13px] text-muted-foreground">Lido em: “{texto}”</p>;
}

function ItemCard({ it, idPrefix, onChange, onRemover }: { it: Item; idPrefix: string; onChange: (p: Partial<Item>) => void; onRemover: () => void }) {
  const l = it.lida;
  return (
    <div className="space-y-3 border-t border-border pt-3">
      <div className="flex items-center gap-2">
        <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        <p className="min-w-0 flex-1 truncate text-sm font-semibold">{it.nome}</p>
        <button
          type="button"
          onClick={onRemover}
          aria-label={`Remover ${it.nome}`}
          className="inline-flex size-11 shrink-0 items-center justify-center rounded-xl text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <Trash2 className="size-4" aria-hidden />
        </button>
      </div>

      {it.estado === "lendo" && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" aria-hidden /> A ler o PDF…
        </p>
      )}
      {it.estado === "erro_leitura" && <Aviso tipo="amber">Não foi possível abrir este PDF (pode estar danificado ou protegido). Introduza os valores à mão.</Aviso>}
      {it.estado === "sem_texto" && <Aviso tipo="amber">Este PDF parece ser uma digitalização (imagem) e não tem texto. Introduza os valores à mão.</Aviso>}
      {it.estado === "nada_encontrado" && (
        <Aviso tipo="amber">
          Não encontrámos os valores neste PDF. Introduza-os à mão — e se quiser ajudar, diga-nos que programa de salários a sua empresa usa.
        </Aviso>
      )}

      {it.estado === "ok" && l && (
        <>
          {it.duplicado && <Aviso tipo="amber">Parece o mesmo ficheiro duas vezes — não vamos somá-lo outra vez.</Aviso>}
          <p className="text-[13px] text-muted-foreground">
            Ano: <span className="font-semibold text-foreground">{l.ano ?? "não indicado"}</span> · NIF da entidade:{" "}
            <span className="num font-semibold text-foreground">{l.nifEntidade ?? "não encontrado"}</span>
          </p>
          {l.avisos.includes("ano_diferente") && l.ano !== null && (
            <Aviso tipo="amber">
              Esta declaração é de {l.ano}. Para o IRS de 2026 precisa da declaração de 2026 (a empresa entrega até 20 de janeiro de 2027). Pode usá-la como
              estimativa.
            </Aviso>
          )}
          {l.avisos.includes("valores_em_falta") && <Aviso tipo="amber">Faltam valores nesta declaração — preencha-os antes de aplicar.</Aviso>}
          {!it.duplicado && (
            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Rendimento bruto" htmlFor={`${idPrefix}-rb`}>
                <MoneyInput id={`${idPrefix}-rb`} value={it.rb} onChange={(v) => onChange({ rb: v })} />
                <Fonte texto={l.fontes.rb} />
              </Field>
              <Field label="IRS retido" htmlFor={`${idPrefix}-ret`}>
                <MoneyInput id={`${idPrefix}-ret`} value={it.retencoes} onChange={(v) => onChange({ retencoes: v })} />
                <Fonte texto={l.fontes.retencoes} />
              </Field>
              <Field label="Segurança Social" htmlFor={`${idPrefix}-ss`}>
                <MoneyInput id={`${idPrefix}-ss`} value={it.ss} onChange={(v) => onChange({ ss: v })} />
                <Fonte texto={l.fontes.ss} />
              </Field>
            </div>
          )}
          {l.avisos.includes("ss_fora_do_esperado") && <Aviso tipo="amber">A Segurança Social não corresponde a ~11% do bruto — confirme.</Aviso>}
          {(l.isentos ?? 0) > 0 && (
            <Aviso tipo="info">
              A declaração indica {formatEUR(l.isentos ?? 0)} de rendimentos isentos — se tem IRS Jovem, indique o ano de benefício abaixo.
            </Aviso>
          )}
          {l.sindicais > 0 && <p className="text-[13px] text-muted-foreground">Quotizações sindicais indicadas: {formatEUR(l.sindicais)}.</p>}
        </>
      )}
    </div>
  );
}
