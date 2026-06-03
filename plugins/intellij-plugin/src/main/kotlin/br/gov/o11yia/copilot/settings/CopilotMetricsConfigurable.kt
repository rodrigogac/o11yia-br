package br.gov.o11yia.copilot.settings

import com.intellij.openapi.options.Configurable
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.components.JBCheckBox
import com.intellij.ui.components.JBPasswordField
import com.intellij.ui.components.JBTextField
import com.intellij.ui.dsl.builder.*
import javax.swing.JComponent

class CopilotMetricsConfigurable : Configurable {

    private val settings = CopilotMetricsSettings.getInstance()
    private var panel: DialogPanel? = null

    private val serverUrlField = JBTextField()
    private val userIdField = JBTextField()
    private val apiKeyField = JBPasswordField()
    private val teamField = JBTextField()
    private val projectField = JBTextField()
    private val enabledCheckbox = JBCheckBox("Ativar coleta de métricas")
    private val statusBarCheckbox = JBCheckBox("Mostrar widget na barra de status")
    private val syncIntervalField = JBTextField()

    override fun getDisplayName(): String = "O11yIA Copilot Metrics"

    override fun createComponent(): JComponent {
        panel = panel {
            group("Servidor Central") {
                row("URL do Servidor:") {
                    cell(serverUrlField)
                        .columns(COLUMNS_LARGE)
                        .comment("Endereço do servidor O11yIA BR (ex: http://servidor:8080)")
                }
                row("ID do Usuário:") {
                    cell(userIdField)
                        .columns(COLUMNS_LARGE)
                        .comment("Seu email corporativo para identificação")
                }
                row("API Key:") {
                    cell(apiKeyField)
                        .columns(COLUMNS_LARGE)
                        .comment("Chave de API enviada no header X-API-Key (obrigatória)")
                }
                row("Time:") {
                    cell(teamField)
                        .columns(COLUMNS_LARGE)
                        .comment("Time/squad para atribuição das métricas (opcional)")
                }
                row("Projeto:") {
                    cell(projectField)
                        .columns(COLUMNS_LARGE)
                        .comment("Projeto para atribuição das métricas (opcional)")
                }
            }

            group("Monitoramento") {
                row {
                    cell(enabledCheckbox)
                }
                row {
                    cell(statusBarCheckbox)
                }
                row("Intervalo de Sincronização:") {
                    cell(syncIntervalField)
                        .columns(COLUMNS_SHORT)
                        .comment("Segundos entre cada envio de métricas")
                }
            }

            group("Teste") {
                row {
                    button("Testar Conexão") {
                        testConnection()
                    }
                }
            }
        }

        reset()
        return panel!!
    }

    override fun isModified(): Boolean {
        return serverUrlField.text != settings.serverUrl ||
                userIdField.text != settings.userId ||
                String(apiKeyField.password) != settings.apiKey ||
                teamField.text != settings.team ||
                projectField.text != settings.project ||
                enabledCheckbox.isSelected != settings.enabled ||
                statusBarCheckbox.isSelected != settings.showStatusBarWidget ||
                syncIntervalField.text.toIntOrNull() != settings.syncIntervalSeconds
    }

    override fun apply() {
        settings.serverUrl = serverUrlField.text.trimEnd('/')
        settings.userId = userIdField.text
        settings.apiKey = String(apiKeyField.password)
        settings.team = teamField.text
        settings.project = projectField.text
        settings.enabled = enabledCheckbox.isSelected
        settings.showStatusBarWidget = statusBarCheckbox.isSelected
        settings.syncIntervalSeconds = syncIntervalField.text.toIntOrNull() ?: 30
    }

    override fun reset() {
        serverUrlField.text = settings.serverUrl
        userIdField.text = settings.userId
        apiKeyField.text = settings.apiKey
        teamField.text = settings.team
        projectField.text = settings.project
        enabledCheckbox.isSelected = settings.enabled
        statusBarCheckbox.isSelected = settings.showStatusBarWidget
        syncIntervalField.text = settings.syncIntervalSeconds.toString()
    }

    private fun testConnection() {
        val url = serverUrlField.text.trimEnd('/')
        val apiKey = String(apiKeyField.password)
        Thread {
            try {
                val connection = java.net.URL("$url/health").openConnection() as java.net.HttpURLConnection
                connection.requestMethod = "GET"
                connection.setRequestProperty("X-API-Key", apiKey)
                connection.connectTimeout = 5000
                connection.readTimeout = 5000

                val responseCode = connection.responseCode
                if (responseCode == 200) {
                    showInfo("Conexão OK! Servidor respondendo.")
                } else if (responseCode == 401) {
                    showError("Não autorizado (401). Verifique a API Key.")
                } else {
                    showError("Servidor respondeu com código: $responseCode")
                }
            } catch (e: Exception) {
                showError("Erro de conexão: ${e.message}")
            }
        }.start()
    }

    private fun showInfo(message: String) {
        com.intellij.openapi.ui.Messages.showInfoMessage(message, "Teste de Conexão")
    }

    private fun showError(message: String) {
        com.intellij.openapi.ui.Messages.showErrorDialog(message, "Erro de Conexão")
    }
}
