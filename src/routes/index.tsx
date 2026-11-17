import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Lock, Receipt, Wallet } from "lucide-react";

export const Route = createFileRoute("/")({
  component: Index,
});

function ToolCard({ to, icon, title, text, cta }: { to: "/salario" | "/irs"; icon: React.ReactNode; title: string; text: string; cta: string }) {
  return (
    <Link
      to={to}
      className="group card-surface flex flex-col gap-5 p-6 transition-all hover:-translate-y-0.5 hover:shadow-lift focus-visible:shadow-lift sm:p-8"
    >
      <span className="inline-flex size-14 items-center justify-center rounded-2xl bg-primary-soft text-primary">{icon}</span>
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold leading-tight tracking-normal sm:text-3xl">{title}</h2>
        <p className="text-base leading-relaxed text-muted-foreground">{text}</p>
      </div>
      <span className="mt-auto inline-flex items-center gap-2 text-base font-semibold text-primary">
        {cta}
        <ArrowRight className="size-5 transition-transform group-hover:translate-x-1" aria-hidden />
      </span>
    </Link>
  );
}

function Index() {
  return (
    <div className="space-y-10">
      <section className="max-w-2xl space-y-4">
        <p className="text-sm font-semibold uppercase tracking-[0.14em] text-primary">Portugal · 2026</p>
        <h1 className="font-display text-4xl font-semibold leading-[1.05] tracking-normal sm:text-5xl">
          As suas contas de salário e IRS, sem complicações.
        </h1>
        <p className="text-lg leading-relaxed text-muted-foreground">
          Escolha uma ferramenta. Os resultados aparecem à medida que escreve.
        </p>
      </section>

      <div className="grid gap-5 md:grid-cols-2">
        <ToolCard
          to="/salario"
          icon={<Wallet className="size-7" aria-hidden />}
          title="Salário líquido"
          text="Quanto recebe ao fim do mês, depois da Segurança Social e do IRS retido."
          cta="Calcular salário"
        />
        <ToolCard
          to="/irs"
          icon={<Receipt className="size-7" aria-hidden />}
          title="IRS 2026 — vou receber ou pagar?"
          text="Em 4 passos simples, veja se terá reembolso ou imposto a pagar na declaração."
          cta="Começar assistente"
        />
      </div>

      <p className="flex items-start gap-3 rounded-2xl bg-muted p-4 text-sm leading-relaxed text-muted-foreground">
        <Lock className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
        Os seus dados nunca saem deste ecrã: todos os cálculos são feitos no seu telemóvel ou computador, sem contas nem registos.
      </p>
    </div>
  );
}
