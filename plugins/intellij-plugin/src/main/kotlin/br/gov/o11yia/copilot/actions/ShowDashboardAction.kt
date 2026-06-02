package br.gov.o11yia.copilot.actions

import br.gov.o11yia.copilot.settings.CopilotMetricsSettings
import com.intellij.ide.BrowserUtil
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent

class ShowDashboardAction : AnAction() {

    override fun actionPerformed(e: AnActionEvent) {
        val settings = CopilotMetricsSettings.getInstance()
        // Dashboard Streamlit roda na porta 8501
        val dashboardUrl = settings.serverUrl
            .replace(":8080", ":8501")
            .replace("/v1", "")
        
        BrowserUtil.browse(dashboardUrl)
    }

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabledAndVisible = true
    }
}
