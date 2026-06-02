import * as vscode from "vscode";
import { getConfig } from "./config";
import { TokenMetric } from "./types";

const BATCH_INTERVAL_MS = 30_000; // flush em batch a cada 30s
const MAX_QUEUE = 5_000; // proteção contra crescimento infinito offline

export interface SessionStats {
  inputTokens: number;
  outputTokens: number;
  metricsSent: number;
  pending: number;
  lastSyncOk: boolean | null; // null = ainda não tentou
  lastError?: string;
}

/**
 * Fila em memória + flush em batch a cada 30s, com requeue em falha.
 * Espelha a lógica do plugins/chrome-extension/background.js.
 */
export class MetricSender {
  private queue: TokenMetric[] = [];
  private timer: NodeJS.Timeout | undefined;
  private readonly onChange = new vscode.EventEmitter<SessionStats>();
  readonly onStatsChanged = this.onChange.event;

  private stats: SessionStats = {
    inputTokens: 0,
    outputTokens: 0,
    metricsSent: 0,
    pending: 0,
    lastSyncOk: null,
  };

  start(): void {
    if (this.timer) {
      return;
    }
    this.timer = setInterval(() => void this.flush(), BATCH_INTERVAL_MS);
  }

  dispose(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = undefined;
    }
    this.onChange.dispose();
  }

  getStats(): SessionStats {
    return { ...this.stats, pending: this.queue.length };
  }

  /** Enfileira uma métrica para envio em batch. */
  enqueue(metric: TokenMetric): void {
    this.queue.push(metric);
    if (this.queue.length > MAX_QUEUE) {
      // descarta as mais antigas para não estourar memória
      this.queue.splice(0, this.queue.length - MAX_QUEUE);
    }
    this.stats.inputTokens += metric.input_tokens;
    this.stats.outputTokens += metric.output_tokens;
    this.emit();
  }

  /**
   * Envia UMA métrica imediatamente via POST /v1/metrics.
   * Em falha, enfileira para retry no batch.
   */
  async sendNow(metric: TokenMetric): Promise<boolean> {
    const cfg = getConfig();
    try {
      const res = await fetch(`${cfg.serverUrl}/v1/metrics`, {
        method: "POST",
        headers: this.headers(cfg.apiKey),
        body: JSON.stringify(metric),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status} ${res.statusText}`);
      }
      this.stats.metricsSent += 1;
      this.stats.lastSyncOk = true;
      this.stats.lastError = undefined;
      this.emit();
      return true;
    } catch (err) {
      this.stats.lastSyncOk = false;
      this.stats.lastError = err instanceof Error ? err.message : String(err);
      // Requeue para tentar no próximo flush.
      this.queue.push(metric);
      this.stats.inputTokens += metric.input_tokens;
      this.stats.outputTokens += metric.output_tokens;
      this.emit();
      return false;
    }
  }

  /** Flush em batch via POST /v1/metrics/batch. Requeue em falha. */
  async flush(): Promise<boolean> {
    if (this.queue.length === 0) {
      return true;
    }
    const cfg = getConfig();
    if (!cfg.enabled) {
      return false;
    }
    const batch = [...this.queue];
    this.queue = [];
    this.emit();

    try {
      const res = await fetch(`${cfg.serverUrl}/v1/metrics/batch`, {
        method: "POST",
        headers: this.headers(cfg.apiKey),
        body: JSON.stringify(batch),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status} ${res.statusText}`);
      }
      this.stats.metricsSent += batch.length;
      this.stats.lastSyncOk = true;
      this.stats.lastError = undefined;
      this.emit();
      return true;
    } catch (err) {
      // Recoloca o batch na frente da fila (preserva ordem aproximada).
      this.queue = [...batch, ...this.queue];
      this.stats.lastSyncOk = false;
      this.stats.lastError = err instanceof Error ? err.message : String(err);
      this.emit();
      return false;
    }
  }

  /** Checa o /health do backend. */
  async health(): Promise<boolean> {
    const cfg = getConfig();
    try {
      const res = await fetch(`${cfg.serverUrl}/health`, { method: "GET" });
      return res.ok;
    } catch {
      return false;
    }
  }

  private headers(apiKey: string): Record<string, string> {
    return {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    };
  }

  private emit(): void {
    this.onChange.fire(this.getStats());
  }
}
