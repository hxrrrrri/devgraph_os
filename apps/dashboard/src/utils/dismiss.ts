import { useCallback, useEffect, useState } from "react";

const STORAGE_PREFIX = "devgraph:dismissed:";

function readDismissed(key: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(STORAGE_PREFIX + key) === "1";
  } catch {
    return false;
  }
}

function writeDismissed(key: string, value: boolean): void {
  if (typeof window === "undefined") return;
  try {
    if (value) window.localStorage.setItem(STORAGE_PREFIX + key, "1");
    else window.localStorage.removeItem(STORAGE_PREFIX + key);
  } catch {
    /* storage disabled or full — fall back to in-memory state only */
  }
}

export function useDismissible(key: string): { dismissed: boolean; dismiss: () => void; reset: () => void } {
  const [dismissed, setDismissed] = useState<boolean>(() => readDismissed(key));

  useEffect(() => {
    setDismissed(readDismissed(key));
  }, [key]);

  const dismiss = useCallback(() => {
    writeDismissed(key, true);
    setDismissed(true);
  }, [key]);

  const reset = useCallback(() => {
    writeDismissed(key, false);
    setDismissed(false);
  }, [key]);

  return { dismissed, dismiss, reset };
}
