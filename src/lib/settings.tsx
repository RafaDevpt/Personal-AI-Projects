import { createContext, useContext, useEffect, type ReactNode } from "react";
import { usePersistentState } from "@/hooks/use-persistent-state";

type Tema = "claro" | "escuro";

interface Settings {
  tema: Tema;
}

interface SettingsCtx extends Settings {
  setTema: (t: Tema) => void;
  resetSettings: () => void;
}

const Ctx = createContext<SettingsCtx | null>(null);

export const THEME_STORAGE_KEY = "contas-certas-2026:definicoes";

function migrarDefinicoes(raw: unknown, inicial: Settings): Settings {
  const tema = raw && typeof raw === "object" && "tema" in raw ? raw.tema : undefined;
  return { tema: tema === "escuro" ? "escuro" : inicial.tema };
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [s, setS, reset] = usePersistentState<Settings>("definicoes", { tema: "claro" }, { migrate: migrarDefinicoes });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", s.tema === "escuro");
  }, [s.tema]);

  return (
    <Ctx.Provider
      value={{
        ...s,
        setTema: (tema) => setS((p) => ({ ...p, tema })),
        resetSettings: reset,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useSettings() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useSettings fora do SettingsProvider");
  return c;
}
