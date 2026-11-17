import { useEffect, useId, useState, type ReactNode } from "react";
import { HelpCircle, Minus, Plus } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { formatInputNumber, parseMoney } from "@/lib/format";

export function FieldHelp({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Popover>
      <PopoverTrigger
        type="button"
        aria-label={`O que é: ${label}`}
        className="inline-flex size-11 -my-3 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-primary print:hidden"
      >
        <HelpCircle className="size-[18px]" aria-hidden />
      </PopoverTrigger>
      <PopoverContent className="w-80 rounded-2xl text-sm leading-relaxed" side="top" align="start">
        <p className="font-semibold text-foreground">{label}</p>
        <div className="mt-1 text-muted-foreground">{children}</div>
      </PopoverContent>
    </Popover>
  );
}

interface FieldProps {
  label: string;
  help?: ReactNode;
  htmlFor?: string;
  hint?: ReactNode;
  children: ReactNode;
  className?: string;
  as?: "div" | "fieldset";
}

export function Field({ label, help, htmlFor, hint, children, className, as = "div" }: FieldProps) {
  const Comp = as;
  const LabelTag = as === "fieldset" ? "legend" : "label";
  return (
    <Comp className={cn("min-w-0 space-y-2", className)}>
      <div className="flex items-center gap-1">
        <LabelTag
          {...(as === "fieldset" ? {} : { htmlFor })}
          className="text-[15px] font-semibold leading-tight text-foreground"
        >
          {label}
        </LabelTag>
        {help && <FieldHelp label={label}>{help}</FieldHelp>}
      </div>
      {children}
      {hint && <p className="text-[13px] text-muted-foreground">{hint}</p>}
    </Comp>
  );
}

const inputBase =
  "h-12 w-full rounded-xl border border-input bg-card px-4 text-base text-foreground transition-colors placeholder:text-muted-foreground focus-visible:border-primary focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring";

interface MoneyInputProps {
  id?: string;
  value: number;
  onChange: (v: number) => void;
  placeholder?: string;
  suffix?: string;
  ariaLabel?: string;
  ariaDescribedBy?: string;
  large?: boolean;
}

export function MoneyInput({ id, value, onChange, placeholder = "0", suffix = "€", ariaLabel, ariaDescribedBy, large }: MoneyInputProps) {
  const [text, setText] = useState(() => formatInputNumber(value));
  useEffect(() => {
    if (Math.abs(parseMoney(text) - value) > 0.001) setText(formatInputNumber(value));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);
  return (
    <div className="relative">
      <input
        id={id}
        type="text"
        inputMode="decimal"
        autoComplete="off"
        aria-label={ariaLabel}
        aria-describedby={ariaDescribedBy}
        placeholder={placeholder}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          onChange(parseMoney(e.target.value));
        }}
        onBlur={() => setText(formatInputNumber(parseMoney(text)))}
        className={cn(inputBase, "num pr-10", large && "h-14 text-2xl font-semibold")}
      />
      <span aria-hidden className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-muted-foreground">
        {suffix}
      </span>
    </div>
  );
}

export function NumberInput({ id, value, onChange, min = 0, max = 120, ariaLabel }: { id?: string; value: number; onChange: (v: number) => void; min?: number; max?: number; ariaLabel?: string }) {
  // O texto fica livre enquanto se escreve; os limites só se aplicam ao sair do campo.
  const [text, setText] = useState(() => String(value));
  useEffect(() => {
    if (parseInt(text, 10) !== value) setText(String(value));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);
  return (
    <input
      id={id}
      type="text"
      inputMode="numeric"
      autoComplete="off"
      aria-label={ariaLabel}
      value={text}
      onChange={(e) => {
        const t = e.target.value.replace(/\D/g, "").slice(0, 3);
        setText(t);
        const n = parseInt(t, 10);
        if (Number.isFinite(n) && n >= min && n <= max) onChange(n);
      }}
      onBlur={() => {
        const n = parseInt(text, 10);
        const v = Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : value;
        setText(String(v));
        if (v !== value) onChange(v);
      }}
      className={cn(inputBase, "num")}
    />
  );
}

interface StepperProps {
  id?: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  label: string;
}

export function Stepper({ id, value, onChange, min = 0, max = 20, label }: StepperProps) {
  return (
    <div className="flex items-center gap-2" role="group" aria-label={label}>
      <button
        type="button"
        onClick={() => onChange(Math.max(min, value - 1))}
        disabled={value <= min}
        aria-label={`Diminuir ${label}`}
        className="inline-flex size-12 items-center justify-center rounded-xl border border-input bg-card text-foreground transition-colors hover:bg-accent disabled:opacity-40"
      >
        <Minus className="size-5" aria-hidden />
      </button>
      <output id={id} aria-live="polite" className="num min-w-12 text-center text-2xl font-semibold">
        {value}
      </output>
      <button
        type="button"
        onClick={() => onChange(Math.min(max, value + 1))}
        disabled={value >= max}
        aria-label={`Aumentar ${label}`}
        className="inline-flex size-12 items-center justify-center rounded-xl border border-input bg-card text-foreground transition-colors hover:bg-accent disabled:opacity-40"
      >
        <Plus className="size-5" aria-hidden />
      </button>
    </div>
  );
}

interface SegmentedProps<T extends string | number> {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string; sub?: string }[];
  label: string;
  columns?: number;
}

export function Segmented<T extends string | number>({ value, onChange, options, label, columns }: SegmentedProps<T>) {
  const name = useId();
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="grid gap-1 rounded-2xl bg-muted p-1"
      style={{ gridTemplateColumns: `repeat(${columns ?? options.length}, minmax(0, 1fr))` }}
    >
      {options.map((o) => {
        const checked = o.value === value;
        return (
          <label
            key={String(o.value)}
            className={cn(
              "relative flex min-h-11 cursor-pointer flex-col items-center justify-center rounded-xl px-2 py-2 text-center text-sm font-semibold leading-tight transition-all",
              "has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px] has-[:focus-visible]:outline-ring",
              checked ? "bg-card text-primary ring-1 ring-primary/30" : "text-muted-foreground hover:text-foreground",
            )}
          >
            <input
              type="radio"
              name={name}
              className="sr-only"
              checked={checked}
              onChange={() => onChange(o.value)}
            />
            <span>{o.label}</span>
            {o.sub && <span className="mt-0.5 text-[13px] font-medium">{o.sub}</span>}
          </label>
        );
      })}
    </div>
  );
}

export function CheckRow({ id, checked, onChange, children, help, helpLabel }: { id?: string; checked: boolean; onChange: (v: boolean) => void; children: ReactNode; help?: ReactNode; helpLabel?: string }) {
  const autoId = useId();
  const cid = id ?? autoId;
  return (
    <div className="flex items-center gap-1">
      <label htmlFor={cid} className="flex min-h-11 flex-1 cursor-pointer items-center gap-3 rounded-xl text-[15px] font-medium">
        <input
          id={cid}
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="size-5 shrink-0 rounded accent-primary"
        />
        <span>{children}</span>
      </label>
      {help && <FieldHelp label={helpLabel ?? "Ajuda"}>{help}</FieldHelp>}
    </div>
  );
}

export function SelectInput<T extends string | number>({ id, value, onChange, options, ariaLabel }: { id?: string; value: T; onChange: (v: T) => void; options: { value: T; label: string }[]; ariaLabel?: string }) {
  return (
    <select
      id={id}
      aria-label={ariaLabel}
      value={String(value)}
      onChange={(e) => {
        const o = options.find((x) => String(x.value) === e.target.value);
        if (o) onChange(o.value);
      }}
      className={cn(inputBase, "pr-4")}
    >
      {options.map((o) => (
        <option key={String(o.value)} value={String(o.value)}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
