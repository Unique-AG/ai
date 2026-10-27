#!/usr/bin/env node
import fs from "node:fs";
import { pathToFileURL } from "node:url";

const IMAGE_REFERENCE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._/:@+-]*$/;
const VARIABLE_PATTERN =
	/\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))/g;

/**
 * @param {string} rawBuildArgs
 * @param {NodeJS.ProcessEnv} environment
 * @returns {Map<string, string>}
 */
export function parseBuildArgs(rawBuildArgs, environment = process.env) {
	const buildArgs = new Map();

	for (const rawLine of rawBuildArgs.split(/\r?\n/)) {
		const line = rawLine.trim();
		if (line === "") {
			continue;
		}

		const separatorIndex = line.indexOf("=");
		if (separatorIndex === -1) {
			const value = environment[line];
			if (value === undefined) {
				throw new Error(`Build argument ${line} has no value`);
			}
			buildArgs.set(line, value);
			continue;
		}

		const name = line.slice(0, separatorIndex).trim();
		const value = line.slice(separatorIndex + 1);
		if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) {
			throw new Error(`Invalid build argument name: ${name}`);
		}
		buildArgs.set(name, value);
	}

	return buildArgs;
}

/**
 * @param {string} value
 * @param {Map<string, string>} variables
 * @returns {string}
 */
function expandVariables(value, variables) {
	return value.replace(VARIABLE_PATTERN, (_match, bracedName, bareName) => {
		const name = bracedName ?? bareName;
		const replacement = variables.get(name);
		if (replacement === undefined) {
			throw new Error(`Unresolved variable in final runtime base: ${name}`);
		}
		return replacement;
	});
}

/**
 * @param {string} contents
 * @returns {string[]}
 */
export function parseInstructions(contents) {
	const physicalLines = contents.replace(/\r\n/g, "\n").split("\n");
	let escapeCharacter = "\\";

	for (const line of physicalLines) {
		const trimmed = line.trim();
		if (trimmed === "") {
			continue;
		}
		const escapeDirective = trimmed.match(/^#\s*escape\s*=\s*([\\`])\s*$/i);
		if (escapeDirective) {
			escapeCharacter = escapeDirective[1];
			continue;
		}
		if (trimmed.startsWith("#")) {
			continue;
		}
		break;
	}

	const instructions = [];
	let continuation = "";

	for (const physicalLine of physicalLines) {
		const trimmed = physicalLine.trim();
		if (trimmed === "" || trimmed.startsWith("#")) {
			continue;
		}

		const lineWithoutTrailingWhitespace = physicalLine.trimEnd();
		if (lineWithoutTrailingWhitespace.endsWith(escapeCharacter)) {
			continuation += `${lineWithoutTrailingWhitespace.slice(0, -1)} `;
			continue;
		}

		const instruction = `${continuation}${physicalLine}`.trim();
		continuation = "";
		if (instruction !== "") {
			instructions.push(instruction);
		}
	}

	if (continuation !== "") {
		throw new Error("Dockerfile ends with an incomplete line continuation");
	}

	return instructions;
}

/**
 * @param {string} instruction
 * @returns {{ source: string, alias?: string } | null}
 */
function parseFromInstruction(instruction) {
	const match = instruction.match(
		/^FROM(?:\s+--platform=(?:"[^"]*"|'[^']*'|\S+))?\s+(?:"([^"]+)"|'([^']+)'|(\S+?))(?:\s+AS\s+([A-Za-z0-9._-]+))?\s*$/i,
	);
	if (!match) {
		return null;
	}

	return {
		source: match[1] ?? match[2] ?? match[3],
		alias: match[4],
	};
}

/**
 * @param {string} contents
 * @param {string} rawBuildArgs
 * @param {NodeJS.ProcessEnv} environment
 * @returns {string}
 */
export function resolveRuntimeBase(
	contents,
	rawBuildArgs = "",
	environment = process.env,
) {
	const suppliedBuildArgs = parseBuildArgs(rawBuildArgs, environment);
	const globalArgs = new Map([
		["TARGETPLATFORM", "linux/amd64"],
		["TARGETOS", "linux"],
		["TARGETARCH", "amd64"],
		["TARGETVARIANT", ""],
	]);
	const stages = new Map();
	let finalExternalBase;
	let foundFrom = false;

	for (const instruction of parseInstructions(contents)) {
		const argMatch = instruction.match(
			/^ARG\s+([A-Za-z_][A-Za-z0-9_]*)(?:=(.*))?$/i,
		);
		if (argMatch && !foundFrom) {
			const [, name, defaultValue] = argMatch;
			const suppliedValue = suppliedBuildArgs.get(name);
			if (suppliedValue !== undefined) {
				globalArgs.set(name, suppliedValue);
			} else if (defaultValue !== undefined) {
				globalArgs.set(name, expandVariables(defaultValue.trim(), globalArgs));
			}
			continue;
		}

		const from = parseFromInstruction(instruction);
		if (!from) {
			continue;
		}

		foundFrom = true;
		const expandedSource = expandVariables(from.source, globalArgs);
		const parentStageBase = stages.get(expandedSource.toLowerCase());
		const externalBase = parentStageBase ?? expandedSource;

		if (from.alias) {
			stages.set(from.alias.toLowerCase(), externalBase);
		}
		finalExternalBase = externalBase;
	}

	if (!foundFrom || finalExternalBase === undefined) {
		throw new Error("Dockerfile has no FROM instruction");
	}
	if (finalExternalBase.toLowerCase() === "scratch") {
		throw new Error("A scratch runtime stage has no base image to scan");
	}
	if (!IMAGE_REFERENCE_PATTERN.test(finalExternalBase)) {
		throw new Error("Resolved runtime base is not a valid image reference");
	}

	return finalExternalBase;
}

function main() {
	const dockerfilePath = process.env.DOCKERFILE_PATH;
	const githubOutput = process.env.GITHUB_OUTPUT;
	if (!dockerfilePath) {
		throw new Error("DOCKERFILE_PATH is required");
	}
	if (!githubOutput) {
		throw new Error("GITHUB_OUTPUT is required");
	}

	const contents = fs.readFileSync(dockerfilePath, "utf8");
	const runtimeBase = resolveRuntimeBase(
		contents,
		process.env.DOCKER_BUILD_ARGS ?? "",
	);
	fs.appendFileSync(githubOutput, `runtime_base_image=${runtimeBase}\n`);
	console.log(`Resolved final runtime base image: ${runtimeBase}`);
}

if (
	process.argv[1] &&
	pathToFileURL(process.argv[1]).href === import.meta.url
) {
	main();
}
