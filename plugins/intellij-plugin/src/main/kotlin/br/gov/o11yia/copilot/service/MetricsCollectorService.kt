package br.gov.o11yia.copilot.service

import br.gov.o11yia.copilot.settings.CopilotMetricsSettings
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.diagnostic.Logger
import kotlinx.coroutines.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.time.Instant
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.TimeUnit

@Service(Service.Level.APP)
class MetricsCollectorService {

    private val logger = Logger.getInstance(MetricsCollectorService::class.java)
    private val settings = CopilotMetricsSettings.getInstance()
    private val gson = Gson()
    private val metricsQueue = ConcurrentLinkedQueue<TokenMetric>()
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private var syncJob: Job? = null
    private var logWatcherJob: Job? = null
    
    // Estatísticas locais
    var totalCreditsUsed: Double = 0.0
        private set
    var totalRequests: Int = 0
        private set

    data class TokenMetric(
        @SerializedName("user_id") val userId: String,
        val source: String = "intellij",
        val model: String,
        @SerializedName("input_tokens") val inputTokens: Int,
        @SerializedName("output_tokens") val outputTokens: Int,
        @SerializedName("team") val team: String? = null,
        @SerializedName("project") val project: String? = null,
        @SerializedName("reasoning_tokens") val reasoningTokens: Int? = null,
        val timestamp: String = Instant.now().toString(),
        @SerializedName("session_id") val sessionId: String? = null,
        val context: String? = null
    )

    fun start() {
        if (!settings.enabled) {
            logger.info("O11yIA Copilot Metrics disabled")
            return
        }

        logger.info("Starting O11yIA Copilot Metrics service")
        
        // Job de sincronização periódica
        syncJob = scope.launch {
            while (isActive) {
                delay(settings.syncIntervalSeconds * 1000L)
                flushMetrics()
            }
        }

        // Job de monitoramento de logs do Copilot
        logWatcherJob = scope.launch {
            watchCopilotLogs()
        }
    }

    fun stop() {
        logger.info("Stopping O11yIA Copilot Metrics service")
        syncJob?.cancel()
        logWatcherJob?.cancel()
        scope.cancel()
    }

    fun addMetric(metric: TokenMetric) {
        metricsQueue.offer(metric)
        totalRequests++
        
        // Calcular créditos (estimativa)
        val credits = calculateCredits(metric.model, metric.inputTokens, metric.outputTokens)
        totalCreditsUsed += credits
    }

    private fun calculateCredits(model: String, inputTokens: Int, outputTokens: Int): Double {
        val costs = when (model.lowercase()) {
            "gpt-4o" -> Pair(0.00025, 0.001)
            "gpt-4o-mini" -> Pair(0.000015, 0.00006)
            "claude-sonnet-4" -> Pair(0.0003, 0.0015)
            else -> Pair(0.0002, 0.0008)
        }
        return (inputTokens * costs.first) + (outputTokens * costs.second)
    }

    suspend fun flushMetrics(): Boolean {
        if (metricsQueue.isEmpty()) return true

        val metricsToSend = mutableListOf<TokenMetric>()
        while (metricsQueue.isNotEmpty()) {
            metricsQueue.poll()?.let { metricsToSend.add(it) }
        }

        if (metricsToSend.isEmpty()) return true

        return try {
            val json = gson.toJson(metricsToSend)
            val body = json.toRequestBody("application/json".toMediaType())
            
            val request = Request.Builder()
                .url("${settings.serverUrl}/v1/metrics/batch")
                .addHeader("X-API-Key", settings.apiKey)
                .post(body)
                .build()

            val response = httpClient.newCall(request).execute()

            if (response.isSuccessful) {
                logger.info("Sent ${metricsToSend.size} metrics successfully")
                true
            } else {
                // Requeue on failure
                metricsToSend.forEach { metricsQueue.offer(it) }
                if (response.code == 401) {
                    logger.error("Authentication failed (401) sending metrics: invalid or missing X-API-Key. " +
                            "Configure a API Key em Tools > O11yIA Copilot Metrics. Métricas mantidas na fila.")
                } else {
                    logger.warn("Failed to send metrics: ${response.code}")
                }
                false
            }
        } catch (e: Exception) {
            // Requeue on error
            metricsToSend.forEach { metricsQueue.offer(it) }
            logger.warn("Error sending metrics: ${e.message}")
            false
        }
    }

    private suspend fun watchCopilotLogs() {
        // Diretório de logs do Copilot
        val copilotLogDir = File(System.getProperty("user.home"), ".copilot/logs")
        if (!copilotLogDir.exists()) {
            logger.info("Copilot log directory not found, using fallback monitoring")
            return
        }

        val logFile = copilotLogDir.listFiles()
            ?.filter { it.extension == "log" }
            ?.maxByOrNull { it.lastModified() }

        if (logFile == null) {
            logger.info("No Copilot log files found")
            return
        }

        logger.info("Watching Copilot log: ${logFile.absolutePath}")
        
        var lastPosition = logFile.length()
        
        while (true) {
            delay(5000) // Check every 5 seconds
            
            if (!logFile.exists()) continue
            
            val currentLength = logFile.length()
            if (currentLength > lastPosition) {
                // New content
                logFile.inputStream().use { stream ->
                    stream.skip(lastPosition)
                    val newContent = stream.bufferedReader().readText()
                    processLogContent(newContent)
                }
                lastPosition = currentLength
            }
        }
    }

    private fun processLogContent(content: String) {
        // Parse log entries for token usage
        // Format varies by Copilot version, this is a heuristic
        val tokenPattern = Regex("""tokens[:\s]+(\d+).*?completion[:\s]+(\d+)""", RegexOption.IGNORE_CASE)
        val modelPattern = Regex("""model[:\s]+["']?([^"'\s,}]+)""", RegexOption.IGNORE_CASE)
        
        var lastModel = "gpt-4o"
        
        content.lines().forEach { line ->
            modelPattern.find(line)?.let {
                lastModel = it.groupValues[1]
            }
            
            tokenPattern.find(line)?.let { match ->
                val inputTokens = match.groupValues[1].toIntOrNull() ?: 0
                val outputTokens = match.groupValues[2].toIntOrNull() ?: 0
                
                if (inputTokens > 0 || outputTokens > 0) {
                    addMetric(TokenMetric(
                        userId = settings.userId,
                        model = lastModel,
                        inputTokens = inputTokens,
                        outputTokens = outputTokens,
                        team = settings.team.ifBlank { null },
                        project = settings.project.ifBlank { null },
                        context = "completion"
                    ))
                }
            }
        }
    }

    suspend fun fetchUserStats(): UserStats? {
        return try {
            val request = Request.Builder()
                .url("${settings.serverUrl}/v1/users/${settings.userId}")
                .addHeader("X-API-Key", settings.apiKey)
                .get()
                .build()

            val response = httpClient.newCall(request).execute()

            if (response.isSuccessful) {
                response.body?.string()?.let {
                    gson.fromJson(it, UserStats::class.java)
                }
            } else {
                if (response.code == 401) {
                    logger.error("Authentication failed (401) fetching user stats: invalid or missing X-API-Key. " +
                            "Configure a API Key em Tools > O11yIA Copilot Metrics.")
                } else {
                    logger.warn("Failed to fetch user stats: ${response.code}")
                }
                null
            }
        } catch (e: Exception) {
            logger.warn("Error fetching user stats: ${e.message}")
            null
        }
    }

    data class UserStats(
        @SerializedName("user_id") val userId: String,
        @SerializedName("total_credits") val totalCredits: Double,
        @SerializedName("total_input_tokens") val totalInputTokens: Long,
        @SerializedName("total_output_tokens") val totalOutputTokens: Long,
        @SerializedName("request_count") val requestCount: Int
    )

    companion object {
        fun getInstance(): MetricsCollectorService =
            ApplicationManager.getApplication().getService(MetricsCollectorService::class.java)
    }
}
