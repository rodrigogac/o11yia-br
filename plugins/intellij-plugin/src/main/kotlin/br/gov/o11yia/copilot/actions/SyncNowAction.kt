package br.gov.o11yia.copilot.actions

import br.gov.o11yia.copilot.service.MetricsCollectorService
import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import kotlinx.coroutines.runBlocking

class SyncNowAction : AnAction() {

    override fun actionPerformed(e: AnActionEvent) {
        val service = MetricsCollectorService.getInstance()
        
        val success = runBlocking {
            service.flushMetrics()
        }
        
        val notification = NotificationGroupManager.getInstance()
            .getNotificationGroup("O11yIA Copilot Metrics")
            .createNotification(
                if (success) "Métricas sincronizadas!" else "Erro ao sincronizar métricas",
                if (success) NotificationType.INFORMATION else NotificationType.WARNING
            )
        
        notification.notify(e.project)
    }

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabledAndVisible = true
    }
}
