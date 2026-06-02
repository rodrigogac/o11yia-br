package br.gov.o11yia.copilot

import br.gov.o11yia.copilot.service.MetricsCollectorService
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.project.Project
import com.intellij.openapi.startup.ProjectActivity

class CopilotMetricsStartup : ProjectActivity {

    private val logger = Logger.getInstance(CopilotMetricsStartup::class.java)

    override suspend fun execute(project: Project) {
        logger.info("O11yIA Copilot Metrics initializing for project: ${project.name}")
        
        val service = MetricsCollectorService.getInstance()
        service.start()
        
        // Register shutdown hook
        project.messageBus.connect().subscribe(
            com.intellij.openapi.project.ProjectManager.TOPIC,
            object : com.intellij.openapi.project.ProjectManagerListener {
                override fun projectClosing(project: Project) {
                    service.stop()
                }
            }
        )
    }
}
