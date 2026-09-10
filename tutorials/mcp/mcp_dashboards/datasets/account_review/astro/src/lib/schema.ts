import { z } from "zod";

import { zClient as clientSchema, zCountByResult as countByResultSchema } from "./generated/zod.gen.ts";

export const clientRowSchema = clientSchema;
export type ClientRow = z.infer<typeof clientRowSchema>;

export const kpiRowSchema = z.object({
  bucket: z.string(),
  label: z.string(),
  count: z.number(),
});
export type KpiRow = z.infer<typeof kpiRowSchema>;

export const countBySchema = countByResultSchema.extend({
  rows: z.array(kpiRowSchema).optional(),
});
export type CountByResult = z.infer<typeof countBySchema>;

export const figureSchema = z.object({
  label: z.string().nullable(),
  value: z.string().nullable(),
  pct: z.number().nullable(),
  status: z.string().nullable(),
});
export type Figure = z.infer<typeof figureSchema>;

export const FIGURE_GROUP_SIZE = 3;
const FIGURE_PREFIXES = ["fig", "perf", "mand", "hold"] as const;
type FigurePrefix = (typeof FIGURE_PREFIXES)[number];
type FigureSlot = 1 | 2 | 3;
const FIGURE_GROUP_BY_PREFIX = {
  fig: "documents",
  perf: "performance",
  mand: "mandate",
  hold: "holdings",
} as const;

export function readFigure<Prefix extends FigurePrefix>(row: ClientRow, prefix: Prefix, slot: FigureSlot): Figure {
  const group = row.figures[FIGURE_GROUP_BY_PREFIX[prefix]];
  return figureSchema.parse(group[slot - 1] ?? {});
}
