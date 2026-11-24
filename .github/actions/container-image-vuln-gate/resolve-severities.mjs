#!/usr/bin/env node
import fs from "node:fs";
import { pathToFileURL } from "node:url";
import {
	formatSeverities,
	parseSeverities,
	unionSeveritySets,
} from "./classify-findings.mjs";

const DEFAULT_FAIL = "CRITICAL,HIGH";
const DEFAULT_WARN = "MEDIUM";

/**
 * @param {string | undefined} inputFail
 * @param {string | undefined} inputWarn
 * @returns {{ failSeverity: string; warnSeverity: string; scanSeverity: string }}
 */
export function resolveSeverities(inputFail, inputWarn) {
	const failRaw = inputFail?.trim() ? inputFail : DEFAULT_FAIL;
	const warnRaw = inputWarn?.trim() ? inputWarn : DEFAULT_WARN;
	const failSet = parseSeverities(failRaw);
	const warnSet = parseSeverities(warnRaw);
	const scanSet = unionSeveritySets(failSet, warnSet);
	return {
		failSeverity: formatSeverities(failSet),
		warnSeverity: formatSeverities(warnSet),
		scanSeverity: formatSeverities(scanSet),
	};
}

function main() {
	const { INPUT_FAIL = "", INPUT_WARN = "", GITHUB_OUTPUT = "" } = process.env;
	if (!GITHUB_OUTPUT) {
		throw new Error("GITHUB_OUTPUT is required");
	}

	const resolved = resolveSeverities(INPUT_FAIL, INPUT_WARN);
	console.log(
		`Severity tiers: fail=${resolved.failSeverity} warn=${resolved.warnSeverity} scan=${resolved.scanSeverity}`,
	);

	fs.appendFileSync(
		GITHUB_OUTPUT,
		[
			`fail_severity=${resolved.failSeverity}`,
			`warn_severity=${resolved.warnSeverity}`,
			`scan_severity=${resolved.scanSeverity}`,
		].join("\n") + "\n",
	);
}

if (
	process.argv[1] &&
	pathToFileURL(process.argv[1]).href === import.meta.url
) {
	main();
}
