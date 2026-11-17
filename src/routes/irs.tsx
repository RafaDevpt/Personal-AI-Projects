import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { AlertTriangle, ArrowLeft, ArrowRight, Calculator, Printer, ReceiptText, RotateCcw, Trash2, UserPlus } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import { formatEUR, formatPct } from "@/lib/format";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { EfaturaForm, type BlocoUI } from "@/components/irs/EfaturaForm";
import { DeclaracaoImport } from "@/components/irs/DeclaracaoImport";
import { CheckRow, Field, MoneyInput, NumberInput, Segmented, SelectInput, Stepper } from "@/components/form/fields";
import { SectionCard } from "@/components/results/parts";
import { Avisos, Comparacao, ResultadoHero, TabelaDetalhe } from "@/components/irs/IrsResult";
import { Steps } from "@/components/results/parts";
import { usePersistentState } from "@/hooks/use-persistent-state";
import { calcIRS, compararTributacao, type AgregadoInput, type EfaturaBloco, type ModoDespesas } from "@/lib/fiscal/irs";
import { estimarAnualDoMensal } from "@/lib/fiscal/salario";
import {
  DED_GERAIS,
  DED_DEFICIENCIA,
  IAS,
  RENDIMENTO_DEFICIENCIA,
  IDADE_PADRAO,
  IRS_JOVEM_ANOS_MAX,
  MIN_EXIST_VR,
  SS_TRABALHADOR,
} from "@/lib/fiscal/rules2026";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/irs")({
  component: IrsPage,
});

interface TitularState {
  rb: number;
  ss: number | null;
  retencoes: number;
  irsJovemAno: number;
  idade: number;
  ppr: number;
  sindicais: number;
  incapacidade: 0 | 60 | 90;
  mensal: number;
  novembro50: boolean;
  natalNovembro: boolean;
}

interface IrsState {
  passo: number;
  casado: boolean;
  dependentes: number[];
  dependentesAlternada: boolean[];
  dependentesDeficiencia: number;
  dependentesDeficiencia90: number;
  ascendentesDeficiencia: number;
  trabalhoDomestico: number;
  ascendentes: number;
  titulares: [TitularState, TitularState];
  despGerais: number;
  saude: number;
  educacao: number;
  rendas: number;
  jurosHab: number;
  lares: number;
  ivaFatura: number;
  pensaoAlimentos: number;
  /** Versão do formato guardado (2 = com modo e-fatura). */
  versao: number;
  modoDespesas: ModoDespesas;
  efatura: { titulares: [EfaturaBloco, EfaturaBloco]; dependentes: EfaturaBloco };
  /** Valores "Deduções Provisórias em IRS" do Portal, só para confirmação. */
  efaturaPortal: { t0: number; t1: number; dep: number };
}

const B0: EfaturaBloco = { gerais: 0, saude: 0, educacao: 0, habitacao: 0, lares: 0, domestico: 0, iva: {} };

const T0: TitularState = { rb: 0, ss: null, retencoes: 0, irsJovemAno: 0, idade: IDADE_PADRAO, ppr: 0, sindicais: 0, incapacidade: 0, mensal: 0, novembro50: true, natalNovembro: true };

const INICIAL: IrsState = {
  passo: 0,
  casado: false,
  dependentes: [],
  dependentesAlternada: [],
  dependentesDeficiencia: 0,
  dependentesDeficiencia90: 0,
  ascendentesDeficiencia: 0,
  trabalhoDomestico: 0,
  ascendentes: 0,
  titulares: [{ ...T0, rb: 21000, retencoes: 2350 }, { ...T0 }],
  despGerais: 0,
  saude: 0,
  educacao: 0,
  rendas: 0,
  jurosHab: 0,
  lares: 0,
  ivaFatura: 0,
  pensaoAlimentos: 0,
  versao: 2,
  modoDespesas: "efatura",
  efatura: { titulares: [B0, B0], dependentes: B0 },
  efaturaPortal: { t0: 0, t1: 0, dep: 0 },
};

const num = (x: unknown, d = 0) => (typeof x === "number" && Number.isFinite(x) ? x : d);
type Solto<T> = { [K in keyof T]?: unknown };
function solto<T>(x: unknown): Solto<T> {
  return x && typeof x === "object" && !Array.isArray(x) ? (x as Solto<T>) : {};
}

function limparBloco(raw: unknown): EfaturaBloco {
  const x = solto<EfaturaBloco>(raw);
  const iva: Record<string, number> = {};
  for (const [k, v] of Object.entries(solto<Record<string, unknown>>(x.iva))) iva[k] = Math.max(0, num(v));
  return { gerais: num(x.gerais), saude: num(x.saude), educacao: num(x.educacao), habitacao: num(x.habitacao), lares: num(x.lares), domestico: Math.max(0, num(x.domestico)), iva };
}

/** Lê o estado guardado de forma defensiva. O formato antigo (sem versão) tinha deduções do e-fatura
 * escritas como "valores gastos" — essa parte é reposta; agregado e rendimentos mantêm-se. */
function migrarIrs(input: unknown, ini: IrsState): IrsState {
  if (!input || typeof input !== "object") return ini;
  const raw = solto<IrsState>(input);
  const tit = Array.isArray(raw.titulares) ? raw.titulares : [];
  const titulares = [0, 1].map((i) => {
    const t = solto<TitularState>(tit[i]);
    const b = ini.titulares[i as 0 | 1];
    return {
      rb: num(t.rb, b.rb), ss: t.ss === null || t.ss === undefined ? null : num(t.ss), retencoes: num(t.retencoes, b.retencoes),
      irsJovemAno: num(t.irsJovemAno), idade: num(t.idade, IDADE_PADRAO), ppr: num(t.ppr), mensal: num(t.mensal),
      sindicais: Math.max(0, num(t.sindicais)),
      incapacidade: t.incapacidade === 60 || t.incapacidade === 90 ? t.incapacidade : 0,
      novembro50: typeof t.novembro50 === "boolean" ? t.novembro50 : true,
      natalNovembro: typeof t.natalNovembro === "boolean" ? t.natalNovembro : true,
    };
  }) as [TitularState, TitularState];
  const dependentes = Array.isArray(raw.dependentes) ? raw.dependentes.map((x) => num(x, 10)) : [];
  const ascendentes = Math.max(0, Math.floor(num(raw.ascendentes)));
  const dependentesDeficiencia = Math.min(dependentes.length, Math.max(0, Math.floor(num(raw.dependentesDeficiencia))));
  const base: IrsState = {
    ...ini,
    passo: Math.min(3, Math.max(0, num(raw.passo))),
    casado: raw.casado === true,
    dependentes,
    dependentesAlternada: dependentes.map((_, i) => Array.isArray(raw.dependentesAlternada) && raw.dependentesAlternada[i] === true),
    dependentesDeficiencia,
    dependentesDeficiencia90: Math.min(dependentesDeficiencia, Math.max(0, Math.floor(num(raw.dependentesDeficiencia90)))),
    ascendentes,
    ascendentesDeficiencia: Math.min(ascendentes, Math.max(0, Math.floor(num(raw.ascendentesDeficiencia)))),
    trabalhoDomestico: Math.max(0, num(raw.trabalhoDomestico)),
    titulares,
    pensaoAlimentos: num(raw.pensaoAlimentos),
  };
  if (raw.versao !== 2) return base; // formato antigo: passo 3 recomeça em modo e-fatura
  const ef = solto<IrsState["efatura"]>(raw.efatura);
  const efT = Array.isArray(ef.titulares) ? ef.titulares : [];
  const portal = solto<IrsState["efaturaPortal"]>(raw.efaturaPortal);
  return {
    ...base,
    despGerais: num(raw.despGerais), saude: num(raw.saude), educacao: num(raw.educacao), rendas: num(raw.rendas),
    jurosHab: num(raw.jurosHab), lares: num(raw.lares), ivaFatura: num(raw.ivaFatura),
    modoDespesas: raw.modoDespesas === "gasto" ? "gasto" : "efatura",
    efatura: { titulares: [limparBloco(efT[0]), limparBloco(efT[1])], dependentes: limparBloco(ef.dependentes) },
    efaturaPortal: { t0: num(portal.t0), t1: num(portal.t1), dep: num(portal.dep) },
  };
}

/** Rendimento acima do mínimo de existência sem retenções indicadas — quase sempre esquecimento. */
const faltaRetencoes = (t: TitularState) => t.rb > MIN_EXIST_VR && t.retencoes === 0;

const PASSOS = ["Agregado", "Rendimentos", "Despesas", "Resultado"];

function IrsPage() {
  const [s, setS, reset] = usePersistentState<IrsState>("irs", INICIAL, { migrate: migrarIrs });
  const set = <K extends keyof IrsState>(k: K, v: IrsState[K]) => setS((p) => ({ ...p, [k]: v }));
  const setTit = (i: 0 | 1, patch: Partial<TitularState>) =>
    setS((p) => {
      const t = [...p.titulares] as [TitularState, TitularState];
      t[i] = { ...t[i], ...patch };
      return { ...p, titulares: t };
    });

  const agregado: AgregadoInput = useMemo(
    () => ({
      titulares: s.titulares.map((t) => ({ rb: t.rb, ss: t.ss, retencoes: t.retencoes, irsJovemAno: t.irsJovemAno, idade: t.idade, ppr: t.ppr, sindicais: t.sindicais, incapacidade: t.incapacidade })),
      casado: s.casado,
      conjunta: false,
      dependentesIdades: s.dependentes,
      dependentesAlternada: s.dependentesAlternada,
      dependentesDeficiencia: s.dependentesDeficiencia,
      dependentesDeficiencia90: s.dependentesDeficiencia90,
      ascendentesDeficiencia: s.ascendentesDeficiencia,
      trabalhoDomestico: s.trabalhoDomestico,
      ascendentes: s.ascendentes,
      despGerais: s.despGerais,
      saude: s.saude,
      educacao: s.educacao,
      rendas: s.rendas,
      jurosHab: s.jurosHab,
      lares: s.lares,
      ivaFatura: s.ivaFatura,
      pensaoAlimentos: s.pensaoAlimentos,
      modoDespesas: s.modoDespesas,
      efaturaTitulares: s.efatura.titulares,
      efaturaDependentes: s.dependentes.length > 0 ? s.efatura.dependentes : undefined,
    }),
    [s],
  );

  const resultado = useMemo(() => {
    if (s.casado) {
      const c = compararTributacao(agregado);
      return { tipo: "casal" as const, ...c, melhor: c.recomendado === "conjunta" ? c.conjunta : c.separada };
    }
    const r = calcIRS(agregado);
    return { tipo: "individual" as const, r, melhor: r };
  }, [agregado, s.casado]);

  const avisos = useMemo(() => {
    const out: { tipo: "aviso" | "info"; titulo: string; texto: string }[] = [
      {
        tipo: "info",
        titulo: "Isto é uma simulação",
        texto: "Serve para ter uma ideia do resultado. O valor que conta é o que as Finanças calcularem quando entregar a declaração no Portal das Finanças.",
      },
    ];
    const ativos: TitularState[] = s.casado ? s.titulares : [s.titulares[0]];
    const sujeitos = ativos.length;
    const gerais = resultado.melhor.deducoes.gerais;
    if (ativos.some(faltaRetencoes)) {
      out.push({
        tipo: "aviso",
        titulo: "Falta indicar as retenções na fonte — sem elas o resultado mostra o imposto todo como 'a pagar'.",
        texto: "Está no recibo de dezembro (IRS acumulado) ou no Portal das Finanças → 'Rendimentos e Retenções'. Volte ao passo 2 para as indicar.",
      });
    }
    if (ativos.some((t) => t.rb > 0 && t.rb <= MIN_EXIST_VR) && gerais < DED_GERAIS.limitePorSujeito * sujeitos - 0.005) {
      out.push({
        tipo: "aviso",
        titulo: "Com o salário mínimo precisa de ~715 € de despesas gerais no e-fatura para ficar isento",
        texto: "Peça fatura com NIF nas compras do dia a dia (supermercado, combustível, contas da casa) para chegar aos 250 € de dedução.",
      });
    }
    if (resultado.tipo === "casal" && resultado.separada.deducoes.cortadoLimite > 0) out.push({
      tipo: "info", titulo: "Tributação separada: limite das deduções",
      texto: "Dividimos o limite global das deduções a meio por cada um, como a lei manda fazer com os limites do agregado (art. 78.º n.º 14 do CIRS). A lei não o diz expressamente para este limite, por isso confirme na simulação oficial do Portal das Finanças.",
    });
    if (ativos.some((t) => t.irsJovemAno > 0)) out.push({
      tipo: "info", titulo: "IRS Jovem: valor aproximado",
      texto: "A parte isenta conta para a taxa do resto do rendimento (art. 12.º-B do CIRS). As Finanças não publicaram um exemplo do cálculo final, por isso o valor pode ter pequenas diferenças.",
    });
    return out;
  }, [s, resultado]);

  const passo = s.passo;
  const semRetencoes = (s.casado ? s.titulares : [s.titulares[0]]).some(faltaRetencoes);
  const setBloco = (quem: 0 | 1 | "dep", b: EfaturaBloco) =>
    setS((p) => {
      const titulares = [...p.efatura.titulares] as [EfaturaBloco, EfaturaBloco];
      if (quem === "dep") return { ...p, efatura: { ...p.efatura, dependentes: b } };
      titulares[quem] = b;
      return { ...p, efatura: { ...p.efatura, titulares } };
    });
  const setPortal = (k: "t0" | "t1" | "dep", v: number) => setS((p) => ({ ...p, efaturaPortal: { ...p.efaturaPortal, [k]: v } }));
  const blocos: BlocoUI[] = [
    ...(s.casado ? ([0, 1] as const) : ([0] as const)).map((i) => ({
      id: `ef-t${i}`,
      titulo: `Titular ${i + 1}`,
      bloco: s.efatura.titulares[i],
      portal: s.efaturaPortal[i === 0 ? "t0" : "t1"],
      onChange: (b: EfaturaBloco) => setBloco(i, b),
      onPortal: (v: number) => setPortal(i === 0 ? "t0" : "t1", v),
    })),
    ...(s.dependentes.length > 0
      ? [{ id: "ef-dep", titulo: "Dependentes (soma de todos)", bloco: s.efatura.dependentes, portal: s.efaturaPortal.dep, onChange: (b: EfaturaBloco) => setBloco("dep", b), onPortal: (v: number) => setPortal("dep", v) }]
      : []),
  ];
  const irPara = (n: number) => {
    set("passo", Math.max(0, Math.min(PASSOS.length - 1, n)));
    if (typeof window !== "undefined") window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="space-y-6">
      <header className="grid min-w-0 gap-3 sm:flex sm:items-end sm:justify-between">
        <div className="space-y-1">
          <h1 className="font-display text-3xl font-semibold tracking-normal sm:text-4xl">IRS 2026 — vou receber ou pagar?</h1>
          <p className="text-muted-foreground">Rendimentos de 2026 · trabalho por conta de outrem · Continente</p>
        </div>
        <div className="flex gap-2 print:hidden">
          <button type="button" onClick={() => window.print()} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-input px-4 text-sm font-semibold hover:bg-muted">
            <Printer className="size-4" aria-hidden /> Imprimir
          </button>
          <button type="button" onClick={reset} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-input px-4 text-sm font-semibold hover:bg-muted">
            <RotateCcw className="size-4" aria-hidden /> Limpar dados
          </button>
        </div>
      </header>

      {/* Progresso */}
      <nav aria-label="Passos do assistente" className="space-y-3 print:hidden">
        <div
          className="h-2 overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-valuemin={1}
          aria-valuemax={PASSOS.length}
          aria-valuenow={passo + 1}
          aria-valuetext={`Passo ${passo + 1} de ${PASSOS.length}: ${PASSOS[passo]}`}
        >
          <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${((passo + 1) / PASSOS.length) * 100}%` }} />
        </div>
        <ol className="grid grid-cols-4 gap-1">
          {PASSOS.map((p, i) => (
            <li key={p}>
              <button
                type="button"
                onClick={() => irPara(i)}
                aria-current={i === passo ? "step" : undefined}
                className={cn(
                  "flex min-h-11 w-full flex-col items-center justify-center rounded-xl px-1 text-[13px] font-semibold transition-colors sm:flex-row sm:gap-2 sm:text-sm",
                  i === passo ? "text-primary" : i < passo ? "text-foreground" : "text-muted-foreground",
                )}
              >
                <span className={cn("inline-flex size-6 items-center justify-center rounded-full text-[13px]", i <= passo ? "bg-primary text-primary-foreground" : "bg-muted")}>
                  {i + 1}
                </span>
                {p}
              </button>
            </li>
          ))}
        </ol>
      </nav>

      <div className={cn("grid items-start gap-6", passo < 3 && "lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]")}>
        <div className="space-y-5">
          {passo === 0 && (
            <SectionCard title="1. Agregado familiar" description="Quem entra na declaração.">
              <Field as="fieldset" label="Estado civil" help="Casados e unidos de facto podem entregar uma declaração em conjunto. Calculamos sempre as duas opções e indicamos a melhor.">
                <Segmented
                  label="Estado civil"
                  value={s.casado ? "c" : "s"}
                  onChange={(v) => set("casado", v === "c")}
                  options={[
                    { value: "s", label: "Sozinho(a)", sub: "solteiro, divorciado, viúvo" },
                    { value: "c", label: "Casado(a)", sub: "ou unido de facto" },
                  ]}
                />
              </Field>
              <Field as="fieldset" label="Dependentes" help="Filhos ou menores a cargo, ou maiores até 25 anos a estudar sem rendimentos acima do salário mínimo. A idade conta para o valor da dedução.">
                <Stepper
                  label="dependentes"
                  value={s.dependentes.length}
                  onChange={(n) =>
                    setS((p) => {
                      const dependentes = n > p.dependentes.length ? [...p.dependentes, ...Array<number>(n - p.dependentes.length).fill(10)] : p.dependentes.slice(0, n);
                      const dependentesDeficiencia = Math.min(p.dependentesDeficiencia, n);
                      return { ...p, dependentes, dependentesAlternada: dependentes.map((_, i) => p.dependentesAlternada[i] ?? false), dependentesDeficiencia, dependentesDeficiencia90: Math.min(p.dependentesDeficiencia90, dependentesDeficiencia) };
                    })
                  }
                />
              </Field>
              {s.dependentes.length > 0 && (
                <div className="grid gap-3 sm:grid-cols-2">
                  {s.dependentes.map((idade, i) => (
                    <div key={i}>
                    <div className="flex items-end gap-2">
                      <Field label={`Idade do ${i + 1}.º dependente`} htmlFor={`dep-${i}`} className="flex-1" hint="Idade a 31 de dezembro de 2026">
                        <NumberInput id={`dep-${i}`} value={idade} max={30} onChange={(v) => set("dependentes", s.dependentes.map((x, j) => (j === i ? v : x)))} />
                      </Field>
                      <button
                        type="button"
                        aria-label={`Remover ${i + 1}.º dependente`}
                        onClick={() => setS((p) => {
                          const dependentes = p.dependentes.filter((_, j) => j !== i);
                          const dependentesDeficiencia = Math.min(p.dependentesDeficiencia, dependentes.length);
                          return { ...p, dependentes, dependentesAlternada: p.dependentesAlternada.filter((_, j) => j !== i), dependentesDeficiencia, dependentesDeficiencia90: Math.min(p.dependentesDeficiencia90, dependentesDeficiencia) };
                        })}
                        className="mb-6 inline-flex size-12 items-center justify-center rounded-xl text-muted-foreground hover:bg-muted hover:text-foreground"
                      >
                        <Trash2 className="size-5" aria-hidden />
                      </button>
                    </div>
                    <CheckRow checked={s.dependentesAlternada[i] ?? false} onChange={(v) => set("dependentesAlternada", s.dependentesAlternada.map((x, j) => j === i ? v : x))} helpLabel="Residência alternada" help="Assinale se os pais estão separados, a guarda é partilhada e a criança vive alternadamente com os dois, com acordo comunicado às Finanças. A dedução do dependente é dividida a meio.">
                      Vive em residência alternada
                    </CheckRow>
                    </div>
                  ))}
                </div>
              )}
              <Field as="fieldset" label="Ascendentes a cargo" help="Pais ou avós que vivem consigo e têm rendimentos iguais ou inferiores à pensão mínima.">
                <Stepper label="ascendentes" value={s.ascendentes} max={4} onChange={(v) => setS((p) => ({ ...p, ascendentes: v, ascendentesDeficiencia: Math.min(p.ascendentesDeficiencia, v) }))} />
              </Field>
              <Collapsible>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" className="min-h-11 w-full justify-start whitespace-normal text-left">Alguém tem incapacidade de 60% ou mais?</Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-4 pt-3">
                  <p className="text-sm text-muted-foreground">Conta quem tem atestado médico de incapacidade multiúso com 60% ou mais. A incapacidade do próprio indica-se no passo 2.</p>
                  {s.dependentes.length > 0 && <Field as="fieldset" label="Dependentes com incapacidade">
                    <Stepper label="dependentes com incapacidade" value={s.dependentesDeficiencia} max={s.dependentes.length} onChange={(v) => setS((p) => ({ ...p, dependentesDeficiencia: v, dependentesDeficiencia90: Math.min(p.dependentesDeficiencia90, v) }))} />
                  </Field>}
                  {s.dependentesDeficiencia > 0 && <Field as="fieldset" label="Desses, com 90% ou mais">
                    <Stepper label="dependentes com 90% ou mais" value={s.dependentesDeficiencia90} max={s.dependentesDeficiencia} onChange={(v) => set("dependentesDeficiencia90", v)} />
                  </Field>}
                  {s.ascendentes > 0 && <Field as="fieldset" label="Ascendentes com incapacidade">
                    <Stepper label="ascendentes com incapacidade" value={s.ascendentesDeficiencia} max={s.ascendentes} onChange={(v) => set("ascendentesDeficiencia", v)} />
                  </Field>}
                </CollapsibleContent>
              </Collapsible>
            </SectionCard>
          )}

          {passo === 1 &&
            (s.casado ? ([0, 1] as const) : ([0] as const)).map((i) => (
              <TitularForm
                key={i}
                idx={i}
                t={s.titulares[i]}
                casado={s.casado}
                onChange={(patch) => setTit(i, patch)}
                situacao={s.casado ? (s.titulares[i === 0 ? 1 : 0].rb > 0 || s.titulares[i === 0 ? 1 : 0].mensal > 0 ? "casado_dois" : "casado_unico") : "nao_casado"}
                dependentes={s.dependentes.length}
              />
            ))}

          {passo === 2 && (
            <SectionCard
              title="3. Despesas"
              description={
                s.modoDespesas === "efatura"
                  ? "Abra o e-fatura → Deduções Provisórias em IRS (ano 2026) e copie o valor grande de cada quadrado — não o total de despesas por baixo."
                  : "Indique quanto gastou em cada tipo de despesa. Para o casal, indique o total do agregado."
              }
            >
              {s.modoDespesas === "efatura" ? (
                <>
                  <EfaturaForm blocos={blocos} />
                  <button type="button" onClick={() => set("modoDespesas", "gasto")} className="min-h-11 text-left text-sm font-semibold text-primary underline underline-offset-4 hover:no-underline">
                    Não tenho o e-fatura — introduzir valores gastos
                  </button>
                </>
              ) : (
              <>
              <button type="button" onClick={() => set("modoDespesas", "efatura")} className="inline-flex min-h-11 items-center gap-2 text-left text-sm font-semibold text-primary underline underline-offset-4 hover:no-underline">
                <ReceiptText className="size-4" aria-hidden /> Tenho o e-fatura — copiar as deduções já calculadas
              </button>
              <div className="grid gap-5 sm:grid-cols-2">
                <Field label="Despesas gerais familiares" htmlFor="gerais" help="Total de faturas com NIF de supermercado, roupa, combustível, água, luz, telecomunicações, etc. Deduz 35%, até 250 € por pessoa. Se vive sozinho(a) com filhos a cargo: 45%, até 335 €.">
                  <MoneyInput id="gerais" value={s.despGerais} onChange={(v) => set("despGerais", v)} />
                </Field>
                <Field label="Saúde" htmlFor="saude" help="Consultas, farmácia, exames, seguros de saúde. Deduz 15%, até 1 000 €.">
                  <MoneyInput id="saude" value={s.saude} onChange={(v) => set("saude", v)} />
                </Field>
                <Field label="Educação" htmlFor="educ" help="Propinas, creche, manuais, explicações. Deduz 30%, até 800 €.">
                  <MoneyInput id="educ" value={s.educacao} onChange={(v) => set("educacao", v)} />
                </Field>
                <Field label="Lares" htmlFor="lares" help="Despesas com lares e apoio domiciliário para si, dependentes ou ascendentes. Deduz 25%, até 403,75 €.">
                  <MoneyInput id="lares" value={s.lares} onChange={(v) => set("lares", v)} />
                </Field>
                <Field label="Trabalho doméstico" htmlFor="domestico" help="Salário pago a empregada doméstica declarada à Segurança Social. Deduz 5%, até 200 €. Na declaração: Anexo H, código 666.">
                  <MoneyInput id="domestico" value={s.trabalhoDomestico} onChange={(v) => set("trabalhoDomestico", v)} />
                </Field>
                <Field label="Dedução de IVA por exigência de fatura" htmlFor="iva" help="Valor da dedução já calculado no e-fatura (restaurantes, cabeleireiro, oficinas, veterinário, passes...). Escreva a dedução, não o total gasto. Até 250 €.">
                  <MoneyInput id="iva" value={s.ivaFatura} onChange={(v) => set("ivaFatura", v)} />
                </Field>
              </div>
              </>
              )}
              <div className={cn("grid gap-5 border-t border-border pt-5", s.casado && "sm:grid-cols-2")}>
                <Field label="Rendas da casa" htmlFor="rendas" help="Total de rendas pagas em 2026 pela casa onde vive, com contrato registado nas Finanças. Deduz 15%, até 900 € (até 1 050 € para rendimentos baixos). Os recibos de renda eletrónicos não aparecem no e-fatura, por isso indique-as aqui. Na declaração: Anexo H, código 654.">
                  <MoneyInput id="rendas" value={s.rendas} onChange={(v) => set("rendas", v)} />
                </Field>
                <Field label="Juros do crédito à habitação" htmlFor="juros" help="Só para crédito à habitação própria permanente contratado até 31 de dezembro de 2011. Deduz 15%, até 296 € (até 450 € para rendimentos baixos). Os juros também não aparecem no e-fatura. Se indicar rendas e juros, conta só a dedução maior. Na declaração: Anexo H, código 655.">
                  <MoneyInput id="juros" value={s.jurosHab} onChange={(v) => set("jurosHab", v)} />
                </Field>
                {(s.casado ? ([0, 1] as const) : ([0] as const)).map((i) => (
                  <Field key={i} label={s.casado ? `PPR — titular ${i + 1}` : "PPR — Plano Poupança Reforma"} htmlFor={`ppr-${i}`} help="Valor que aplicou em PPR em 2026. Deduz 20%, até 400 € (menos de 35 anos), 350 € (35 a 50) ou 300 € (mais de 50). Conta para o limite global das deduções. Na declaração: Anexo H, quadro 6B, código 601.">
                    <MoneyInput id={`ppr-${i}`} value={s.titulares[i].ppr} onChange={(v) => setTit(i, { ppr: v })} />
                  </Field>
                ))}
                <Field label="Pensão de alimentos que paga" htmlFor="alimentos" help="Só se paga pensão de alimentos por decisão do tribunal ou acordo homologado (por exemplo, a filhos que não vivem consigo). Indique o total pago em 2026. Deduz 20%. Se não paga, deixe a 0 €. Na declaração: Anexo H, quadro 6A.">
                  <MoneyInput id="alimentos" value={s.pensaoAlimentos} onChange={(v) => set("pensaoAlimentos", v)} />
                </Field>
              </div>
            </SectionCard>
          )}

          {passo === 3 && (
            <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
              <SectionCard title="4. Resultado" className="shadow-lift">
                {resultado.tipo === "casal" ? (
                  <Comparacao conjunta={resultado.conjunta} separada={resultado.separada} recomendado={resultado.recomendado} diferenca={resultado.diferenca} semRetencoes={semRetencoes} />
                ) : (
                  <div className="space-y-5">
                    <ResultadoHero r={resultado.r} semRetencoes={semRetencoes} />
                    <TabelaDetalhe r={resultado.r} />
                    <Steps passos={resultado.r.passos} />
                  </div>
                )}
              </SectionCard>
              <div className="space-y-4">
                <Avisos avisos={avisos} />
              </div>
            </div>
          )}

          <div className="flex gap-3 print:hidden">
            {passo > 0 && (
              <button type="button" onClick={() => irPara(passo - 1)} className="inline-flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl border border-input bg-card px-5 text-base font-semibold hover:bg-muted sm:flex-none">
                <ArrowLeft className="size-5" aria-hidden /> Anterior
              </button>
            )}
            {passo < PASSOS.length - 1 && (
              <button type="button" onClick={() => irPara(passo + 1)} className="inline-flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-6 text-base font-semibold text-primary-foreground shadow-soft hover:bg-primary/90 sm:flex-none">
                {passo === PASSOS.length - 2 ? "Ver resultado" : "Seguinte"} <ArrowRight className="size-5" aria-hidden />
              </button>
            )}
          </div>
        </div>

        {passo < 3 && (
          <aside aria-label="Estimativa atual" className="space-y-3 lg:sticky lg:top-24 print:hidden">
            <div className="card-surface space-y-3 p-5 shadow-lift">
              <p className="text-sm font-semibold text-muted-foreground">
                Estimativa até agora{resultado.tipo === "casal" ? ` · ${resultado.recomendado === "conjunta" ? "conjunta" : "separada"}` : ""}
              </p>
              <ResultadoHero r={resultado.melhor} compact semRetencoes={semRetencoes} />
              <p className="text-[13px] text-muted-foreground">Atualiza à medida que preenche. Veja o detalhe no passo 4.</p>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

function TitularForm({
  idx,
  t,
  casado,
  onChange,
  situacao,
  dependentes,
}: {
  idx: 0 | 1;
  t: TitularState;
  casado: boolean;
  onChange: (p: Partial<TitularState>) => void;
  situacao: "nao_casado" | "casado_dois" | "casado_unico";
  dependentes: number;
}) {
  const [aberto, setAberto] = useState(false);
  const p = `t${idx}`;
  const ssAuto = t.ss === null;
  const ssValor = ssAuto ? Math.round(t.rb * SS_TRABALHADOR * 100) / 100 : (t.ss ?? 0);

  const estimar = () => {
    const e = estimarAnualDoMensal(t.mensal, { situacao, dependentes, irsJovemAno: t.irsJovemAno, novembro50: t.novembro50, natalEmNovembro: t.natalNovembro });
    onChange({ rb: e.brutoAnual, retencoes: e.retencoes, ss: null });
    setAberto(false);
  };

  return (
    <SectionCard title={casado ? `2. Rendimentos — titular ${idx + 1}` : "2. Rendimentos"} description="Salários de 2026, como aparecem na declaração anual da entidade patronal.">
      <DeclaracaoImport idPrefix={p} onAplicar={(v) => onChange({ rb: v.rb, retencoes: v.retencoes, ss: v.ss, sindicais: v.sindicais })} />

      <div className="rounded-2xl bg-primary-soft p-4">
        <button type="button" onClick={() => setAberto((v) => !v)} aria-expanded={aberto} className="flex min-h-11 w-full items-center gap-2 text-left text-[15px] font-semibold text-primary">
          <Calculator className="size-5" aria-hidden /> Estimar a partir do salário mensal
        </button>
        {aberto && (
          <div className="mt-3 space-y-4">
            {t.incapacidade > 0 && <Alert className="rounded-2xl border-pagar/50 bg-pagar-soft">
              <AlertTriangle className="size-4" aria-hidden />
              <AlertDescription>A estimativa usa as tabelas de retenção gerais. Com incapacidade a retenção real é mais baixa — use antes os valores da declaração da empresa.</AlertDescription>
            </Alert>}
            <Field label="Salário bruto mensal" htmlFor={`${p}-mensal`} help="Usamos 14 salários (12 meses + férias + Natal) e as tabelas de retenção de 2026 para estimar o rendimento anual e o IRS retido.">
              <MoneyInput id={`${p}-mensal`} value={t.mensal} onChange={(v) => onChange({ mensal: v })} />
            </Field>
            <CheckRow checked={t.novembro50} onChange={(v) => onChange({ novembro50: v })} helpLabel="Retenção de novembro" help="Em novembro de 2026 a retenção foi reduzida para metade na maioria dos salários, por causa da descida das taxas de IRS.">
              Aplicar retenção a 50% em novembro
            </CheckRow>
            {t.novembro50 && (
              <CheckRow checked={t.natalNovembro} onChange={(v) => onChange({ natalNovembro: v })} helpLabel="Subsídio de Natal em novembro" help="Se a empresa pagou o subsídio de Natal em novembro, a retenção sobre ele também foi reduzida para metade.">
                O subsídio de Natal é pago em novembro
              </CheckRow>
            )}
            <button type="button" onClick={estimar} disabled={t.mensal <= 0} className="inline-flex min-h-11 items-center justify-center rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              Preencher rendimento e retenções
            </button>
          </div>
        )}
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Rendimento bruto anual" htmlFor={`${p}-rb`} help="Soma de todos os salários brutos do ano, incluindo subsídios de férias e Natal.">
          <MoneyInput id={`${p}-rb`} value={t.rb} onChange={(v) => onChange({ rb: v })} />
        </Field>
        <Field
          label="IRS retido no ano"
          htmlFor={`${p}-ret`}
          help="Total de IRS que a empresa descontou ao longo do ano. Está nos recibos de vencimento ou na declaração anual de rendimentos. Também pode consultá-lo no Portal das Finanças → 'Rendimentos e Retenções'."
          hint={faltaRetencoes(t) ? "Está no recibo de dezembro (IRS acumulado) ou no Portal das Finanças → 'Rendimentos e Retenções'" : undefined}
        >
          <MoneyInput id={`${p}-ret`} value={t.retencoes} onChange={(v) => onChange({ retencoes: v })} />
        </Field>
        <Field
          label="Segurança Social paga"
          htmlFor={`${p}-ss`}
          help="Descontos para a Segurança Social no ano. Preenchemos 11% do bruto automaticamente; altere se for diferente."
          hint={
            ssAuto ? (
              "Calculado automaticamente (11%)"
            ) : (
              <button type="button" onClick={() => onChange({ ss: null })} className="font-semibold text-primary underline-offset-2 hover:underline">
                Repor 11% automático
              </button>
            )
          }
        >
          <MoneyInput id={`${p}-ss`} value={ssValor} onChange={(v) => onChange({ ss: v })} />
        </Field>
        <Field label="Quotas sindicais pagas" htmlFor={`${p}-sindicais`} help="Se é sócio de um sindicato, indique o total de quotas pagas em 2026. Contam até 1% do salário bruto, a dobrar. Vêm na declaração da empresa (Anexo A, quadro 4A).">
          <MoneyInput id={`${p}-sindicais`} value={t.sindicais} onChange={(v) => onChange({ sindicais: v })} />
        </Field>
        <Field label="Idade" htmlFor={`${p}-idade`} help="Idade a 31 de dezembro de 2026. Conta para o limite da dedução do PPR.">
          <NumberInput id={`${p}-idade`} value={t.idade} min={16} max={110} onChange={(v) => onChange({ idade: v })} />
        </Field>
        <Field label="Incapacidade" htmlFor={`${p}-incapacidade`} help={`Com atestado multiúso de 60% ou mais, ${formatPct(RENDIMENTO_DEFICIENCIA.pctExcluido)} do salário fica fora do IRS (até ${formatEUR(RENDIMENTO_DEFICIENCIA.exclusaoMax)}) e há uma dedução de ${formatEUR(IAS * DED_DEFICIENCIA.titularIAS)}. Com 90% ou mais, a dedução dobra.`}>
          <SelectInput<0 | 60 | 90> id={`${p}-incapacidade`} value={t.incapacidade} onChange={(v) => onChange({ incapacidade: v })} options={[{ value: 0, label: "Não tem" }, { value: 60, label: "60% a 89%" }, { value: 90, label: "90% ou mais" }]} />
        </Field>
        <Field label="IRS Jovem" htmlFor={`${p}-jovem`} help="Até aos 35 anos, parte do rendimento fica isenta nos primeiros 10 anos de trabalho: 100% no 1.º ano, 75% do 2.º ao 4.º, 50% do 5.º ao 7.º e 25% do 8.º ao 10.º. Na declaração: Anexo A, quadro 4F.1." className="sm:col-span-2">
          <SelectInput
            id={`${p}-jovem`}
            value={t.irsJovemAno}
            onChange={(v) => onChange({ irsJovemAno: v })}
            options={[{ value: 0, label: "Não se aplica" }, ...Array.from({ length: IRS_JOVEM_ANOS_MAX }, (_, i) => ({ value: i + 1, label: `${i + 1}.º ano de benefício` }))]}
          />
        </Field>
      </div>
      {faltaRetencoes(t) && (
        <Alert role="alert" className="rounded-2xl border-pagar/50 bg-pagar-soft">
          <AlertTriangle className="size-4" aria-hidden />
          <AlertDescription className="font-semibold text-foreground">
            Falta indicar as retenções na fonte — sem elas o resultado mostra o imposto todo como 'a pagar'.
          </AlertDescription>
        </Alert>
      )}
      {casado && idx === 1 && t.rb === 0 && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <UserPlus className="size-4" aria-hidden /> Se o cônjuge não teve rendimentos, deixe a 0 €.
        </p>
      )}
    </SectionCard>
  );
}
