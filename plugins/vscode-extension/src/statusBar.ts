import * as vscode from "vscode";
import { SessionStats } from "./sender";

export class StatusBar {
  private readonly item: vscode.StatusBarItem;

  constructor() {
    this.item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100
    );
    this.item.command = "o11yia.showStatus";
    this.item.name = "O11yIA BR";
    this.update({
      inputTokens: 0,
      outputTokens: 0,
      metricsSent: 0,
      pending: 0,
      lastSyncOk: null,
    });
    this.item.show();
  }

  update(stats: SessionStats): void {
    const total = stats.inputTokens + stats.outputTokens;
    let icon = "$(cloud)"; // ainda não sincronizou
    if (stats.lastSyncOk === true) {
      icon = "$(cloud-upload)";
    } else if (stats.lastSyncOk === false) {
      icon = "$(warning)";
    }
    const pendingTxt = stats.pending > 0 ? ` ($(sync) ${stats.pending})` : "";
    this.item.text = `${icon} O11yIA ${formatTokens(total)} tok${pendingTxt}`;

    const lines = [
      "O11yIA BR — sessão atual",
      `Input tokens:  ${stats.inputTokens}`,
      `Output tokens: ${stats.outputTokens}`,
      `Total:         ${total}`,
      `Métricas enviadas: ${stats.metricsSent}`,
      `Na fila (pendentes): ${stats.pending}`,
      `Último sync: ${
        stats.lastSyncOk === null
          ? "—"
          : stats.lastSyncOk
            ? "OK"
            : `FALHA${stats.lastError ? " — " + stats.lastError : ""}`
      }`,
    ];
    this.item.tooltip = lines.join("\n");

    this.item.backgroundColor =
      stats.lastSyncOk === false
        ? new vscode.ThemeColor("statusBarItem.warningBackground")
        : undefined;
  }

  dispose(): void {
    this.item.dispose();
  }
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) {
    return (n / 1_000_000).toFixed(1) + "M";
  }
  if (n >= 1_000) {
    return (n / 1_000).toFixed(1) + "k";
  }
  return String(n);
}
