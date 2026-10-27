/**
 * Classify Trivy findings as inherited from the runtime base image or introduced
 * by the application Dockerfile layers.
 */

/** @typedef {import('./types.d.ts').TrivyScan} TrivyScan */
/** @typedef {import('./types.d.ts').TrivyVulnerability} TrivyVulnerability */
/** @typedef {import('./types.d.ts').ClassifiedFinding} ClassifiedFinding */
/** @typedef {import('./types.d.ts').ClassificationResult} ClassificationResult */
/** @typedef {import('./types.d.ts').LayerVerification} LayerVerification */
/** @typedef {import('./types.d.ts').ScanCoverage} ScanCoverage */
/** @typedef {import('./types.d.ts').SeverityPartition} SeverityPartition */

const ALLOWED_SEVERITIES = new Set([
	"UNKNOWN",
	"LOW",
	"MEDIUM",
	"HIGH",
	"CRITICAL",
]);

/**
 * @param {string} csv
 * @returns {Set<string>}
 */
export function parseSeverities(csv) {
	if (csv.trim() === "") {
		throw new Error("Severity list is empty");
	}

	/** @type {Set<string>} */
	const severities = new Set();
	for (const token of csv.split(",")) {
		const severity = token.trim().toUpperCase();
		if (severity === "") {
			continue;
		}
		if (!ALLOWED_SEVERITIES.has(severity)) {
			throw new Error(`Invalid severity token: ${token.trim()}`);
		}
		severities.add(severity);
	}

	if (severities.size === 0) {
		throw new Error("Severity list is empty");
	}

	return severities;
}

/**
 * @param {Set<string>} severities
 * @returns {string}
 */
export function formatSeverities(severities) {
	return [...severities].join(",");
}

/**
 * @param {...Set<string>} sets
 * @returns {Set<string>}
 */
export function unionSeveritySets(...sets) {
	/** @type {Set<string>} */
	const union = new Set();
	for (const set of sets) {
		for (const severity of set) {
			union.add(severity);
		}
	}
	return union;
}

/**
 * @param {ClassifiedFinding[]} findings
 * @param {Set<string>} failSeverities
 * @returns {SeverityPartition}
 */
export function partitionBySeverity(findings, failSeverities) {
	/** @type {ClassifiedFinding[]} */
	const blocking = [];
	/** @type {ClassifiedFinding[]} */
	const advisory = [];

	for (const finding of findings) {
		const severity = (finding.Severity ?? "").toUpperCase();
		if (failSeverities.has(severity)) {
			blocking.push(finding);
		} else {
			advisory.push(finding);
		}
	}

	return { blocking, advisory };
}

/**
 * Counts what Trivy inspected so an all-zero finding report can be told apart
 * from a scan that saw nothing. Requires --list-all-pkgs (Trivy default).
 *
 * @param {TrivyScan} scan
 * @returns {ScanCoverage}
 */
export function summarizeCoverage(scan) {
	let osPackages = 0;
	let languagePackages = 0;
	const targets = [];
	for (const result of scan.Results ?? []) {
		const packageCount = result.Packages?.length ?? 0;
		if (result.Class === "os-pkgs") {
			osPackages += packageCount;
		} else if (result.Class === "lang-pkgs") {
			languagePackages += packageCount;
		}
		targets.push(
			`${result.Target ?? "unknown"} [${result.Type ?? "unknown"}: ${packageCount} pkgs]`,
		);
	}
	return {
		layers: scan.Metadata?.DiffIDs?.length ?? 0,
		osPackages,
		languagePackages,
		targets,
	};
}

/**
 * @param {ScanCoverage} baseCoverage
 * @param {ScanCoverage} finalCoverage
 * @returns {string | null}
 */
export function verifyCoverage(baseCoverage, finalCoverage) {
	const baseTotal = baseCoverage.osPackages + baseCoverage.languagePackages;
	const finalTotal = finalCoverage.osPackages + finalCoverage.languagePackages;
	if (finalTotal === 0) {
		return "Final scan lists no packages; Trivy did not inspect the image contents";
	}
	if (finalTotal < baseTotal) {
		return `Final image lists ${finalTotal} packages but its runtime base lists ${baseTotal}`;
	}
	return null;
}

/**
 * @param {TrivyVulnerability} finding
 * @param {string | undefined} resultClass
 * @param {string | undefined} resultType
 * @returns {string}
 */
export function findingKey(finding, resultClass, resultType) {
	const pkgId = finding.PkgIdentifier?.PURL ?? finding.PkgID;
	if (!pkgId) {
		return "";
	}
	return [
		resultClass ?? "",
		resultType ?? "",
		pkgId,
		finding.InstalledVersion ?? "",
		finding.VulnerabilityID ?? "",
	].join("|");
}

/**
 * @param {TrivyScan} baseScan
 * @param {TrivyScan} finalScan
 * @returns {LayerVerification}
 */
export function verifyBaseLayerPrefix(baseScan, finalScan) {
	const baseDiffIds = baseScan.Metadata?.DiffIDs ?? [];
	const finalDiffIds = finalScan.Metadata?.DiffIDs ?? [];

	if (baseDiffIds.length === 0) {
		return { ok: false, reason: "Base scan has no Metadata.DiffIDs" };
	}
	if (finalDiffIds.length === 0) {
		return { ok: false, reason: "Final scan has no Metadata.DiffIDs" };
	}
	if (finalDiffIds.length < baseDiffIds.length) {
		return {
			ok: false,
			reason: "Final image has fewer layers than the configured runtime base",
		};
	}

	for (let index = 0; index < baseDiffIds.length; index++) {
		if (baseDiffIds[index] !== finalDiffIds[index]) {
			return {
				ok: false,
				reason: `Layer mismatch at index ${index}: expected ${baseDiffIds[index]}, got ${finalDiffIds[index]}`,
			};
		}
	}

	return { ok: true, baseDiffIds };
}

/**
 * @param {TrivyScan} baseScan
 * @returns {Set<string>}
 */
export function buildInheritedKeySet(baseScan) {
	const keys = new Set();
	for (const result of baseScan.Results ?? []) {
		for (const vulnerability of result.Vulnerabilities ?? []) {
			const key = findingKey(vulnerability, result.Class, result.Type);
			if (key !== "") {
				keys.add(key);
			}
		}
	}
	return keys;
}

/**
 * @param {TrivyVulnerability} vulnerability
 * @returns {boolean}
 */
export function isFixable(vulnerability) {
	return (
		vulnerability.FixedVersion != null && vulnerability.FixedVersion !== ""
	);
}

/**
 * @param {TrivyScan} baseScan
 * @param {TrivyScan} finalScan
 * @returns {ClassificationResult}
 */
export function classifyFindings(baseScan, finalScan) {
	const verification = verifyBaseLayerPrefix(baseScan, finalScan);
	if (!verification.ok) {
		throw new Error(verification.reason);
	}

	const inheritedKeys = buildInheritedKeySet(baseScan);
	/** @type {ClassifiedFinding[]} */
	const inherited = [];
	/** @type {ClassifiedFinding[]} */
	const introduced = [];

	for (const result of finalScan.Results ?? []) {
		for (const vulnerability of result.Vulnerabilities ?? []) {
			const key = findingKey(vulnerability, result.Class, result.Type);
			const origin =
				key !== "" && inheritedKeys.has(key) ? "inherited" : "introduced";
			const classified = {
				...vulnerability,
				origin,
				resultClass: result.Class,
				resultType: result.Type,
				resultTarget: result.Target,
			};
			if (origin === "inherited") {
				inherited.push(classified);
			} else {
				introduced.push(classified);
			}
		}
	}

	return {
		inherited,
		introduced,
		inheritedFixable: inherited.filter(isFixable),
		inheritedUnfixable: inherited.filter((finding) => !isFixable(finding)),
		introducedFixable: introduced.filter(isFixable),
		introducedUnfixable: introduced.filter((finding) => !isFixable(finding)),
	};
}
