import assert from "node:assert/strict";
import test from "node:test";
import {
	buildInheritedKeySet,
	classifyFindings,
	findingKey,
	formatSeverities,
	isFixable,
	parseSeverities,
	partitionBySeverity,
	summarizeCoverage,
	unionSeveritySets,
	verifyBaseLayerPrefix,
	verifyCoverage,
} from "./classify-findings.mjs";

const baseLayerOne = "sha256:base-layer-1";
const baseLayerTwo = "sha256:base-layer-2";
const appLayer = "sha256:app-layer-1";

/** @type {import('./types.d.ts').TrivyScan} */
const baseScan = {
	Metadata: {
		DiffIDs: [baseLayerOne, baseLayerTwo],
	},
	Results: [
		{
			Class: "os-pkgs",
			Type: "debian",
			Vulnerabilities: [
				{
					VulnerabilityID: "CVE-2024-0001",
					PkgName: "libssl3",
					PkgID: "libssl3@3.0.1",
					PkgIdentifier: { PURL: "pkg:deb/debian/libssl3@3.0.1" },
					InstalledVersion: "3.0.1",
					FixedVersion: "3.0.2",
					Severity: "HIGH",
				},
			],
		},
		{
			Class: "lang-pkgs",
			Type: "npm",
			Vulnerabilities: [
				{
					VulnerabilityID: "CVE-2024-0002",
					PkgName: "lodash",
					PkgIdentifier: { PURL: "pkg:npm/lodash@4.17.20" },
					InstalledVersion: "4.17.20",
					FixedVersion: "4.17.21",
					Severity: "CRITICAL",
				},
			],
		},
	],
};

test("findingKey prefers PURL over PkgID", () => {
	const key = findingKey(
		{
			VulnerabilityID: "CVE-2024-0001",
			PkgID: "libssl3@3.0.1",
			PkgIdentifier: { PURL: "pkg:deb/debian/libssl3@3.0.1" },
			InstalledVersion: "3.0.1",
		},
		"os-pkgs",
		"debian",
	);
	assert.equal(
		key,
		"os-pkgs|debian|pkg:deb/debian/libssl3@3.0.1|3.0.1|CVE-2024-0001",
	);
});

test("verifyBaseLayerPrefix accepts matching prefix", () => {
	const finalScan = {
		Metadata: {
			DiffIDs: [baseLayerOne, baseLayerTwo, appLayer],
		},
	};
	const result = verifyBaseLayerPrefix(baseScan, finalScan);
	assert.equal(result.ok, true);
});

test("verifyBaseLayerPrefix rejects mismatched base", () => {
	const finalScan = {
		Metadata: {
			DiffIDs: ["sha256:other-base", baseLayerTwo, appLayer],
		},
	};
	const result = verifyBaseLayerPrefix(baseScan, finalScan);
	assert.equal(result.ok, false);
});

test("classifyFindings marks identical base findings as inherited", () => {
	const finalScan = {
		Metadata: {
			DiffIDs: [baseLayerOne, baseLayerTwo, appLayer],
		},
		Results: baseScan.Results,
	};

	const result = classifyFindings(baseScan, finalScan);
	assert.equal(result.inherited.length, 2);
	assert.equal(result.introduced.length, 0);
	assert.equal(result.inheritedFixable.length, 2);
});

test("classifyFindings treats application-added OS packages as introduced", () => {
	const finalScan = {
		Metadata: {
			DiffIDs: [baseLayerOne, baseLayerTwo, appLayer],
		},
		Results: [
			...(baseScan.Results ?? []),
			{
				Class: "os-pkgs",
				Type: "debian",
				Vulnerabilities: [
					{
						VulnerabilityID: "CVE-2024-9999",
						PkgName: "libreoffice-core",
						PkgIdentifier: { PURL: "pkg:deb/debian/libreoffice-core@7.0.0" },
						InstalledVersion: "7.0.0",
						FixedVersion: "7.0.1",
						Severity: "HIGH",
					},
				],
			},
		],
	};

	const result = classifyFindings(baseScan, finalScan);
	assert.equal(result.inherited.length, 2);
	assert.equal(result.introduced.length, 1);
	assert.equal(result.introducedFixable[0]?.PkgName, "libreoffice-core");
});

test("classifyFindings treats changed package versions as introduced", () => {
	const finalScan = {
		Metadata: {
			DiffIDs: [baseLayerOne, baseLayerTwo, appLayer],
		},
		Results: [
			{
				Class: "os-pkgs",
				Type: "debian",
				Vulnerabilities: [
					{
						VulnerabilityID: "CVE-2024-0001",
						PkgName: "libssl3",
						PkgIdentifier: { PURL: "pkg:deb/debian/libssl3@3.0.3" },
						InstalledVersion: "3.0.3",
						FixedVersion: "3.0.4",
						Severity: "HIGH",
					},
				],
			},
		],
	};

	const result = classifyFindings(baseScan, finalScan);
	assert.equal(result.inherited.length, 0);
	assert.equal(result.introduced.length, 1);
});

test("classifyFindings treats findings without a package identity as introduced", () => {
	const unidentifiedFinding = {
		VulnerabilityID: "CVE-2024-0003",
		PkgName: "unknown-package",
		InstalledVersion: "1.0.0",
		FixedVersion: "1.0.1",
		Severity: "HIGH",
	};
	const unidentifiedBaseScan = {
		...baseScan,
		Results: [
			{
				Class: "lang-pkgs",
				Type: "unknown",
				Vulnerabilities: [unidentifiedFinding],
			},
		],
	};
	const finalScan = {
		Metadata: {
			DiffIDs: [baseLayerOne, baseLayerTwo, appLayer],
		},
		Results: unidentifiedBaseScan.Results,
	};

	const result = classifyFindings(unidentifiedBaseScan, finalScan);
	assert.equal(result.inherited.length, 0);
	assert.equal(result.introduced.length, 1);
});

test("classifyFindings separates introduced unfixable findings", () => {
	const finalScan = {
		Metadata: {
			DiffIDs: [baseLayerOne, baseLayerTwo, appLayer],
		},
		Results: [
			{
				Class: "lang-pkgs",
				Type: "npm",
				Vulnerabilities: [
					{
						VulnerabilityID: "CVE-2024-0004",
						PkgName: "application-package",
						PkgIdentifier: {
							PURL: "pkg:npm/application-package@1.0.0",
						},
						InstalledVersion: "1.0.0",
						FixedVersion: "",
						Severity: "HIGH",
					},
				],
			},
		],
	};

	const result = classifyFindings(baseScan, finalScan);
	assert.equal(result.introducedFixable.length, 0);
	assert.equal(result.introducedUnfixable.length, 1);
});

test("isFixable distinguishes patched and unpatched findings", () => {
	assert.equal(isFixable({ FixedVersion: "1.2.3" }), true);
	assert.equal(isFixable({ FixedVersion: "" }), false);
	assert.equal(isFixable({ FixedVersion: null }), false);
});

test("buildInheritedKeySet includes library packages from the base", () => {
	const keys = buildInheritedKeySet(baseScan);
	assert.equal(keys.size, 2);
	assert.match([...keys][1] ?? "", /lodash/);
});

test("summarizeCoverage counts layers and packages per result class", () => {
	const coverage = summarizeCoverage({
		Metadata: { DiffIDs: [baseLayerOne, appLayer] },
		Results: [
			{
				Target: "image (debian 13)",
				Class: "os-pkgs",
				Type: "debian",
				Packages: [{ Name: "bash" }, { Name: "libssl3" }],
			},
			{
				Target: "Node.js",
				Class: "lang-pkgs",
				Type: "node-pkg",
				Packages: [{ Name: "lodash" }],
			},
			{ Target: "no-packages", Class: "lang-pkgs", Type: "gobinary" },
		],
	});

	assert.deepEqual(coverage, {
		layers: 2,
		osPackages: 2,
		languagePackages: 1,
		targets: [
			"image (debian 13) [debian: 2 pkgs]",
			"Node.js [node-pkg: 1 pkgs]",
			"no-packages [gobinary: 0 pkgs]",
		],
	});
});

test("summarizeCoverage returns zeros for a scan without results", () => {
	assert.deepEqual(summarizeCoverage({}), {
		layers: 0,
		osPackages: 0,
		languagePackages: 0,
		targets: [],
	});
});

test("verifyCoverage accepts a final image that contains its base", () => {
	const base = { layers: 1, osPackages: 80, languagePackages: 5, targets: [] };
	const final = {
		layers: 3,
		osPackages: 80,
		languagePackages: 900,
		targets: [],
	};
	assert.equal(verifyCoverage(base, final), null);
});

test("verifyCoverage rejects an empty final scan", () => {
	const base = { layers: 1, osPackages: 80, languagePackages: 0, targets: [] };
	const final = { layers: 3, osPackages: 0, languagePackages: 0, targets: [] };
	assert.match(verifyCoverage(base, final) ?? "", /lists no packages/);
});

test("verifyCoverage rejects a final image with fewer packages than its base", () => {
	const base = { layers: 1, osPackages: 80, languagePackages: 5, targets: [] };
	const final = { layers: 3, osPackages: 40, languagePackages: 0, targets: [] };
	assert.match(
		verifyCoverage(base, final) ?? "",
		/lists 40 packages but its runtime base lists 85/,
	);
});

test("parseSeverities normalizes comma-separated tokens", () => {
	assert.deepEqual(
		[...parseSeverities(" critical , high ")],
		["CRITICAL", "HIGH"],
	);
});

test("parseSeverities rejects empty and invalid lists", () => {
	assert.throws(() => parseSeverities(""), /Severity list is empty/);
	assert.throws(
		() => parseSeverities("CRITICAL,SEVERE"),
		/Invalid severity token/,
	);
});

test("unionSeveritySets deduplicates severities", () => {
	assert.equal(
		formatSeverities(
			unionSeveritySets(
				parseSeverities("CRITICAL,HIGH"),
				parseSeverities("HIGH,MEDIUM"),
			),
		),
		"CRITICAL,HIGH,MEDIUM",
	);
});

test("partitionBySeverity splits introduced fixable findings by fail tier", () => {
	const findings = [
		{ Severity: "CRITICAL", PkgName: "a" },
		{ Severity: "HIGH", PkgName: "b" },
		{ Severity: "MEDIUM", PkgName: "c" },
	];
	const failSet = parseSeverities("CRITICAL");
	const { blocking, advisory } = partitionBySeverity(findings, failSet);
	assert.equal(blocking.length, 1);
	assert.equal(advisory.length, 2);
	assert.equal(blocking[0]?.PkgName, "a");
});
