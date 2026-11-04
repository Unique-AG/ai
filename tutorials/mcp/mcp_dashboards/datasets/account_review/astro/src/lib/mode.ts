import fs from "node:fs";
import path from "node:path";
import { z } from "zod";

import { clientRowSchema } from "./schema.ts";

export type DashboardMode = "live" | "preview" | "live-local";

export interface McpLiveConfig {
  baseUrl: string;
}

/** Shape of src/data/mock.json: one typed clients array, same as list_clients returns. */
export const mockDataSchema = z.object({
  clients: z.array(clientRowSchema),
});

export type MockData = z.infer<typeof mockDataSchema>;

export function getMode(): DashboardMode {
  return (process.env.DASHBOARD_MODE ?? "live") as DashboardMode;
}

export function loadMockData(mode: DashboardMode): MockData | Record<string, never> {
  if (mode !== "preview") return {};

  const mockPath = path.resolve(process.cwd(), "src/data/mock.json");
  if (!fs.existsSync(mockPath)) return { clients: [] };

  const raw = JSON.parse(fs.readFileSync(mockPath, "utf-8")) as unknown;
  return mockDataSchema.parse(raw);
}

export function getMcpLiveConfig(mode: DashboardMode, mcpLocalUrl: string): McpLiveConfig | null {
  return mode === "live-local" ? { baseUrl: mcpLocalUrl } : null;
}

