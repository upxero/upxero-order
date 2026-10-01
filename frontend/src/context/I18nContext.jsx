import { createContext, useContext, useMemo } from "react";
import { makeT } from "../lib/i18n";

const I18nContext = createContext({ lang: "en", t: (s) => s });

export function I18nProvider({ lang = "en", children }) {
  const value = useMemo(() => ({ lang, t: makeT(lang) }), [lang]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export const useI18n = () => useContext(I18nContext);
export const useT = () => useContext(I18nContext).t;
