import fs from "node:fs";
import path from "node:path";

import { renderCaseCss, renderOpenSectionsCss, type CaseDefinition } from "./cases.ts";

/** Inlines case-driven CSS placeholders in src/styles.css at build time. */
export function buildPageCss(allCases: CaseDefinition[]): string {
  const { visibility, badges, bars } = renderCaseCss(allCases);
  const openSectionsCss = renderOpenSectionsCss(allCases);

  const baseCssPath = path.resolve(process.cwd(), "src/styles.css");
  const baseCss = fs.readFileSync(baseCssPath, "utf-8");

  return baseCss
    .replace("/* __CASE_VISIBILITY_CSS__ */", visibility)
    .replace("/* __CASE_BADGE_CSS__ */", badges)
    .replace("/* __CASE_BARS_CSS__ */", bars)
    .replace("/* __CASE_OPEN_SECTIONS_CSS__ */", openSectionsCss);
}
