import { useCallback, useEffect, useRef, useState } from "react";

export const STORAGE_PREFIX = "contas-certas-2026:";

/** Estado guardado no localStorage deste browser (nunca sai do dispositivo). */
export function usePersistentState<T extends object>(
  key: string,
  initial: T,
  options?: { migrate?: (raw: unknown, initial: T) => T },
) {
  const fullKey = STORAGE_PREFIX + key;
  const initialRef = useRef(initial);
  const migrateRef = useRef(options?.migrate);
  const [state, setState] = useState<T>(initial);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(fullKey);
      if (raw) {
        const parsed: unknown = JSON.parse(raw);
        const mig = migrateRef.current;
        setState(mig ? mig(parsed, initialRef.current) : { ...initialRef.current, ...(parsed as object) });
      }
    } catch {
      /* armazenamento indisponível */
    }
    setHydrated(true);
  }, [fullKey]);

  useEffect(() => {
    if (!hydrated) return;
    try {
      const json = JSON.stringify(state);
      if (json === JSON.stringify(initialRef.current)) window.localStorage.removeItem(fullKey);
      else window.localStorage.setItem(fullKey, json);
    } catch {
      /* armazenamento indisponível */
    }
  }, [fullKey, state, hydrated]);

  const reset = useCallback(() => {
    try {
      window.localStorage.removeItem(fullKey);
    } catch {
      /* ignore */
    }
    setState(initialRef.current);
  }, [fullKey]);

  return [state, setState, reset] as const;
}
