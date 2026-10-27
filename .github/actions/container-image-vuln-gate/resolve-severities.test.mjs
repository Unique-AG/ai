import assert from "node:assert/strict";
import test from "node:test";
import { resolveSeverities } from "./resolve-severities.mjs";

test("resolveSeverities applies defaults for empty pass-through inputs", () => {
	assert.deepEqual(resolveSeverities("", ""), {
		failSeverity: "CRITICAL,HIGH",
		warnSeverity: "MEDIUM",
		scanSeverity: "CRITICAL,HIGH,MEDIUM",
	});
});

test("resolveSeverities honors explicit caller inputs", () => {
	assert.deepEqual(resolveSeverities("HIGH", "MEDIUM"), {
		failSeverity: "HIGH",
		warnSeverity: "MEDIUM",
		scanSeverity: "HIGH,MEDIUM",
	});
});

test("resolveSeverities keeps HIGH findings in the scan when fail tier is lowered", () => {
	assert.deepEqual(resolveSeverities("CRITICAL", "HIGH,MEDIUM"), {
		failSeverity: "CRITICAL",
		warnSeverity: "HIGH,MEDIUM",
		scanSeverity: "CRITICAL,HIGH,MEDIUM",
	});
});

test("resolveSeverities deduplicates overlapping tiers for the scan union", () => {
	assert.deepEqual(resolveSeverities("CRITICAL,HIGH", "HIGH,MEDIUM"), {
		failSeverity: "CRITICAL,HIGH",
		warnSeverity: "HIGH,MEDIUM",
		scanSeverity: "CRITICAL,HIGH,MEDIUM",
	});
});

test("resolveSeverities rejects invalid tokens", () => {
	assert.throws(
		() => resolveSeverities("SEVERE", "HIGH"),
		/Invalid severity token: SEVERE/,
	);
});
