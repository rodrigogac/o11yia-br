import * as vscode from "vscode";

export interface O11yiaConfig {
  enabled: boolean;
  serverUrl: string;
  userId: string;
  apiKey: string;
  team: string;
}

const SECTION = "o11yia";

export function getConfig(): O11yiaConfig {
  const c = vscode.workspace.getConfiguration(SECTION);
  // Remove barra(s) final(is) para evitar URLs como ".../v1/metrics//".
  const rawUrl = c.get<string>("serverUrl", "http://localhost:8080");
  const serverUrl = rawUrl.replace(/\/+$/, "");
  return {
    enabled: c.get<boolean>("enabled", true),
    serverUrl,
    userId: c.get<string>("userId", "").trim(),
    apiKey: c.get<string>("apiKey", "").trim(),
    team: c.get<string>("team", "").trim(),
  };
}

/** Resolve um userId utilizável: configurado, ou fallback para o login da máquina. */
export function resolveUserId(cfg: O11yiaConfig): string {
  if (cfg.userId) {
    return cfg.userId;
  }
  return process.env.USER || process.env.USERNAME || "unknown@vscode";
}
