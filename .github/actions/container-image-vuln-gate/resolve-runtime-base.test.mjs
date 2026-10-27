import assert from "node:assert/strict";
import test from "node:test";
import {
	parseBuildArgs,
	parseInstructions,
	resolveRuntimeBase,
} from "./resolve-runtime-base.mjs";

test("resolves the external base of the final stage", () => {
	const dockerfile = `
    FROM node:24 AS build
    RUN npm run build
    FROM registry.example.com/runtime:24 AS runtime
    COPY --from=build /app /app
  `;

	assert.equal(
		resolveRuntimeBase(dockerfile),
		"registry.example.com/runtime:24",
	);
});

test("resolves aliases recursively to their external base", () => {
	const dockerfile = `
    FROM registry.example.com/runtime:24 AS runtime
    RUN apt-get update
    FROM runtime AS configured
    RUN useradd app
    FROM configured AS final
  `;

	assert.equal(
		resolveRuntimeBase(dockerfile),
		"registry.example.com/runtime:24",
	);
});

test("uses global ARG defaults in FROM references", () => {
	const dockerfile = `
    ARG REGISTRY=registry.example.com
    ARG VERSION=24
    FROM \${REGISTRY}/runtime:\${VERSION} AS runtime
  `;

	assert.equal(
		resolveRuntimeBase(dockerfile),
		"registry.example.com/runtime:24",
	);
});

test("build arguments override global ARG defaults", () => {
	const dockerfile = `
    ARG VERSION=24
    FROM registry.example.com/runtime:\${VERSION} AS runtime
  `;

	assert.equal(
		resolveRuntimeBase(dockerfile, "VERSION=26"),
		"registry.example.com/runtime:26",
	);
});

test("handles platform flags, comments, and continuations", () => {
	const dockerfile = `
    # syntax=docker/dockerfile:1
    ARG REGISTRY=registry.example.com
    FROM --platform=linux/amd64 \\
      \${REGISTRY}/runtime:24 \\
      AS runtime
  `;

	assert.equal(
		resolveRuntimeBase(dockerfile),
		"registry.example.com/runtime:24",
	);
});

test("fails closed on unresolved FROM variables", () => {
	assert.throws(
		() => resolveRuntimeBase(`FROM registry.example.com/runtime:\${VERSION}`),
		/Unresolved variable/,
	);
});

test("fails closed for scratch images", () => {
	assert.throws(
		() => resolveRuntimeBase("FROM scratch"),
		/no base image to scan/,
	);
});

test("fails closed when the Dockerfile has no FROM instruction", () => {
	assert.throws(
		() => resolveRuntimeBase("RUN echo no-base"),
		/no FROM instruction/,
	);
});

test("parseBuildArgs resolves key-only values from the environment", () => {
	assert.deepEqual(
		parseBuildArgs("VERSION", { VERSION: "26" }),
		new Map([["VERSION", "26"]]),
	);
});

test("parseInstructions supports the backtick escape directive", () => {
	const instructions = parseInstructions(
		"# escape=`\nFROM registry.example.com/runtime:`\n 24 AS runtime\n",
	);

	assert.deepEqual(instructions, [
		"FROM registry.example.com/runtime:  24 AS runtime",
	]);
});
