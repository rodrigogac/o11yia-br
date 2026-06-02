// Contrato do payload — IGUAL para todos os clientes O11yIA (chrome, intellij, vscode).
export interface TokenMetric {
  user_id: string;
  source: "vscode";
  model: string;
  input_tokens: number;
  output_tokens: number;
  team?: string;
  project?: string;
  reasoning_tokens?: number;
  session_id?: string;
  /** chat | completion | inline */
  context?: "chat" | "completion" | "inline";
  /** ISO-8601 */
  timestamp?: string;
}
