import assert from "node:assert/strict";
import test from "node:test";
import { hasLivePullRequestLabel } from "./check-label.mjs";

const options = {
	apiUrl: "https://api.github.com",
	repository: "unique-ag/monorepo",
	pullRequestNumber: "123",
	label: "security-exception",
	token: "test-token",
};

test("finds the requested live label", async () => {
	const fetchImpl = async (url, request) => {
		assert.equal(
			url.href,
			"https://api.github.com/repos/unique-ag/monorepo/issues/123/labels?per_page=100&page=1",
		);
		assert.equal(request.headers.Authorization, "Bearer test-token");
		assert.equal(request.redirect, "error");
		return new Response(
			JSON.stringify([{ name: "other" }, { name: "security-exception" }]),
		);
	};

	assert.equal(await hasLivePullRequestLabel({ ...options, fetchImpl }), true);
});

test("returns false when the requested live label is absent", async () => {
	const fetchImpl = async () =>
		new Response(JSON.stringify([{ name: "other" }]));

	assert.equal(await hasLivePullRequestLabel({ ...options, fetchImpl }), false);
});

test("checks additional label pages", async () => {
	const firstPage = Array.from({ length: 100 }, (_, index) => ({
		name: `label-${index}`,
	}));
	const fetchImpl = async (url) =>
		new Response(
			JSON.stringify(
				url.searchParams.get("page") === "1"
					? firstPage
					: [{ name: "security-exception" }],
			),
		);

	assert.equal(await hasLivePullRequestLabel({ ...options, fetchImpl }), true);
});

test("fails closed when GitHub rejects the labels request", async () => {
	const fetchImpl = async () => new Response("rate limited", { status: 403 });

	await assert.rejects(
		hasLivePullRequestLabel({ ...options, fetchImpl }),
		/HTTP 403/,
	);
});

test("fails closed when GitHub returns a malformed label", async () => {
	const fetchImpl = async () => new Response(JSON.stringify([{}]));

	await assert.rejects(
		hasLivePullRequestLabel({ ...options, fetchImpl }),
		/invalid label/,
	);
});

test("rejects non-HTTPS API URLs", async () => {
	await assert.rejects(
		hasLivePullRequestLabel({
			...options,
			apiUrl: "http://api.github.com",
			fetchImpl: async () => new Response("[]"),
		}),
		/must use HTTPS/,
	);
});
