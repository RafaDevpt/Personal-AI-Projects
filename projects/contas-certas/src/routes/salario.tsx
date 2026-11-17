import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Printer, RotateCcw } from "lucide-react";
import { CheckRow, Field, MoneyInput, Segmented, SelectInput, Stepper } from "@/components/form/fields";
import { SectionCard, StackedBar, Stat, Steps } from "@/components/results/parts";
import { usePersistentState } from "@/hooks/use-persistent-state";
import { calcBrutoParaLiquido, calcSalario, type Duodecimos, type RefeicaoTipo, type SalarioInput } from "@/lib/fiscal/salario";
import type { Situacao } from "@/lib/fiscal/retencao";
import { DIAS_UTEIS_PADRAO, IRS_JOVEM_ANOS_MAX, REFEICAO_ISENTO, SS_EMPREGADOR } from "@/lib/fiscal/rules2026";
import { formatEUR, formatPct } from "@/lib/format";

export const Route = createFileRoute("/salario")({
  component: SalarioPage,
});

interface SalarioState {
  modo: "bruto" | "liquido";
  bruto: number;
  alvo: number;
  outros: number;
  situacao: Situacao;
  dependentes: number;
  depDeficiencia: number;
  refeicaoDia: number;
  refeicaoTipo: RefeicaoTipo;
  dias: number;
  duodecimos: Duodecimos;
  irsJovemAno: number;
  novembro: boolean;
}

const INICIAL: SalarioState = {
  modo: "bruto",
  bruto: 1500,
  alvo: 1200,
  outros: 0,
  situacao: "nao_casado",
  dependentes: 0,
  depDeficiencia: 0,
  refeicaoDia: 0,
  refeicaoTipo: "cartao",
  dias: DIAS_UTEIS_PADRAO,
  duodecimos: 0,
  irsJovemAno: 0,
  novembro: false,
};

const eur = (n: number) => formatEUR(n).replace(/ €$/, " €");

function SalarioPage() {
  const [s, setS, reset] = usePersistentState<SalarioState>("salario", INICIAL);
  const set = <K extends keyof SalarioState>(k: K, v: SalarioState[K]) => setS((p) => ({ ...p, [k]: v }));

  const { r, bruto } = useMemo(() => {
    const resto: Omit<SalarioInput, "bruto"> = {
      outrosSujeitos: s.outros,
      situacao: s.situacao,
      dependentes: s.dependentes,
      depDeficiencia: s.depDeficiencia,
      refeicaoDia: s.refeicaoDia,
      refeicaoTipo: s.refeicaoTipo,
      dias: s.dias,
      duodecimos: s.duodecimos,
      irsJovemAno: s.irsJovemAno,
      novembro: s.novembro,
    };
    if (s.modo === "liquido") {
      const inv = calcBrutoParaLiquido(s.alvo, resto);
      return { r: inv.resultado, bruto: inv.bruto };
    }
    return { r: calcSalario({ ...resto, bruto: s.bruto }), bruto: s.bruto };
  }, [s]);

  const irsTotal = r.ret + r.retDuo;
  const [resultadoVisivel, setResultadoVisivel] = useState(false);
  useEffect(() => {
    const el = document.getElementById("resultado");
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(([e]) => setResultadoVisivel(!!e?.isIntersecting), { threshold: 0.15 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  const isentoRef = REFEICAO_ISENTO[s.refeicaoTipo];

  return (
    <div className="space-y-6">
      <header className="grid min-w-0 gap-3 sm:flex sm:items-end sm:justify-between">
        <div className="space-y-1">
          <h1 className="font-display text-3xl font-semibold tracking-normal sm:text-4xl">Salário líquido</h1>
          <p className="text-muted-foreground">Trabalho por conta de outrem · Continente · 2026</p>
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

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        {/* Entradas */}
        <div className="space-y-5 print:hidden">
          <SectionCard>
            <Segmented
              label="Modo de cálculo"
              value={s.modo}
              onChange={(v) => set("modo", v)}
              options={[
                { value: "bruto", label: "Sei o bruto", sub: "quanto recebo?" },
                { value: "liquido", label: "Quero receber", sub: "quanto devo pedir?" },
              ]}
            />
            {s.modo === "bruto" ? (
              <Field label="Salário base bruto mensal" htmlFor="bruto" help="O valor que aparece no contrato, antes de descontos. Inclua diuturnidades, isenção de horário e outros complementos fixos.">
                <MoneyInput id="bruto" value={s.bruto} onChange={(v) => set("bruto", v)} large />
              </Field>
            ) : (
              <Field label="Quero receber por mês (líquido)" htmlFor="alvo" help="Indique quanto quer receber na conta ao fim do mês. Calculamos o salário bruto de que precisa.">
                <MoneyInput id="alvo" value={s.alvo} onChange={(v) => set("alvo", v)} large />
              </Field>
            )}
          </SectionCard>

          <SectionCard title="Agregado familiar">
            <Field as="fieldset" label="Situação" help="Define a tabela de retenção. «Casado, 1 titular» é quando só um dos cônjuges tem rendimentos. Unidos de facto contam como casados se assim declararem.">
              <Segmented
                label="Situação"
                value={s.situacao}
                onChange={(v) => set("situacao", v)}
                options={[
                  { value: "nao_casado", label: "Não casado" },
                  { value: "casado_dois", label: "Casado", sub: "2 titulares" },
                  { value: "casado_unico", label: "Casado", sub: "1 titular" },
                ]}
              />
            </Field>
            <div className="grid gap-5 sm:grid-cols-2">
              <Field as="fieldset" label="Dependentes" help="Filhos ou outros dependentes a seu cargo. Cada um reduz o IRS retido todos os meses.">
                <Stepper label="dependentes" value={s.dependentes} onChange={(v) => setS((p) => ({ ...p, dependentes: v, depDeficiencia: Math.min(p.depDeficiencia, v) }))} />
              </Field>
              {s.dependentes > 0 && (
                <Field as="fieldset" label="Com deficiência ≥ 60%" help="Quantos dos dependentes têm incapacidade igual ou superior a 60%. Dá uma redução adicional na retenção.">
                  <Stepper label="dependentes com deficiência" value={s.depDeficiencia} max={s.dependentes} onChange={(v) => set("depDeficiencia", v)} />
                </Field>
              )}
            </div>
          </SectionCard>

          <SectionCard title="Outros valores">
            <Field label="Outros abonos sujeitos a imposto" htmlFor="outros" help="Prémios, horas extra ou outros valores mensais que pagam IRS e Segurança Social. Se não tem, deixe vazio.">
              <MoneyInput id="outros" value={s.outros} onChange={(v) => set("outros", v)} />
            </Field>
            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Subsídio de refeição por dia" htmlFor="refeicao" help={`Valor diário. Até ${eur(REFEICAO_ISENTO.cartao)} em cartão ou ${eur(REFEICAO_ISENTO.dinheiro)} em dinheiro não paga impostos.`}>
                <MoneyInput id="refeicao" value={s.refeicaoDia} onChange={(v) => set("refeicaoDia", v)} />
              </Field>
              <Field as="fieldset" label="Dias por mês" help="Dias de trabalho com subsídio de refeição. Em média são 22.">
                <Stepper label="dias com subsídio de refeição" value={s.dias} max={31} onChange={(v) => set("dias", v)} />
              </Field>
            </div>
            <Field as="fieldset" label="Forma de pagamento da refeição" help="Em cartão o limite isento é mais alto do que em dinheiro.">
              <Segmented
                label="Forma de pagamento da refeição"
                value={s.refeicaoTipo}
                onChange={(v) => set("refeicaoTipo", v)}
                options={[
                  { value: "cartao", label: "Cartão", sub: `isento até ${eur(REFEICAO_ISENTO.cartao)}` },
                  { value: "dinheiro", label: "Dinheiro", sub: `isento até ${eur(REFEICAO_ISENTO.dinheiro)}` },
                ]}
              />
            </Field>
            <Field as="fieldset" label="Subsídios em duodécimos" help="Se a empresa paga parte dos subsídios de férias e de Natal todos os meses, em vez de os pagar por inteiro em junho e dezembro.">
              <Segmented
                label="Subsídios em duodécimos"
                value={s.duodecimos}
                onChange={(v) => set("duodecimos", v)}
                options={[
                  { value: 0, label: "Não" },
                  { value: 0.5, label: "50%" },
                  { value: 1, label: "100%" },
                ]}
              />
            </Field>
            <Field label="IRS Jovem" htmlFor="jovem" help="Para quem tem até 35 anos: parte do salário fica isenta de IRS nos primeiros 10 anos de trabalho. Escolha em que ano do benefício está.">
              <SelectInput
                id="jovem"
                value={s.irsJovemAno}
                onChange={(v) => set("irsJovemAno", v)}
                options={[{ value: 0, label: "Não se aplica" }, ...Array.from({ length: IRS_JOVEM_ANOS_MAX }, (_, i) => ({ value: i + 1, label: `${i + 1}.º ano de benefício` }))]}
              />
            </Field>
            <CheckRow
              checked={s.novembro}
              onChange={(v) => set("novembro", v)}
              helpLabel="Novembro de 2026"
              help="Em novembro de 2026 a retenção de IRS é reduzida para metade (para a maioria dos salários), por causa da descida das taxas."
            >
              Calcular para novembro de 2026 (retenção a 50%)
            </CheckRow>
            {s.novembro && (
              <p className="-mt-2 rounded-xl bg-muted px-3 py-2 text-sm text-muted-foreground">
                Em novembro o IRS retido é metade porque reflete a descida do IRS desde janeiro. O acerto final faz-se na declaração de 2027.
              </p>
            )}
          </SectionCard>
        </div>

        {/* Resumo fixo no telemóvel. Faz scroll por JS: o hash do URL é usado pelas rotas. */}
        <a
          href="#resultado"
          onClick={(e) => {
            e.preventDefault();
            document.getElementById("resultado")?.scrollIntoView({ behavior: "smooth" });
          }}
          aria-hidden={resultadoVisivel}
          tabIndex={resultadoVisivel ? -1 : 0}
          className={`fixed inset-x-3 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] sm:bottom-3 z-30 flex transition-all duration-300 ${resultadoVisivel ? "pointer-events-none translate-y-24 opacity-0" : ""} min-h-14 items-center justify-between rounded-2xl bg-primary px-5 text-primary-foreground lg:hidden print:hidden`}
        >
          <span className="text-sm font-semibold">Recebe por mês</span>
          <span className="num font-bold text-2xl">{formatEUR(r.liquido)}</span>
        </a>

        {/* Resultado */}
        <div id="resultado" className="scroll-mt-20 space-y-5 lg:sticky lg:top-24">
          <SectionCard className="shadow-lift">
            <div aria-live="polite" aria-atomic="true" className="space-y-1">
              <p className="text-sm font-semibold text-muted-foreground">Recebe por mês</p>
              <p className="num font-bold text-5xl leading-none tracking-normal text-primary sm:text-6xl">{formatEUR(r.liquido)}</p>
              {s.modo === "liquido" && (
                <p className="pt-2 text-base">
                  Precisa de um salário bruto de <strong className="num">{formatEUR(bruto)}</strong>
                </p>
              )}
              <p className="pt-1 text-sm text-muted-foreground">
                Tabela {r.tabela} de retenção{s.novembro ? " · novembro 2026" : ""}
              </p>
            </div>
            <p className="text-sm text-muted-foreground">Isto é uma simulação: o recibo pode ter pequenas diferenças. O IRS retido é arredondado ao euro, como nos recibos.</p>

            <StackedBar
              label="Distribuição do salário"
              segments={[
                { label: "Líquido", value: r.liquido, className: "bg-bar-liquido" },
                { label: "Segurança Social", value: r.ss, className: "bg-bar-ss" },
                { label: "IRS retido", value: irsTotal, className: "bg-bar-irs" },
              ]}
            />

            <div className="grid grid-cols-2 gap-3">
              <Stat label="Segurança Social" value={`− ${formatEUR(r.ss)}`} />
              <Stat label="IRS retido" value={`− ${formatEUR(irsTotal)}`} />
              <Stat label="Taxa efetiva de IRS" value={formatPct(r.taxaEfetivaIRS)} hint="IRS retido ao longo do ano ÷ rendimento sujeito" />
              <Stat label="Total anual líquido" value={formatEUR(r.liquidoAnual)} hint="12 meses + subsídios" />
              <Stat label="Custo para a empresa" value={formatEUR(r.custoEmpresaMensal)} hint={`por mês · bruto + ${formatPct(SS_EMPREGADOR, 2)} TSU`} />
              <Stat label="Custo anual para a empresa" value={formatEUR(r.custoEmpresaAnual)} hint="14 salários + TSU + refeição" />
            </div>

            <Steps passos={r.passos} />
            {r.refeicaoExcesso > 0 && (
              <p className="text-[13px] text-muted-foreground">
                O subsídio de refeição acima de {formatEUR(isentoRef)}/dia ({formatEUR(r.refeicaoExcesso)}) paga IRS e Segurança Social.
              </p>
            )}
          </SectionCard>

          {s.duodecimos < 1 &&
            (s.novembro ? (
              <SectionCard>
                <div className="space-y-1">
                  <h2 className="text-[15px] font-semibold">
                    Subsídio de Natal — pago em novembro{s.duodecimos === 0.5 ? " (metade restante)" : ""}
                  </h2>
                  <p className="num font-bold text-3xl text-primary">{formatEUR(r.natalNovembro.liquido)}</p>
                  <p className="text-sm text-muted-foreground">
                    Bruto {formatEUR(r.natalNovembro.bruto)} · SS − {formatEUR(r.natalNovembro.ss)} · IRS − {formatEUR(r.natalNovembro.irs)}
                  </p>
                  <p className="text-sm text-muted-foreground">Se a empresa pagar em dezembro: {formatEUR(r.subsidioNormal.liquido)}</p>
                </div>
                <div className="flex items-baseline justify-between gap-3 border-t border-border pt-3 text-sm">
                  <span className="text-muted-foreground">Subsídio de férias{s.duodecimos === 0.5 ? " (metade restante)" : ""}</span>
                  <span className="num font-semibold">{formatEUR(r.subsidioNormal.liquido)}</span>
                </div>
              </SectionCard>
            ) : (
              <SectionCard>
                <div className="space-y-1">
                  <h2 className="text-[15px] font-semibold">
                    Subsídio de férias / Natal (pago por inteiro{s.duodecimos === 0.5 ? " — metade restante" : ""})
                  </h2>
                  <p className="num font-bold text-3xl text-primary">{formatEUR(r.subsidioNormal.liquido)}</p>
                  <p className="text-sm text-muted-foreground">
                    Bruto {formatEUR(r.subsidioNormal.bruto)} · SS − {formatEUR(r.subsidioNormal.ss)} · IRS − {formatEUR(r.subsidioNormal.irs)} · cada subsídio
                  </p>
                </div>
              </SectionCard>
            ))}
        </div>
      </div>
    </div>
  );
}
