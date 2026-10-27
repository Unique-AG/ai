#!/usr/bin/env node
import fs from "node:fs";
import { pathToFileURL } from "node:url";

const MAX_LABEL_PAGES = 10;
const MAX_RESPONSE_BYTES = 1024 * 1024;

function validateInputs({
	apiUrl,
	repository,
	pullRequestNumber,
	label,
	token,
}) {
	const parsedApiUrl = new URL(apiUrl);
	if (parsedApiUrl.protocol !== "https:") {
		throw new Error("GitHub API URL must use HTTPS");
	}
	if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository)) {
		throw new Error("GITHUB_REPOSITORY is invalid");
	}
	if (!/^[1-9][0-9]*$/.test(pullRequestNumber)) {
		throw new Error("Pull request number is invalid");
	}
	if (label === "" || label.length > 50 || /[\r\n]/.test(label)) {
		throw new Error("Label is invalid");
	}
	if (token === "") {
		throw new Error("GITHUB_TOKEN is required for pull requests");
	}
	return parsedApiUrl;
}

async function readJsonResponse(response) {
	const contentLength = Number(response.headers.get("content-length") ?? "0");
	if (contentLength > MAX_RESPONSE_BYTES) {
		throw new Error("GitHub labels response is too large");
	}

	const body = await response.text();
	if (Buffer.byteLength(body) > MAX_RESPONSE_BYTES) {
		throw new Error("GitHub labels response is too large");
	}
	return JSON.parse(body);
}

/**
 * @param {{
 *   apiUrl: string;
 *   repository: string;
 *   pullRequestNumber: string;
 *   label: string;
 *   token: string;
 *   fetchImpl?: typeof fetch;
 * }} options
 * @returns {Promise<boolean>}
 */
export async function hasLivePullRequestLabel(options) {
	const {
		repository,
		pullRequestNumber,
		label,
		token,
		fetchImpl = fetch,
	} = options;
	const parsedApiUrl = validateInputs(options);
	const labelsUrl = new URL(
		`repos/${repository}/issues/${pullRequestNumber}/labels`,
		`${parsedApiUrl.href.replace(/\/$/, "")}/`,
	);

	for (let page = 1; page <= MAX_LABEL_PAGES; page++) {
		labelsUrl.search = new URLSearchParams({
			per_page: "100",
			page: String(page),
		}).toString();
		const response = await fetchImpl(labelsUrl, {
			headers: {
				Accept: "application/vnd.github+json",
				Authorization: `Bearer ${token}`,
				"X-GitHub-Api-Version": "2022-11-28",
			},
			redirect: "error",
			signal: AbortSignal.timeout(10_000),
		});

		if (!response.ok) {
			throw new Error(
				`GitHub labels request failed with HTTP ${response.status}`,
			);
		}

		const payload = await readJsonResponse(response);
		if (!Array.isArray(payload)) {
			throw new Error("GitHub labels response is not an array");
		}
		const labels = payload.map((item) => {
			if (
				typeof item !== "object" ||
				item === null ||
				!("name" in item) ||
				typeof item.name !== "string"
			) {
				throw new Error("GitHub labels response contains an invalid label");
			}
			return item.name;
		});
		if (labels.includes(label)) {
			return true;
		}
		if (payload.length < 100) {
			return false;
		}
	}

	throw new Error("GitHub labels response exceeded the pagination limit");
}

function writeResult(githubOutput, hasLabel) {
	fs.appendFileSync(githubOutput, `has_label=${String(hasLabel)}\n`);
}

async function main() {
	const githubOutput = process.env.GITHUB_OUTPUT;
	if (!githubOutput) {
		throw new Error("GITHUB_OUTPUT is required");
	}

	if (process.env.GITHUB_EVENT_NAME !== "pull_request") {
		writeResult(githubOutput, false);
		console.log("Non-PR run: live label check skipped");
		return;
	}

	const hasLabel = await hasLivePullRequestLabel({
		apiUrl: process.env.GITHUB_API_URL ?? "",
		repository: process.env.GITHUB_REPOSITORY ?? "",
		pullRequestNumber: process.env.PULL_REQUEST_NUMBER ?? "",
		label: process.env.LABEL ?? "",
		token: process.env.GITHUB_TOKEN ?? "",
	});
	writeResult(githubOutput, hasLabel);
	console.log(
		hasLabel
			? "Requested live pull request label found"
			: "Requested live pull request label not found",
	);
}

if (
	process.argv[1] &&
	pathToFileURL(process.argv[1]).href === import.meta.url
) {
	await main();
}
