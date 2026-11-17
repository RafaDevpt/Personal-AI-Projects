import { useState } from "react";
import {
  AlertTriangle,
  Armchair,
  BrushCleaning,
  Bike,
  BookOpen,
  Bus,
  Car,
  ChevronDown,
  CircleCheck,
  Dumbbell,
  GraduationCap,
  HeartPulse,
  House,
  Landmark,
  Newspaper,
  Palette,
  PawPrint,
  Scissors,
  ShoppingCart,
  UtensilsCrossed,
  type LucideIcon,
} from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Field, MoneyInput } from "@/components/form/fields";
import { formatEUR } from "@/lib/format";
import { ivaTotalBloco, totalBloco, type EfaturaBloco } from "@/lib/fiscal/irs";
import { round2 } from "@/lib/fiscal/money";
import { SETORES_IVA, type SetorIVA } from "@/lib/fiscal/rules2026";
import { cn } from "@/lib/utils";
import { EfaturaImport } from "./EfaturaImport";

type CampoDeducao = "gerais" | "saude" | "educacao" | "habitacao" | "lares" | "domestico";

const DEDUCOES: { key: CampoDeducao; label: string; icon: LucideIcon }[] = [
  { key: "gerais", label: "Despesas Gerais Familiares", icon: ShoppingCart },
  { key: "saude", label: "Saúde", icon: HeartPulse },
  { key: "educacao", label: "Educação", icon: GraduationCap },
  { key: "habitacao", label: "Habitação", icon: House },
  { key: "lares", label: "Lares", icon: Armchair },
  { key: "domestico", label: "Trabalho Doméstico", icon: BrushCleaning },
];

const ICONES_IVA: Record<SetorIVA, LucideIcon> = {
  reparacao_automoveis: Car,
  reparacao_motociclos: Bike,
  restauracao_alojamento: UtensilsCrossed,
  cabeleireiros: Scissors,
  veterinarios: PawPrint,
  transportes_publicos: Bus,
  ginasios: Dumbbell,
  jornais_revistas: Newspaper,
  livros: BookOpen,
  atividades_artisticas: Palette,
  museus_monumentos: Landmark,
};

export interface BlocoUI {
  id: string;
  titulo: string;
  bloco: EfaturaBloco;
  portal: number;
  onChange: (b: EfaturaBloco) => void;
  onPortal: (v: number) => void;
}

function Tile({ id, label, icon: Icon, value, onChange }: { id: string; label: string; icon: LucideIcon; value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex min-w-0 flex-col justify-between gap-2 rounded-2xl bg-muted/50 p-3">
      <label htmlFor={id} className="flex items-start gap-2 text-[13px] font-semibold leading-tight">
        <Icon className="mt-px size-4 shrink-0 text-primary" aria-hidden />
        <span>{label}</span>
      </label>
      <MoneyInput id={id} value={value} onChange={onChange} />
    </div>
  );
}

function BlocoEfatura({ b }: { b: BlocoUI }) {
  const [ivaAberto, setIvaAberto] = useState(false);
  const { bloco, onChange } = b;
  const ivaSub = ivaTotalBloco(bloco);
  const total = totalBloco(bloco);
  const diff = round2(total - b.portal);
  const setIva = (k: SetorIVA, v: number) => onChange({ ...bloco, iva: { ...bloco.iva, [k]: v } });

  return (
    <div className="space-y-4">
      <EfaturaImport idPrefix={b.id} bloco={bloco} onAplicar={(novo, totalLido) => {
        b.onChange(novo);
        if (totalLido !== null) b.onPortal(totalLido);
      }} />
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {DEDUCOES.map((d) => (
          <Tile key={d.key} id={`${b.id}-${d.key}`} label={d.label} icon={d.icon} value={bloco[d.key] ?? 0} onChange={(v) => onChange({ ...bloco, [d.key]: v })} />
        ))}
      </div>

      <Collapsible open={ivaAberto} onOpenChange={setIvaAberto} className="rounded-2xl bg-muted/60 p-2">
        <CollapsibleTrigger className="flex min-h-11 w-full items-center justify-between gap-3 rounded-xl px-2 text-left text-[15px] font-semibold">
          <span>IVA por exigência de fatura (11 setores)</span>
          <span className="flex shrink-0 items-center gap-2">
            <span className="num text-sm text-muted-foreground">{formatEUR(ivaSub)}</span>
            <ChevronDown className={cn("size-5 transition-transform", ivaAberto && "rotate-180")} aria-hidden />
          </span>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="grid grid-cols-2 gap-2 pt-2 sm:grid-cols-3">
            {SETORES_IVA.map((s) => (
              <Tile key={s.key} id={`${b.id}-iva-${s.key}`} label={s.label} icon={ICONES_IVA[s.key]} value={bloco.iva?.[s.key] ?? 0} onChange={(v) => setIva(s.key, v)} />
            ))}
          </div>
        </CollapsibleContent>
      </Collapsible>

      <div className="space-y-3 border-t border-border pt-4">
        <p className="flex items-baseline justify-between gap-3 text-[15px] font-semibold">
          <span>Total deste e-fatura</span>
          <span className="num text-xl font-bold">{formatEUR(total)}</span>
        </p>
        <Field
          label="Valor de 'Deduções Provisórias em IRS' no Portal"
          htmlFor={`${b.id}-portal`}
          hint="Opcional — serve só para confirmar que copiou tudo."
        >
          <MoneyInput id={`${b.id}-portal`} value={b.portal} onChange={b.onPortal} />
        </Field>
        {b.portal > 0 &&
          (Math.abs(diff) <= 0.01 ? (
            <p role="status" className="flex items-center gap-2 rounded-xl bg-receber-soft px-3 py-2 text-sm font-semibold text-receber">
              <CircleCheck className="size-5 shrink-0" aria-hidden /> Bate certo
            </p>
          ) : (
            <p role="status" className="flex items-center gap-2 rounded-xl bg-pagar-soft px-3 py-2 text-sm font-semibold text-pagar-ink">
              <AlertTriangle className="size-5 shrink-0" aria-hidden /> Diferença de {formatEUR(Math.abs(diff))} — confirme os valores
            </p>
          ))}
      </div>
    </div>
  );
}

export function EfaturaForm({ blocos }: { blocos: BlocoUI[] }) {
  const [ativo, setAtivo] = useState(blocos[0]?.id ?? "");
  const atual = blocos.some((b) => b.id === ativo) ? ativo : (blocos[0]?.id ?? "");
  if (blocos.length === 1) return <BlocoEfatura b={blocos[0]!} />;
  return (
    <Tabs value={atual} onValueChange={setAtivo}>
      <TabsList className="grid h-auto w-full gap-1 rounded-2xl p-1" style={{ gridTemplateColumns: `repeat(${blocos.length}, minmax(0, 1fr))` }}>
        {blocos.map((b) => (
          <TabsTrigger key={b.id} value={b.id} className="min-h-11 whitespace-normal rounded-xl px-2 text-sm font-semibold leading-tight">
            <span>
              {b.titulo}
              <span className="num block text-[13px] font-medium text-muted-foreground">{formatEUR(totalBloco(b.bloco))}</span>
            </span>
          </TabsTrigger>
        ))}
      </TabsList>
      {blocos.map((b) => (
        <TabsContent key={b.id} value={b.id} className="mt-4">
          <BlocoEfatura b={b} />
        </TabsContent>
      ))}
    </Tabs>
  );
}
