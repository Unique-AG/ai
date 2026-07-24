// Ports build.py's rule_case_pairs/render_case_css/render_open_sections_css
// from Python string-building to plain JS, run at Astro build time. Same
// registry (src/data/cases.json, copied from ../dashboard-v005/src/cases.json),
// same generated CSS shape — just template literals instead of f-strings.

/** Flatten each case's rule_codes into (rule_code, case) pairs. */
export function rulePairs(cases) {
  const pairs = [];
  for (const c of cases) {
    for (const ruleCode of c.rule_codes) pairs.push([ruleCode, c]);
  }
  return pairs;
}

/** [data-rule=...] visibility + badge-label + progress-bar CSS. */
export function renderCaseCss(cases) {
  const visibility = [];
  const badges = [];
  const bars = [];
  for (const [ruleCode, c] of rulePairs(cases)) {
    visibility.push(`
.actionbar[data-rule="${ruleCode}"] .actionbar-case[data-rule="${ruleCode}"] { display: flex; }
.detail[data-rule="${ruleCode}"] .case-figure[data-rule="${ruleCode}"] { display: block; }`);
    if (c.figure2_title) {
      visibility.push(
        `.detail[data-rule="${ruleCode}"] .case-figure2[data-rule="${ruleCode}"] { display: block; }`
      );
    }
    const label = c.tag.replace(/"/g, '\\"');
    badges.push(`.case-badge[data-rule="${ruleCode}"]::before { content: "${label}"; }`);
    if (c.figure_bars) {
      bars.push(`.case-figure[data-rule="${ruleCode}"] .figbar { display: block; }`);
    }
  }
  return { visibility: visibility.join("\n"), badges: badges.join("\n"), bars: bars.join("\n") };
}

/** Force-open CSS for generic client-page sections named in a case's open_sections. */
export function renderOpenSectionsCss(cases) {
  const rules = [];
  for (const [ruleCode, c] of rulePairs(cases)) {
    for (const key of c.open_sections ?? []) {
      rules.push(`
.detail[data-rule="${ruleCode}"] .sec[data-key="${key}"] > .sec-body { display: block; }
.detail[data-rule="${ruleCode}"] .sec[data-key="${key}"] > .sec-sum .sec-chev { transform: rotate(90deg); }`);
    }
  }
  return rules.join("\n");
}
