import { Link } from "@tanstack/react-router";
import { Moon, Receipt, Settings2, Sun, Trash2, Wallet, BookOpen } from "lucide-react";
import type { ReactNode } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useSettings } from "@/lib/settings";
import { STORAGE_PREFIX } from "@/hooks/use-persistent-state";

function Logo() {
  return (
    <span aria-hidden className="hidden size-9 items-center sm:inline-flex justify-center rounded-xl bg-primary text-lg font-bold text-primary-foreground">
      €
    </span>
  );
}

function SettingsMenu() {
  return (
    <Popover>
      <PopoverTrigger
        aria-label="Definições"
        className="inline-flex size-11 items-center justify-center rounded-xl text-foreground transition-colors hover:bg-accent"
      >
        <Settings2 className="size-5" aria-hidden />
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 space-y-4 rounded-2xl p-5">
        <button
          type="button"
          onClick={() => {
            try {
              Object.keys(window.localStorage)
                .filter((k) => k.startsWith(STORAGE_PREFIX))
                .forEach((k) => window.localStorage.removeItem(k));
            } catch {
              /* ignore */
            }
            window.location.reload();
          }}
          className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-input text-sm font-semibold transition-colors hover:bg-muted"
        >
          <Trash2 className="size-4" aria-hidden /> Limpar todos os dados guardados
        </button>
      </PopoverContent>
    </Popover>
  );
}

function ThemeToggle() {
  const { tema, setTema } = useSettings();
  const escuro = tema === "escuro";
  return (
    <button
      type="button"
      onClick={() => setTema(escuro ? "claro" : "escuro")}
      aria-label={escuro ? "Mudar para tema claro" : "Mudar para tema escuro"}
      aria-pressed={escuro}
      className="inline-flex size-11 items-center justify-center rounded-xl text-foreground transition-colors hover:bg-accent"
    >
      {escuro ? <Sun className="size-5" aria-hidden /> : <Moon className="size-5" aria-hidden />}
    </button>
  );
}

const navLink =
  "inline-flex min-h-11 items-center whitespace-nowrap rounded-xl px-2 sm:px-3 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground";

export function AppShell({ children }: { children: ReactNode }) {
  // "Saltar para o conteúdo" usa foco direto em vez de #conteudo, porque o hash é usado pelas rotas.
  const saltar = (e: React.MouseEvent) => {
    e.preventDefault();
    const el = document.getElementById("conteudo");
    el?.focus();
    el?.scrollIntoView();
  };
  return (
    <div className="flex min-h-screen flex-col paper-grain">
      <a href="#conteudo" onClick={saltar} className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-xl focus:bg-card focus:px-4 focus:py-3">
        Saltar para o conteúdo
      </a>
      <header className="sticky top-0 z-40 border-b border-border/70 bg-background/85 backdrop-blur print:static print:border-0">
        <div className="mx-auto grid h-16 max-w-5xl grid-cols-[minmax(0,1fr)_auto] items-center gap-1 px-3 sm:flex sm:gap-2 sm:px-4">
          <Link to="/" className="mr-auto flex min-h-11 min-w-0 items-center gap-2.5 rounded-xl">
            <Logo />
            <span className="whitespace-nowrap text-base font-semibold leading-none sm:text-lg">
              Contas Certas <span className="text-primary">2026</span>
            </span>
          </Link>
          <nav aria-label="Principal" className="hidden items-center sm:flex print:hidden">
            <Link to="/salario" className={navLink} activeProps={{ className: "bg-primary-soft font-bold text-primary underline underline-offset-4", "aria-current": "page" }}>
              Salário
            </Link>
            <Link to="/irs" className={navLink} activeProps={{ className: "bg-primary-soft font-bold text-primary underline underline-offset-4", "aria-current": "page" }}>
              IRS
            </Link>
            <Link to="/regras" className={navLink} activeProps={{ className: "bg-primary-soft font-bold text-primary underline underline-offset-4", "aria-current": "page" }}>
              Regras 2026
            </Link>
          </nav>
          <div className="flex shrink-0 items-center print:hidden">
            <SettingsMenu />
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main id="conteudo" tabIndex={-1} className="mx-auto w-full max-w-5xl flex-1 px-4 pb-24 pt-6 outline-none sm:pb-16 sm:pt-10">
        {children}
      </main>
      <footer className="border-t border-border/70 pb-[calc(6rem+env(safe-area-inset-bottom))] pt-6 text-center text-[13px] text-muted-foreground sm:py-6">
        <p className="mx-auto max-w-5xl px-4">
          Created by Redfox using Claude · Simulação indicativa — não substitui o Portal das Finanças
        </p>
      </footer>
      <nav aria-label="Principal no telemóvel" className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card pb-[env(safe-area-inset-bottom)] sm:hidden print:hidden">
        <div className="grid h-14 grid-cols-3">
          {([
            { to: "/salario", label: "Salário", icon: Wallet },
            { to: "/irs", label: "IRS", icon: Receipt },
            { to: "/regras", label: "Regras 2026", icon: BookOpen },
          ] as const).map(({ to, label, icon: Icon }) => (
            <Link key={to} to={to} className="flex min-h-11 min-w-0 flex-col items-center justify-center gap-0.5 text-[13px] font-medium text-muted-foreground" activeProps={{ className: "bg-primary-soft font-bold text-primary underline underline-offset-4", "aria-current": "page" }}>
              <Icon className="size-5 shrink-0" aria-hidden />
              <span>{label}</span>
            </Link>
          ))}
        </div>
      </nav>
    </div>
  );
}
