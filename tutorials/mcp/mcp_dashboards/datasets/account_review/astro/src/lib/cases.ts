// Loads + validates src/data/cases.json (the registry of the 6 RM
// Account-Remediation use cases — Product doc: RM Account-Remediation
// Dashboard — Use Cases) and ports build.py's rule_case_pairs/
// render_case_css/render_open_sections_css from Python string-building to
// typed TS, run at Astro build time.
//
// `caseDefinitionSchema` is the single source of truth for a case's shape:
// CaseActionBar.astro and ClientDetailPage.astro both import the exported
// `CaseDefinition` type instead of redeclaring an ad hoc `UseCase`
// interface each, so the two can no longer silently drift from each other
// or from what's actually in cases.json.
import { z } from "zod";
// The `with { type: "json" }` import attribute is what lets this module load
// under plain `node --test` (see cases.test.ts) as well as Astro/Vite's
// bundler, which accepts a bare JSON import either way.
import casesFile from "../data/cases.json" with { type: "json" };

const caseActionSchema = z.object({
  label: z.string(),
  toast: z.string(),
  instructions: z.string(),
});

export const caseDefinitionSchema = z.object({
  case_id: z.string(),
  use_case: z.number().int().positive(),
  /** Rule codes this case covers — a client row's `rule_code` field selects which case applies. */
  rule_codes: z.array(z.string()).min(1),
  /** Short badge label shown on `.case-badge`. */
  tag: z.string(),
  icon: z.string(),
  /** Title for CaseFigure's primary (fig-prefixed) figure block, if this case has one. */
  figure_title: z.string().optional(),
  /** Title for CaseFigure's secondary (perf-prefixed) figure block, if this case has one. */
  figure2_title: z.string().optional(),
  /** Client-page section `data-key`s to force-open for this case — see renderOpenSectionsCss. */
  open_sections: z.array(z.string()).optional(),
  /** Show the `.figbar` progress-bar fill under CaseFigure's figure rows for this case (default: hidden). */
  figure_bars: z.boolean().optional(),
  /** Two side-by-side actions instead of the default single "Analyse with AI" button. */
  dual_action: z.object({ actions: z.array(caseActionSchema).min(1) }).optional(),
  /** Extra prose appended to the default single-action prompt (see CaseActionBar.astro's promptFor). */
  instructions: z.string().optional(),
  /** Short underlined link label shown in the smart-action banner (defaults to button_label). */
  banner_link: z.string().optional(),
  /** Short bold headline shown before the open issue in the smart-action banner. */
  banner_headline: z.string().optional(),
});

export type CaseDefinition = z.infer<typeof caseDefinitionSchema>;

const casesFileSchema = z.object({
  description: z.string(),
  cases: z.array(caseDefinitionSchema).min(1),
});

export const cases: CaseDefinition[] = casesFileSchema.parse(casesFile).cases;

/** One (rule_code, case) pair per rule_code a case covers — flattens `cases`' `rule_codes` arrays. */
export type CasePair = [ruleCode: string, useCase: CaseDefinition];

/** Flatten every case's rule_codes into (rule_code, case) pairs. */
export function rulePairs(allCases: CaseDefinition[]): CasePair[] {
  const pairs: CasePair[] = [];
  for (const c of allCases) {
    for (const ruleCode of c.rule_codes) pairs.push([ruleCode, c]);
  }
  return pairs;
}

/** [data-rule=...] visibility + badge-label + progress-bar CSS. */
export function renderCaseCss(allCases: CaseDefinition[]): { visibility: string; badges: string; bars: string } {
  const visibility: string[] = [];
  const badges: string[] = [];
  const bars: string[] = [];
  for (const [ruleCode, c] of rulePairs(allCases)) {
    visibility.push(`
.crit-banner[data-rule="${ruleCode}"] .actionbar-case[data-rule="${ruleCode}"] { display: inline; }
.detail[data-rule="${ruleCode}"] .case-figure[data-rule="${ruleCode}"] { display: block; }`);
    if (c.figure2_title) {
      visibility.push(`.detail[data-rule="${ruleCode}"] .case-figure2[data-rule="${ruleCode}"] { display: block; }`);
    }
    const label = c.tag.replace(/"/g, '\\"');
    badges.push(`.case-badge[data-rule="${ruleCode}"]::before { content: "${label}"; }`);
    if (c.banner_headline) {
      const headline = c.banner_headline.replace(/"/g, '\\"');
      visibility.push(
        `.crit-banner[data-rule="${ruleCode}"] .cb-src-fallback { display: none; }`,
        `.crit-banner[data-rule="${ruleCode}"] .cb-src-case[data-rule="${ruleCode}"] { display: inline; }`,
        `.crit-banner[data-rule="${ruleCode}"] .cb-src-case[data-rule="${ruleCode}"]::before { content: "${headline}"; }`
      );
    }
    if (c.figure_bars) {
      bars.push(`.case-figure[data-rule="${ruleCode}"] .figbar { display: block; }`);
    }
  }
  return { visibility: visibility.join("\n"), badges: badges.join("\n"), bars: bars.join("\n") };
}

/** Force-open CSS for generic client-page sections named in a case's open_sections. */
export function renderOpenSectionsCss(allCases: CaseDefinition[]): string {
  const rules: string[] = [];
  for (const [ruleCode, c] of rulePairs(allCases)) {
    for (const key of c.open_sections ?? []) {
      rules.push(`
.detail[data-rule="${ruleCode}"] .sec[data-key="${key}"] > .sec-body { display: block; }
.detail[data-rule="${ruleCode}"] .sec[data-key="${key}"] > .sec-sum .sec-chev { transform: rotate(90deg); }`);
    }
  }
  return rules.join("\n");
}
