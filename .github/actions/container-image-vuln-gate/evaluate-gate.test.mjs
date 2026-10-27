import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const evaluatorPath = path.join(import.meta.dirname, "evaluate-gate.mjs");

const inheritedFinding = {
	VulnerabilityID: "CVE-2024-0001",
	PkgName: "libssl3",
	PkgIdentifier: { PURL: "pkg:deb/debian/libssl3@3.0.1" },
	InstalledVersion: "3.0.1",
	FixedVersion: "3.0.2",
	Severity: "HIGH",
};

const introducedCriticalFinding = {
	VulnerabilityID: "CVE-2024-0002",
	PkgName: "application-package",
	PkgIdentifier: { PURL: "pkg:npm/application-package@1.0.0" },
	InstalledVersion: "1.0.0",
	FixedVersion: "1.0.1",
	Severity: "CRITICAL",
};

const introducedHighFinding = {
	...introducedCriticalFinding,
	VulnerabilityID: "CVE-2024-0003",
	Severity: "HIGH",
};

const introducedMediumFinding = {
	...introducedCriticalFinding,
	VulnerabilityID: "CVE-2024-0004",
	Severity: "MEDIUM",
};

const basePackages = [{ Name: "libssl3" }, { Name: "bash" }];
const applicationPackages = [{ Name: "application-package" }];

function scan(diffIds, vulnerabilities, { osPackages, languagePackages }) {
	return {
		Metadata: { DiffIDs: diffIds },
		Results: [
			{
				Target: "image (debian 13)",
				Class: "os-pkgs",
				Type: "debian",
				Packages: osPackages,
				Vulnerabilities: vulnerabilities,
			},
			{
				Target: "Node.js",
				Class: "lang-pkgs",
				Type: "node-pkg",
				Packages: languagePackages,
				Vulnerabilities: [],
			},
		],
	};
}

function runEvaluator({
	finalFindings,
	securityException = false,
	omitFinalScan = false,
	finalOsPackages = basePackages,
	finalLanguagePackages = applicationPackages,
	failSeverity = "CRITICAL,HIGH",
	warnSeverity = "MEDIUM",
}) {
	const directory = fs.mkdtempSync(path.join(os.tmpdir(), "vuln-gate-"));
	const basePath = path.join(directory, "base.json");
	const finalPath = path.join(directory, "final.json");
	const summaryPath = path.join(directory, "summary.md");

	fs.writeFileSync(
		basePath,
		JSON.stringify(
			scan(["sha256:base"], [inheritedFinding], {
				osPackages: basePackages,
				languagePackages: [],
			}),
		),
	);
	if (!omitFinalScan) {
		fs.writeFileSync(
			finalPath,
			JSON.stringify(
				scan(["sha256:base", "sha256:application"], finalFindings, {
					osPackages: finalOsPackages,
					languagePackages: finalLanguagePackages,
				}),
			),
		);
	}

	const result = spawnSync(process.execPath, [evaluatorPath], {
		encoding: "utf8",
		env: {
			...process.env,
			BASE_RESULTS_PATH: basePath,
			FINAL_RESULTS_PATH: finalPath,
			GITHUB_STEP_SUMMARY: summaryPath,
			RUNTIME_BASE_IMAGE: "registry.example.com/runtime:24",
			FAIL_SEVERITY: failSeverity,
			WARN_SEVERITY: warnSeverity,
			IS_PULL_REQUEST: "true",
			SECURITY_EXCEPTION: String(securityException),
		},
	});
	result.summary = fs.existsSync(summaryPath)
		? fs.readFileSync(summaryPath, "utf8")
		: "";
	return result;
}

test("passes a pull request with inherited findings only", () => {
	const result = runEvaluator({ finalFindings: [inheritedFinding] });

	assert.equal(result.status, 0);
	assert.match(result.stdout, /Patchable inherited vulnerability/);
	assert.match(result.summary, /\| inherited \| 0 \| 1 \| 0 \|/);
	assert.doesNotMatch(result.summary, /\| inherited \| 1 \|/);
});

test("reports scan coverage as a notice annotation on a clean run", () => {
	const result = runEvaluator({ finalFindings: [] });

	assert.equal(result.status, 0);
	assert.match(
		result.stdout,
		/Base coverage: 1 layers, 2 OS pkgs, 0 language pkgs/,
	);
	assert.match(
		result.stdout,
		/Final coverage: 2 layers, 2 OS pkgs, 1 language pkgs/,
	);
	assert.match(
		result.stdout,
		/::notice title=Vulnerability gate::Tiers fail=CRITICAL,HIGH warn=MEDIUM — scanned 2 layers, 2 OS pkgs, 1 language pkgs against registry\.example\.com\/runtime:24 — introduced blocking: 0, introduced advisory: 0/,
	);
});

test("fails closed when the final scan lists no packages", () => {
	const result = runEvaluator({
		finalFindings: [],
		finalOsPackages: [],
		finalLanguagePackages: [],
	});

	assert.equal(result.status, 1);
	assert.match(result.stderr, /Final scan lists no packages/);
});

test("fails closed when the final image lists fewer packages than its base", () => {
	const result = runEvaluator({
		finalFindings: [],
		finalOsPackages: [{ Name: "bash" }],
		finalLanguagePackages: [],
	});

	assert.equal(result.status, 1);
	assert.match(
		result.stderr,
		/Final image lists 1 packages but its runtime base lists 2/,
	);
});

test("fails a pull request with an introduced blocking finding", () => {
	const result = runEvaluator({
		finalFindings: [inheritedFinding, introducedCriticalFinding],
	});

	assert.equal(result.status, 1);
	assert.match(
		result.stderr,
		/patchable introduced finding\(s\) in the fail tier/,
	);
});

test("fails on an introduced HIGH finding under default fail tier", () => {
	const result = runEvaluator({
		finalFindings: [introducedHighFinding],
	});

	assert.equal(result.status, 1);
	assert.match(
		result.stderr,
		/patchable introduced finding\(s\) in the fail tier/,
	);
});

test("warns but passes on an introduced MEDIUM under the default warn tier", () => {
	const result = runEvaluator({
		finalFindings: [introducedMediumFinding],
	});

	assert.equal(result.status, 0);
	assert.match(
		result.stdout,
		/::warning title=Patchable introduced vulnerability/,
	);
	assert.doesNotMatch(
		result.stderr,
		/patchable introduced finding\(s\) in the fail tier/,
	);
});

test("warns but passes on an introduced HIGH when the fail tier is lowered", () => {
	const result = runEvaluator({
		finalFindings: [introducedHighFinding],
		failSeverity: "CRITICAL",
		warnSeverity: "HIGH,MEDIUM",
	});

	assert.equal(result.status, 0);
	assert.match(
		result.stdout,
		/::warning title=Patchable introduced vulnerability/,
	);
	assert.doesNotMatch(
		result.stderr,
		/patchable introduced finding\(s\) in the fail tier/,
	);
});

test("fails on mixed CRITICAL and HIGH introduced findings under default fail tier", () => {
	const result = runEvaluator({
		finalFindings: [introducedCriticalFinding, introducedHighFinding],
	});

	assert.equal(result.status, 1);
	assert.match(
		result.stdout,
		/::error title=Patchable introduced vulnerability::.*CVE-2024-0002 \(CRITICAL\)/,
	);
	assert.match(
		result.stdout,
		/::error title=Patchable introduced vulnerability::.*CVE-2024-0003 \(HIGH\)/,
	);
	assert.match(
		result.stderr,
		/patchable introduced finding\(s\) in the fail tier/,
	);
});

test("tightening fail tier to include HIGH blocks advisory findings", () => {
	const result = runEvaluator({
		finalFindings: [introducedHighFinding],
		failSeverity: "CRITICAL,HIGH",
	});

	assert.equal(result.status, 1);
	assert.match(
		result.stderr,
		/patchable introduced finding\(s\) in the fail tier/,
	);
});

test("security-exception bypasses an introduced blocking finding", () => {
	const result = runEvaluator({
		finalFindings: [introducedCriticalFinding],
		securityException: true,
	});

	assert.equal(result.status, 0);
	assert.match(
		result.stdout,
		/::warning title=Patchable introduced vulnerability/,
	);
});

test("fails closed when the fail tier is empty", () => {
	const result = runEvaluator({
		finalFindings: [],
		failSeverity: "",
	});

	assert.equal(result.status, 1);
	assert.match(result.stderr, /Invalid severity tiers/);
});

test("fails closed when the final scan report is missing", () => {
	const result = runEvaluator({
		finalFindings: [],
		omitFinalScan: true,
	});

	assert.equal(result.status, 1);
	assert.match(result.stderr, /Missing final scan results/);
});
