import {
  createContext,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import type { Locale } from "./types";
import { en } from "./locales/en";
import type { Translations } from "./types";

type NestedValue = string | { [key: string]: NestedValue };

const messages: Record<Locale, Translations> = { en } as Record<Locale, Translations>;

function getNestedValue(obj: Translations, path: string): string | undefined {
  return path.split(".").reduce((acc: NestedValue | undefined, key) => {
    if (acc && typeof acc === "object" && key in acc) {
      return (acc as Record<string, NestedValue>)[key];
    }
    return undefined;
  }, obj as unknown as NestedValue) as string | undefined;
}

function interpolate(
  template: string,
  params?: Record<string, string | number>,
): string {
  if (!params) return template;
  return Object.entries(params).reduce(
    (str, [k, v]) =>
      str.replace(new RegExp(`\\{\\s*${k}\\s*\\}`, "g"), String(v)),
    template,
  );
}

export function translate(
  locale: Locale,
  key: string,
  params?: Record<string, string | number>,
): string {
  const msg =
    getNestedValue(messages[locale] || en, key) ??
    key;
  return interpolate(msg, params);
}

interface LocaleContextValue {
  locale: Locale;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({ children }: { children: ReactNode }) {
  const value = useMemo(() => ({ locale: "en" as Locale, t: (key: string, params?: Record<string, string | number>) => translate("en", key, params) }), []);

  return (
    <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
  );
}

export function useLocale() {
  const ctx = useContext(LocaleContext);
  if (!ctx)
    throw new Error("useLocale must be used within a LocaleProvider");
  return ctx;
}

export type { Locale };
