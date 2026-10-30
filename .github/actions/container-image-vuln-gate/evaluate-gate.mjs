#!/usr/bin/env node
import fs from "node:fs";
import {
	classifyFindings,
	parseSeverities,
	partitionBySeverity,
	summarizeCoverage,
	verifyCoverage,
} from "./classify-findings.mjs";

const {
	BASE_RESULTS_PATH = "base-trivy-results.json",
	FINAL_RESULTS_PATH = "trivy-results.json",
	RUNTIME_BASE_IMAGE = "",
	FAIL_SEVERITY = "",
	WARN_SEVERITY = "",
	IS_PULL_REQUEST = "false",
	SECURITY_EXCEPTION = "false",
	REPORT_ONLY = "false",
	GITHUB_STEP_SUMMARY = "",
} = process.env;

/**
 * @param {import('./types.d.ts').ClassifiedFinding} finding
 * @returns {string}
 */
function formatFindingLine(finding) {
	const fix =
		finding.FixedVersion != null && finding.FixedVersion !== ""
			? finding.FixedVersion
			: "unfixed";
	return `- **${finding.Severity ?? "UNKNOWN"}** (${finding.origin}) — **${finding.PkgName ?? "unknown"}** \`${finding.InstalledVersion ?? ""}\` → \`${fix}\` — ${finding.VulnerabilityID ?? "unknown"}`;
}

/**
 * @param {import('./types.d.ts').ClassifiedFinding} finding
 * @param {'error' | 'warning'} level
 * @returns {string}
 */
function githubAnnotation(finding, level) {
	const title = `Patchable ${finding.origin} vulnerability`;
	const fixed =
		finding.FixedVersion != null && finding.FixedVersion !== ""
			? ` → ${finding.FixedVersion}`
			: "";
	return `::${level} title=${title}::${finding.PkgName ?? "unknown"} ${finding.InstalledVersion ?? ""}${fixed} ${finding.VulnerabilityID ?? ""} (${finding.Severity ?? "UNKNOWN"}) [${finding.origin}]`;
}

/**
 * @param {import('./types.d.ts').ScanCoverage} coverage
 * @returns {string}
 */
function formatCoverage(coverage) {
	return `${coverage.layers} layers, ${coverage.osPackages} OS pkgs, ${coverage.languagePackages} language pkgs`;
}

function readScan(path) {
	if (!fs.existsSync(path) || fs.statSync(path).size === 0) {
		return null;
	}
	return JSON.parse(fs.readFileSync(path, "utf8"));
}

function appendSummary(text) {
	if (!GITHUB_STEP_SUMMARY) {
		return;
	}
	fs.appendFileSync(GITHUB_STEP_SUMMARY, text);
}

/**
 * @param {import('./types.d.ts').ClassifiedFinding[]} findings
 * @param {string} title
 */
function appendFindingDetails(findings, title) {
	if (findings.length === 0) {
		return;
	}
	appendSummary(`\n<details><summary>${title}</summary>\n\n`);
	for (const finding of findings) {
		appendSummary(`${formatFindingLine(finding)}\n`);
	}
	appendSummary("\n</details>\n");
}

function main() {
	const baseScan = readScan(BASE_RESULTS_PATH);
	const finalScan = readScan(FINAL_RESULTS_PATH);

	if (!finalScan) {
		console.error(
			`::error::Missing final scan results at ${FINAL_RESULTS_PATH}`,
		);
		process.exit(1);
	}

	if (!baseScan) {
		console.error(`::error::Missing base scan results at ${BASE_RESULTS_PATH}`);
		process.exit(1);
	}

	if (!RUNTIME_BASE_IMAGE) {
		console.error("::error::runtime_base_image is required");
		process.exit(1);
	}

	let failSeverities;
	try {
		failSeverities = parseSeverities(FAIL_SEVERITY);
		parseSeverities(WARN_SEVERITY);
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		console.error(`::error::Invalid severity tiers: ${message}`);
		process.exit(1);
	}

	let classification;
	try {
		classification = classifyFindings(baseScan, finalScan);
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		console.error(
			`::error::Runtime base verification failed for ${RUNTIME_BASE_IMAGE}: ${message}`,
		);
		process.exit(1);
	}

	const baseCoverage = summarizeCoverage(baseScan);
	const finalCoverage = summarizeCoverage(finalScan);
	console.log(`Runtime base: ${RUNTIME_BASE_IMAGE}`);
	console.log(`Fail tier: ${FAIL_SEVERITY}; warn tier: ${WARN_SEVERITY}`);
	console.log(`Base coverage: ${formatCoverage(baseCoverage)}`);
	console.log(`Final coverage: ${formatCoverage(finalCoverage)}`);
	for (const target of finalCoverage.targets) {
		console.log(`  final target: ${target}`);
	}

	const coverageProblem = verifyCoverage(baseCoverage, finalCoverage);
	if (coverageProblem) {
		console.error(`::error::Scan coverage check failed: ${coverageProblem}`);
		process.exit(1);
	}

	const {
		inheritedFixable,
		inheritedUnfixable,
		introducedFixable,
		introducedUnfixable,
	} = classification;

	const { blocking: introducedBlocking, advisory: introducedAdvisory } =
		partitionBySeverity(introducedFixable, failSeverities);

	console.log(
		`Inherited fixable: ${inheritedFixable.length}; inherited unfixable: ${inheritedUnfixable.length}`,
	);
	console.log(
		`Introduced fixable: ${introducedFixable.length} (blocking: ${introducedBlocking.length}, advisory: ${introducedAdvisory.length}); introduced unfixable: ${introducedUnfixable.length}`,
	);
	console.log(
		`::notice title=Vulnerability gate::Tiers fail=${FAIL_SEVERITY} warn=${WARN_SEVERITY} — scanned ${formatCoverage(finalCoverage)} against ${RUNTIME_BASE_IMAGE} — introduced blocking: ${introducedBlocking.length}, introduced advisory: ${introducedAdvisory.length}, inherited: ${inheritedFixable.length + inheritedUnfixable.length}`,
	);

	appendSummary("\n### Vulnerability gate (runtime-base aware)\n\n");
	appendSummary(`Runtime base: \`${RUNTIME_BASE_IMAGE}\`\n\n`);
	appendSummary(
		`Fail tier: \`${FAIL_SEVERITY}\` · Warn tier: \`${WARN_SEVERITY}\`\n\n`,
	);
	appendSummary(
		`| Scan | Layers | OS pkgs | Language pkgs |\n| --- | ---: | ---: | ---: |\n| runtime base | ${baseCoverage.layers} | ${baseCoverage.osPackages} | ${baseCoverage.languagePackages} |\n| final image | ${finalCoverage.layers} | ${finalCoverage.osPackages} | ${finalCoverage.languagePackages} |\n\n`,
	);
	appendSummary(
		`| Origin | Blocking | Advisory | Unfixable |\n| --- | ---: | ---: | ---: |\n| inherited | 0 | ${inheritedFixable.length} | ${inheritedUnfixable.length} |\n| introduced | ${introducedBlocking.length} | ${introducedAdvisory.length} | ${introducedUnfixable.length} |\n\n`,
	);

	for (const finding of [...inheritedUnfixable, ...introducedUnfixable]) {
		console.log(
			`::warning title=Unpatched vulnerability::${finding.PkgName ?? "unknown"} ${finding.VulnerabilityID ?? ""} (${finding.Severity ?? "UNKNOWN"}) — no patch available [${finding.origin}]`,
		);
	}

	for (const finding of inheritedFixable) {
		console.log(githubAnnotation(finding, "warning"));
	}

	for (const finding of introducedAdvisory) {
		console.log(githubAnnotation(finding, "warning"));
	}

	const isPullRequest = IS_PULL_REQUEST === "true";
	const hasSecurityException = SECURITY_EXCEPTION === "true";
	const reportOnly = REPORT_ONLY === "true";
	const blocks = isPullRequest && !hasSecurityException && !reportOnly;

	if (introducedBlocking.length === 0) {
		appendSummary("✅ No blocking vulnerabilities introduced by this image.\n");
		appendFindingDetails(
			introducedAdvisory,
			"Introduced advisory findings (warn tier)",
		);
		appendFindingDetails(
			inheritedFixable,
			"Inherited patchable findings (base image)",
		);
		process.exit(0);
	}

	appendFindingDetails(
		introducedBlocking,
		"Introduced blocking findings (fail tier)",
	);
	appendFindingDetails(
		introducedAdvisory,
		"Introduced advisory findings (warn tier)",
	);
	appendFindingDetails(
		inheritedFixable,
		"Inherited patchable findings (base image)",
	);

	for (const finding of introducedBlocking) {
		console.log(githubAnnotation(finding, blocks ? "error" : "warning"));
	}

	if (blocks) {
		console.error(
			`::error::${introducedBlocking.length} patchable introduced finding(s) in the fail tier (${FAIL_SEVERITY}). Fix the application image or add the security-exception label and re-run this job.`,
		);
		process.exit(1);
	}

	if (hasSecurityException) {
		appendSummary(
			"\nsecurity-exception label set — introduced blocking findings reported as warnings only.\n",
		);
	} else if (reportOnly) {
		console.log(
			`::warning title=Vulnerability gate::Report-only run — ${introducedBlocking.length} fail-tier finding(s) reported as warnings. See the job summary.`,
		);
		appendSummary(
			"\nReport-only run — introduced blocking findings reported as warnings only.\n",
		);
	} else {
		appendSummary(
			"\nNon-PR run — introduced blocking findings reported as warnings only.\n",
		);
	}
}

main();
