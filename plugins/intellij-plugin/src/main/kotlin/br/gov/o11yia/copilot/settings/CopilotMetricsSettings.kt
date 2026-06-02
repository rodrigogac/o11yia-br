package br.gov.o11yia.copilot.settings

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage

@State(
    name = "CopilotMetricsSettings",
    storages = [Storage("o11yia-copilot-metrics.xml")]
)
class CopilotMetricsSettings : PersistentStateComponent<CopilotMetricsSettings.State> {

    data class State(
        var serverUrl: String = "http://localhost:8080",
        var userId: String = "user@empresa.gov.br",
        var enabled: Boolean = true,
        var syncIntervalSeconds: Int = 30,
        var showStatusBarWidget: Boolean = true
    )

    private var myState = State()

    override fun getState(): State = myState

    override fun loadState(state: State) {
        myState = state
    }

    var serverUrl: String
        get() = myState.serverUrl
        set(value) { myState.serverUrl = value }

    var userId: String
        get() = myState.userId
        set(value) { myState.userId = value }

    var enabled: Boolean
        get() = myState.enabled
        set(value) { myState.enabled = value }

    var syncIntervalSeconds: Int
        get() = myState.syncIntervalSeconds
        set(value) { myState.syncIntervalSeconds = value }

    var showStatusBarWidget: Boolean
        get() = myState.showStatusBarWidget
        set(value) { myState.showStatusBarWidget = value }

    companion object {
        fun getInstance(): CopilotMetricsSettings =
            ApplicationManager.getApplication().getService(CopilotMetricsSettings::class.java)
    }
}
