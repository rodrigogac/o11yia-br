package br.gov.o11yia.copilot.ui

import br.gov.o11yia.copilot.service.MetricsCollectorService
import br.gov.o11yia.copilot.settings.CopilotMetricsSettings
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.Disposer
import com.intellij.openapi.wm.StatusBar
import com.intellij.openapi.wm.StatusBarWidget
import com.intellij.openapi.wm.StatusBarWidgetFactory
import com.intellij.util.Consumer
import kotlinx.coroutines.*
import java.awt.Component
import java.awt.event.MouseEvent
import javax.swing.Icon

class CopilotMetricsWidgetFactory : StatusBarWidgetFactory {

    override fun getId(): String = "CopilotMetricsWidget"
    
    override fun getDisplayName(): String = "O11yIA Copilot Metrics"
    
    override fun isAvailable(project: Project): Boolean = 
        CopilotMetricsSettings.getInstance().showStatusBarWidget

    override fun createWidget(project: Project): StatusBarWidget = 
        CopilotMetricsWidget(project)

    override fun disposeWidget(widget: StatusBarWidget) {
        Disposer.dispose(widget)
    }

    override fun canBeEnabledOn(statusBar: StatusBar): Boolean = true
}

class CopilotMetricsWidget(private val project: Project) : StatusBarWidget, StatusBarWidget.TextPresentation {

    private val service = MetricsCollectorService.getInstance()
    private val settings = CopilotMetricsSettings.getInstance()
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private var statusBar: StatusBar? = null
    private var currentText = "⚡ --"

    init {
        // Atualiza periodicamente
        scope.launch {
            while (isActive) {
                updateWidget()
                delay(10000) // 10 segundos
            }
        }
    }

    override fun ID(): String = "CopilotMetricsWidget"

    override fun install(statusBar: StatusBar) {
        this.statusBar = statusBar
    }

    override fun dispose() {
        scope.cancel()
        statusBar = null
    }

    override fun getPresentation(): StatusBarWidget.WidgetPresentation = this

    override fun getText(): String = currentText

    override fun getAlignment(): Float = Component.CENTER_ALIGNMENT

    override fun getTooltipText(): String {
        val credits = service.totalCreditsUsed
        val requests = service.totalRequests
        return """
            O11yIA Copilot Metrics
            ─────────────────────
            Créditos: ${String.format("%.2f", credits)}
            Requests: $requests
            Usuário: ${settings.userId}
            Servidor: ${settings.serverUrl}
        """.trimIndent()
    }

    override fun getClickConsumer(): Consumer<MouseEvent>? = Consumer {
        // Abre dashboard ao clicar
        val url = "${settings.serverUrl.replace("http://", "").replace(":8080", ":8501")}"
        // Poderia abrir browser aqui
    }

    private suspend fun updateWidget() {
        val credits = service.totalCreditsUsed
        val icon = when {
            credits > 5000 -> "🔴"
            credits > 3000 -> "🟡"
            else -> "🟢"
        }
        currentText = "$icon ${String.format("%.1f", credits)} cr"
        
        withContext(Dispatchers.Main) {
            statusBar?.updateWidget(ID())
        }
    }
}
