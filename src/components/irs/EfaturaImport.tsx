import { useId, useRef, useState } from "react";
import { CircleCheck, Loader2, Upload } from "lucide-react";
import { Field, MoneyInput } from "@/components/form/fields";
import { Button } from "@/components/ui/button";
import { Aviso } from "./DeclaracaoImport";
import type { EfaturaBloco } from "@/lib/fiscal/irs";
import { SETORES_IVA } from "@/lib/fiscal/rules2026";
import { formatEUR } from "@/lib/format";
import { eErroEfatura, parseEfatura, type CampoEfatura, type EfaturaLido } from "@/lib/import/efatura";
import { cn } from "@/lib/utils";

const QUADRADOS: { key: CampoEfatura; label: string }[] = [
  { key: "gerais", label: "Despesas Gerais Familiares" },
  { key: "saude", label: "Saúde" },
  { key: "educacao", label: "Educação" },
  { key: "habitacao", label: "Habitação" },
  { key: "lares", label: "Lares" },
  { key: "domestico", label: "Trabalho Doméstico" },
  ...SETORES_IVA,
];
const nome = (campo: CampoEfatura) => QUADRADOS.find((q) => q.key === campo)?.label ?? campo;
const ehPdf = (f: File) => f.type === "application/pdf" || /\.pdf$/i.test(f.name);

export function EfaturaImport({ idPrefix, bloco, onAplicar }: {
  idPrefix: string;
  bloco: EfaturaBloco;
  onAplicar: (bloco: EfaturaBloco, total: number | null) => void;
}) {
  const inputId = useId();
  const ocupado = useRef(false);
  const [lido, setLido] = useState<EfaturaLido | null>(null);
  const [lendo, setLendo] = useState(false);
  const [erros, setErros] = useState<string[]>([]);
  const [arrastar, setArrastar] = useState(false);
  const [aplicado, setAplicado] = useState(false);

  const ler = async (files: File[]) => {
    if (ocupado.current) return;
    const validos = files.filter((f) => ehPdf(f) || f.type.startsWith("image/"));
    if (!validos.length) return;
    ocupado.current = true;
    setLendo(true);
    setAplicado(false);
    setErros([]);
    try {
      for (const ficheiro of validos) {
        const pdf = ehPdf(ficheiro);
        let texto: string;
        try {
          texto = pdf
            ? await (await import("@/lib/import/pdfText")).extrairTextoPdf(ficheiro)
            : await (await import("@/lib/import/ocr")).extrairTextoImagem(ficheiro);
        } catch {
          setErros((xs) => [...xs, pdf
            ? "Não foi possível abrir este PDF (pode estar danificado ou protegido). Escreva os valores à mão."
            : "Não foi possível ler a imagem neste dispositivo. Escreva os valores à mão."]);
          continue;
        }
        if (pdf && !texto.trim()) {
          setErros((xs) => [...xs, "Este PDF é uma imagem digitalizada. Carregue antes uma captura de ecrã."]);
          continue;
        }
        const r = parseEfatura(texto);
        if (eErroEfatura(r)) {
          setErros((xs) => [...xs, "Não encontrámos os quadrados do e-fatura neste ficheiro. Confirme que se veem os nomes e os valores, ou escreva-os à mão."]);
          continue;
        }
        // Capturas sobrepostas não substituem campos já lidos ou corrigidos pela pessoa.
        setLido((anterior) => ({
          valores: [...(anterior?.valores ?? []), ...r.valores.filter((v) => !anterior?.valores.some((a) => a.campo === v.campo))],
          total: anterior?.total ?? r.total,
        }));
      }
    } finally {
      ocupado.current = false;
      setLendo(false);
    }
  };

  const soma = lido?.valores.reduce((s, v) => s + v.valor, 0) ?? 0;
  const naoLidos = QUADRADOS.filter((q) => !lido?.valores.some((v) => v.campo === q.key));

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => { e.preventDefault(); setArrastar(true); }}
        onDragLeave={() => setArrastar(false)}
        onDrop={(e) => { e.preventDefault(); setArrastar(false); void ler(Array.from(e.dataTransfer.files)); }}
        className={cn("rounded-2xl border-2 border-dashed border-input p-4 text-center transition-colors", arrastar && "border-primary bg-primary-soft")}
      >
        <input
          id={inputId}
          type="file"
          accept="image/*,application/pdf,.pdf"
          multiple
          disabled={lendo}
          className="peer sr-only"
          onChange={(e) => { const fs = Array.from(e.target.files ?? []); e.target.value = ""; void ler(fs); }}
        />
        <label htmlFor={inputId} className="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl bg-card px-4 text-[15px] font-semibold text-primary ring-1 ring-primary/30 hover:bg-primary-soft peer-focus-visible:outline peer-focus-visible:outline-[3px] peer-focus-visible:outline-ring peer-disabled:opacity-50">
          <Upload className="size-5 shrink-0" aria-hidden /> <span>Preencher com captura de ecrã ou PDF</span>
        </label>
        <p className="mt-2 text-[13px] text-muted-foreground">No e-fatura, abra «Deduções Provisórias em IRS», tire uma captura de ecrã (ou guarde a página em PDF) e carregue-a aqui. Se os quadrados não couberem todos numa captura, carregue duas.</p>
        <p className="mt-1 text-[13px] font-medium text-muted-foreground">O ficheiro é lido só neste dispositivo — não é enviado para lado nenhum.</p>
      </div>
      {lendo && <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" aria-hidden /> A ler… numa imagem pode demorar até um minuto.</p>}
      {erros.map((erro, i) => <Aviso key={i} tipo="amber">{erro}</Aviso>)}
      {aplicado && <p role="status" className="flex items-center gap-2 text-sm font-semibold text-primary"><CircleCheck className="size-4" aria-hidden /> Valores aplicados. Confira-os nos quadrados abaixo.</p>}
      {lido && (
        <div className="space-y-3 rounded-2xl bg-muted/50 p-4">
          <p className="text-[15px] font-semibold">Confirme os valores lidos</p>
          <Aviso tipo="info">Leitura automática: confira cada valor com o que vê no e-fatura antes de aplicar.</Aviso>
          <div className="grid gap-4 sm:grid-cols-3">
            {lido.valores.map((v) => (
              <Field key={v.campo} label={nome(v.campo)} htmlFor={`${idPrefix}-lido-${v.campo}`}>
                <MoneyInput id={`${idPrefix}-lido-${v.campo}`} value={v.valor} onChange={(valor) => setLido((r) => r ? { ...r, valores: r.valores.map((x) => x.campo === v.campo ? { ...x, valor } : x) } : r)} />
                <p className="break-words text-[13px] text-muted-foreground">Lido em: “{v.origem}”</p>
                {v.escolhidoEntreDois && <p className="text-[13px] text-muted-foreground">Havia dois valores; ficou o menor, que é a dedução (não a despesa).</p>}
              </Field>
            ))}
          </div>
          {lido.total !== null && <>
            <p className="num text-sm font-semibold">Total lido: {formatEUR(lido.total)}</p>
            {Math.abs(soma - lido.total) > 0.01 && <Aviso tipo="amber">A soma dos valores lidos não bate com o total — falta algum quadrado ou há um valor mal lido.</Aviso>}
          </>}
          {naoLidos.length > 0 && <p className="text-[13px] text-muted-foreground">Não lidos: {naoLidos.map((q) => q.label).join(" · ")} (ficam como estão).</p>}
          <div className="flex flex-wrap gap-2">
            <Button type="button" disabled={lendo} className="min-h-11 flex-1 rounded-xl px-5 sm:flex-none" onClick={() => {
              const novo = { ...bloco, iva: { ...bloco.iva } };
              for (const v of lido.valores) {
                if (v.campo === "gerais" || v.campo === "saude" || v.campo === "educacao" || v.campo === "habitacao" || v.campo === "lares" || v.campo === "domestico") novo[v.campo] = v.valor;
                else novo.iva[v.campo] = v.valor;
              }
              onAplicar(novo, lido.total);
              setLido(null);
              setErros([]);
              setAplicado(true);
            }}>Aplicar</Button>
            <Button type="button" variant="outline" disabled={lendo} className="min-h-11 rounded-xl px-5" onClick={() => { setLido(null); setErros([]); }}>Cancelar</Button>
          </div>
        </div>
      )}
    </div>
  );
}
