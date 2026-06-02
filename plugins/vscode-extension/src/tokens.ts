import * as vscode from "vscode";

export interface TokenCount {
  tokens: number;
  /** true = contagem nativa do modelo (model.countTokens); false = heurística. */
  measured: boolean;
}

/**
 * Conta tokens de um texto. Tenta a contagem NATIVA da Language Model API
 * (model.countTokens) e, em falha, cai para heurística (~4 chars/token).
 *
 * Medido vs estimado:
 *  - measured=true  -> valor exato reportado pelo tokenizer do modelo.
 *  - measured=false -> aproximação Math.ceil(chars / 4).
 */
export async function countTokens(
  text: string,
  model?: vscode.LanguageModelChat,
  token?: vscode.CancellationToken
): Promise<TokenCount> {
  if (model && typeof model.countTokens === "function") {
    try {
      const tokens = await model.countTokens(text, token);
      return { tokens, measured: true };
    } catch {
      // cai para heurística
    }
  }
  return { tokens: estimateTokens(text), measured: false };
}

/** Heurística simples: ~4 caracteres por token. */
export function estimateTokens(text: string): number {
  if (!text) {
    return 0;
  }
  return Math.ceil(text.length / 4);
}
