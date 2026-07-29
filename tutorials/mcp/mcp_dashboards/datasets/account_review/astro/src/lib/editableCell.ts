export interface EditableOption {
  value: string;
  label: string;
  cssClass: string;
  tool?: "update_client";
}

export interface EditableColumnConfig {
  field: string;
  updateField: "risk_level";
  tdDataAttr: string;
  iconClass?: string;
  statClass: string;
  menuLabel: string;
  options: EditableOption[];
}

/** Lists refreshed after any portfolio-table inline edit or reset. */
export const portfolioListRefresh = "clientsLive,attentionLive,clientPages,portfolioKpis";

export const riskColumn: EditableColumnConfig = {
  field: "compliance.risk_level",
  updateField: "risk_level",
  tdDataAttr: "data-risk",
  iconClass: "risk-indicator",
  statClass: "risk",
  menuLabel: "Set risk",
  options: [
    { value: "High", label: "High", cssClass: "mi-danger" },
    { value: "Medium", label: "Medium", cssClass: "mi-warn" },
    { value: "Low", label: "Low", cssClass: "mi-muted" },
  ],
};
