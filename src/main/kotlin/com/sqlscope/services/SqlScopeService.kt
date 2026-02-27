package com.sqlscope.services

import com.intellij.database.model.DasObject
import com.intellij.database.util.TreePattern
import com.intellij.database.util.TreePatternUtils
import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.sql.dialects.SqlDialectMappings
import com.intellij.sql.dialects.SqlLanguageDialect
import com.intellij.sql.dialects.SqlResolveMappings

/**
 * Core service that applies SQL dialect and resolution-scope mappings.
 *
 * Registered as a project-level service in plugin.xml so that it is created
 * once per open project and disposed when the project is closed.
 *
 * Obtain an instance with [SqlScopeService.getInstance].
 */
@Service(Service.Level.PROJECT)
class SqlScopeService(private val project: Project) {

    // -------------------------------------------------------------------------
    // Dialect mapping
    // -------------------------------------------------------------------------

    /**
     * Sets the SQL dialect for [directory] and all SQL files beneath it.
     *
     * Persists in .idea/sqldialects.xml (committed to VCS by default).
     * The mapping is recursive: child files inherit from the nearest ancestor.
     */
    fun setDialect(directory: VirtualFile, language: SqlLanguageDialect) {
        SqlDialectMappings.getInstance(project).setMapping(directory, language)
        notify("Set SQL dialect to <b>${language.displayName}</b> for <code>${directory.presentableName}</code>")
    }

    /**
     * Clears the dialect mapping for [directory], reverting to the parent's dialect.
     */
    fun clearDialect(directory: VirtualFile) {
        SqlDialectMappings.getInstance(project).setMapping(directory, null)
        notify("Cleared SQL dialect for <code>${directory.presentableName}</code>")
    }

    // -------------------------------------------------------------------------
    // Resolution scope mapping
    // -------------------------------------------------------------------------

    /**
     * Associates [directory] with [scope] for SQL symbol resolution.
     *
     * [scope] can be any DasObject — a whole DbDataSource (server) or a
     * DasNamespace (schema / database on that server). TreePatternUtils.create()
     * builds the appropriate TreePattern in either case.
     *
     * Persists in .idea/sqldialects.xml via SqlResolveMappings, mirroring
     * Settings → Languages & Frameworks → SQL Resolution Scopes.
     */
    fun setResolutionScope(directory: VirtualFile, scope: DasObject, displayName: String) {
        val pattern = TreePattern(TreePatternUtils.create(scope))
        SqlResolveMappings.getInstance(project).setMapping(directory, pattern)
        notify("Set resolution scope to <b>$displayName</b> for <code>${directory.presentableName}</code>")
    }

    /**
     * Clears the resolution scope mapping for [directory].
     */
    fun clearResolutionScope(directory: VirtualFile) {
        SqlResolveMappings.getInstance(project).setMapping(directory, null)
        notify("Cleared resolution scope for <code>${directory.presentableName}</code>")
    }

    // -------------------------------------------------------------------------
    // Notifications
    // -------------------------------------------------------------------------

    fun showError(htmlMessage: String) {
        NotificationGroupManager.getInstance()
            .getNotificationGroup(NOTIFICATION_GROUP)
            .createNotification("SQLScope", htmlMessage, NotificationType.ERROR)
            .notify(project)
    }

    private fun notify(htmlMessage: String) {
        NotificationGroupManager.getInstance()
            .getNotificationGroup(NOTIFICATION_GROUP)
            .createNotification("SQLScope", htmlMessage, NotificationType.INFORMATION)
            .notify(project)
    }

    companion object {
        private const val NOTIFICATION_GROUP = "SQLScope Notifications"

        fun getInstance(project: Project): SqlScopeService = project.service()
    }
}
