import { type XmcpConfig } from "xmcp";

const config: XmcpConfig = {
  http: true,
  paths: {
    tools: "./src/tools",
    prompts: "./src/prompts",
    resources: "./src/resources",
  },
  template: {
    name: "Companies House MCP Server",
    description:
      "An MCP server for the UK Companies House API. \n\nSearch companies, officers, and retrieve company profiles, filing history, PSC data, and more.",
  },
};

export default config;
