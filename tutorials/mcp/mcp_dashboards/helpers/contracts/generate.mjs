// Compiles a dataset's TypeSpec contract to OpenAPI 3.1, then generates the
// Pydantic and Zod/TypeScript artifacts both runtimes import.
//
// Output must be byte-stable: these files are committed and reviewed, and CI
// asserts that running this script produces no diff. That is why
// datamodel-codegen is invoked with --disable-timestamp.
//
// Usage: node helpers/contracts/generate.mjs [dataset]   (all datasets if omitted)
import { existsSync, mkdtempSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const contractsRoot = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(contractsRoot, "..", "..");
const datasetsRoot = join(projectRoot, "datasets");

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd ?? contractsRoot,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function prependHeader(filePath, header) {
  if (!existsSync(filePath)) return;
  const text = readFileSync(filePath, "utf8");
  if (text.startsWith(header.trimStart())) return;
  writeFileSync(filePath, `${header}${text}`);
}

function bannerLines(dataset, comment, sourcePath) {
  return [
    `${comment} AUTO-GENERATED FILE - DO NOT EDIT BY HAND.`,
    `${comment} Source: ${sourcePath}`,
    `${comment} Regenerate with: npm run generate ${dataset} (from tutorials/mcp/mcp_dashboards).`,
    "",
    "",
  ].join("\n");
}

function markOpenApiGenerated(dataset, filePath) {
  const doc = JSON.parse(readFileSync(filePath, "utf8"));
  doc.info = {
    ...doc.info,
    "x-generated-by": `mcp_dashboards; do not edit by hand; regenerate with npm run generate ${dataset}`,
    "x-source": `datasets/${dataset}/contract/main.tsp`,
  };
  writeFileSync(filePath, `${JSON.stringify(doc, null, 2)}\n`);
}

function generate(dataset) {
  const contractRoot = join(datasetsRoot, dataset, "contract");
  const openapiPath = join(contractRoot, "openapi.json");
  const pythonOutput = join(datasetsRoot, dataset, "fastmcp", "generated", "models.py");
  const typescriptOutput = join(datasetsRoot, dataset, "astro", "src", "lib", "generated");

  if (!existsSync(join(contractRoot, "main.tsp"))) {
    console.error(`Dataset ${dataset} has no contract/main.tsp`);
    process.exit(1);
  }

  console.log(`\n=== ${dataset} ===`);
  const before = existsSync(openapiPath) ? statSync(openapiPath).mtimeMs : 0;
  run("npx", ["tsp", "compile", contractRoot]);

  // tsp exits 0 even when an emitter wrote nothing, which would leave the
  // downstream generators reading a stale contract.
  if (!existsSync(openapiPath)) {
    console.error(`tsp compile produced no ${openapiPath} — check the emitter in tspconfig.yaml`);
    process.exit(1);
  }
  if (statSync(openapiPath).mtimeMs === before) {
    console.error(`tsp compile did not rewrite ${openapiPath} — the emitter appears to be disabled`);
    process.exit(1);
  }
  markOpenApiGenerated(dataset, openapiPath);

  const tmp = mkdtempSync(join(tmpdir(), "mcp-dashboard-openapi-ts-"));
  const configPath = join(tmp, "openapi-ts.config.ts");
  writeFileSync(
    configPath,
    `export default {
  input: ${JSON.stringify(openapiPath)},
  output: ${JSON.stringify(typescriptOutput)},
  plugins: [
    "@hey-api/typescript",
    {
      name: "zod",
      compatibilityVersion: 3,
      definitions: true,
      requests: true,
      responses: true,
    },
  ],
};
`,
  );

  run("npx", ["openapi-ts", "-f", configPath]);
  run(
    "uv",
    [
      "run",
      "datamodel-codegen",
      "--input",
      openapiPath,
      "--input-file-type",
      "openapi",
      "--output",
      pythonOutput,
      "--output-model-type",
      "pydantic_v2.BaseModel",
      "--target-python-version",
      "3.12",
      "--use-standard-collections",
      "--use-union-operator",
      "--use-annotated",
      // Without this, every run rewrites a `# timestamp:` line and the
      // committed artifact churns on each regeneration.
      "--disable-timestamp",
    ],
    { cwd: join(projectRoot, "helpers", "python") },
  );

  prependHeader(pythonOutput, bannerLines(dataset, "#", "../contract/main.tsp"));
  for (const name of ["zod.gen.ts", "types.gen.ts", "index.ts"]) {
    prependHeader(join(typescriptOutput, name), bannerLines(dataset, "//", "../../../../contract/main.tsp"));
  }
}

const requested = process.argv[2];
const datasets = requested
  ? [requested]
  : readdirSync(datasetsRoot).filter((name) => existsSync(join(datasetsRoot, name, "contract", "main.tsp")));

if (datasets.length === 0) {
  console.error(`No dataset contracts found under ${datasetsRoot}`);
  process.exit(1);
}

for (const dataset of datasets) {
  generate(dataset);
}
