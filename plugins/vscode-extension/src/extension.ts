import * as vscode from "vscode";
import { getConfig, resolveUserId } from "./config";
import { MetricSender } from "./sender";
import { StatusBar } from "./statusBar";
import { countTokens } from "./tokens";
import { TokenMetric } from "./types";

let sender: MetricSender;
let statusBar: StatusBar;
let sessionId: string;

export function activate(context: vscode.ExtensionContext): void {
  sessionId = `vscode-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

  sender = new MetricSender();
  statusBar = new StatusBar();
  sender.start();

  context.subscriptions.push(
    sender,
    statusBar,
    sender.onStatsChanged((stats) => statusBar.update(stats))
  );

  // ---- Chat Participant: @o11yia ----------------------------------------
  // O usuário conversa com "@o11yia". Encaminhamos a pergunta para um modelo
  // do Copilot (Language Model API) e contabilizamos os tokens de entrada e
  // saída. Isso NÃO usa a API oficial do GitHub Copilot — usa apenas a
  // vscode.lm pública, disponível para qualquer extensão.
  try {
    const participant = vscode.chat.createChatParticipant(
      "o11yia.tracker",
      handleChatRequest
    );
    participant.iconPath = new vscode.ThemeIcon("graph");
    context.subscriptions.push(participant);
  } catch (err) {
    // Em versões do VSCode sem a Chat API, seguimos só com comandos/test metric.
    console.warn("O11yIA: Chat Participant indisponível:", err);
  }

  // ---- Comandos ----------------------------------------------------------
  context.subscriptions.push(
    vscode.commands.registerCommand("o11yia.syncNow", async () => {
      const ok = await sender.flush();
      vscode.window.showInformationMessage(
        ok
          ? "O11yIA: fila sincronizada."
          : `O11yIA: falha ao sincronizar — ${sender.getStats().lastError ?? "erro desconhecido"}`
      );
    }),

    vscode.commands.registerCommand("o11yia.sendTestMetric", async () => {
      const cfg = getConfig();
      const metric: TokenMetric = {
        user_id: resolveUserId(cfg),
        source: "vscode",
        model: "test-model",
        input_tokens: 42,
        output_tokens: 108,
        reasoning_tokens: 0,
        team: cfg.team || undefined,
        session_id: sessionId,
        context: "chat",
        timestamp: new Date().toISOString(),
      };
      const healthy = await sender.health();
      const ok = await sender.sendNow(metric);
      vscode.window.showInformationMessage(
        ok
          ? `O11yIA: métrica de teste enviada para ${cfg.serverUrl}/v1/metrics (health=${healthy ? "ok" : "?"}).`
          : `O11yIA: falha ao enviar métrica de teste (enfileirada para retry) — ${sender.getStats().lastError ?? "erro"}.`
      );
    }),

    vscode.commands.registerCommand("o11yia.showStatus", async () => {
      const cfg = getConfig();
      const s = sender.getStats();
      const healthy = await sender.health();
      const msg = [
        `Servidor: ${cfg.serverUrl} (health: ${healthy ? "OK" : "indisponível"})`,
        `Usuário: ${resolveUserId(cfg)}  Time: ${cfg.team || "—"}`,
        `Habilitado: ${cfg.enabled ? "sim" : "não"}  API key: ${cfg.apiKey ? "definida" : "VAZIA"}`,
        `Sessão: in=${s.inputTokens} out=${s.outputTokens} tokens`,
        `Enviadas: ${s.metricsSent}  Pendentes: ${s.pending}`,
        `Último sync: ${s.lastSyncOk === null ? "—" : s.lastSyncOk ? "OK" : "FALHA"}`,
      ].join("\n");
      vscode.window.showInformationMessage(msg, { modal: true });
    })
  );
}

async function handleChatRequest(
  request: vscode.ChatRequest,
  _ctx: vscode.ChatContext,
  stream: vscode.ChatResponseStream,
  token: vscode.CancellationToken
): Promise<void> {
  const cfg = getConfig();

  // Seleciona um modelo de chat disponível (Copilot, via API pública).
  let model = request.model;
  if (!model) {
    const models = await vscode.lm.selectChatModels({ vendor: "copilot" });
    model = models[0];
  }
  if (!model) {
    stream.markdown(
      "Nenhum modelo de linguagem disponível. Instale/ative o GitHub Copilot."
    );
    return;
  }

  // Conta tokens de ENTRADA (prompt do usuário). Nativo quando possível.
  const input = await countTokens(request.prompt, model, token);

  const messages = [vscode.LanguageModelChatMessage.User(request.prompt)];

  let answer = "";
  try {
    const response = await model.sendRequest(messages, {}, token);
    for await (const fragment of response.text) {
      answer += fragment;
      stream.markdown(fragment);
    }
  } catch (err) {
    if (err instanceof vscode.LanguageModelError) {
      stream.markdown(`\n\nErro do modelo: ${err.message}`);
    } else {
      throw err;
    }
  }

  // Conta tokens de SAÍDA (resposta do modelo).
  const output = await countTokens(answer, model, token);

  if (cfg.enabled) {
    const metric: TokenMetric = {
      user_id: resolveUserId(cfg),
      source: "vscode",
      model: model.id || model.family || "copilot",
      input_tokens: input.tokens,
      output_tokens: output.tokens,
      team: cfg.team || undefined,
      session_id: sessionId,
      context: "chat",
      timestamp: new Date().toISOString(),
    };
    sender.enqueue(metric);
  }

  // Transparência: mostra ao dev o que foi medido vs estimado.
  const tag = (m: boolean) => (m ? "medido" : "estimado");
  stream.markdown(
    `\n\n---\n*O11yIA: in=${input.tokens} (${tag(input.measured)}), ` +
      `out=${output.tokens} (${tag(output.measured)}) tokens — enfileirado.*`
  );
}

export function deactivate(): Thenable<void> | undefined {
  // Tenta um último flush ao desativar.
  return sender?.flush().then(() => undefined);
}
