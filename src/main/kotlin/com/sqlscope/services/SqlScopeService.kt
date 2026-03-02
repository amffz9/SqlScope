package com.sqlscope.services

import com.intellij.database.model.DasDataSource
import com.intellij.database.model.DasObject
import com.intellij.database.model.ObjectName
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
     * Sets the SQL dialect for [file] (file or directory) and all SQL files beneath it.
     *
     * Persists in .idea/sqldialects.xml (committed to VCS by default).
     * The mapping is recursive: child files inherit from the nearest ancestor.
     */
    fun setDialect(file: VirtualFile, language: SqlLanguageDialect) {
        SqlDialectMappings.getInstance(project).setMapping(file, language)
        notify("Set SQL dialect to <b>${language.displayName}</b> for <code>${file.presentableName}</code>")
    }

    /**
     * Clears the dialect mapping for [file], reverting to the parent's dialect.
     */
    fun clearDialect(file: VirtualFile) {
        SqlDialectMappings.getInstance(project).setMapping(file, null)
        notify("Cleared SQL dialect for <code>${file.presentableName}</code>")
    }

    // -------------------------------------------------------------------------
    // Resolution scope mapping
    // -------------------------------------------------------------------------

    /**
     * Associates [file] (file or directory) with [scope] for SQL symbol resolution.
     *
     * [datasource] is the DbPsiDataSource from DbPsiFacade — required because the
     * model-level ancestor chain does not expose the datasource's UUID; only the
     * PSI wrapper does via getUniqueId().
     *
     * Persists in .idea/sqldialects.xml via SqlResolveMappings, mirroring
     * Settings → Languages & Frameworks → SQL Resolution Scopes.
     */
    fun setResolutionScope(file: VirtualFile, scope: DasObject, datasource: DasDataSource, displayName: String) {
        val pattern = buildPattern(scope, datasource)
        SqlResolveMappings.getInstance(project).setMapping(file, pattern)
        notify("Set resolution scope to <b>$displayName</b> for <code>${file.presentableName}</code>")
    }

    /**
     * Clears the resolution scope mapping for [file].
     */
    fun clearResolutionScope(file: VirtualFile) {
        SqlResolveMappings.getInstance(project).setMapping(file, null)
        notify("Cleared resolution scope for <code>${file.presentableName}</code>")
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

        /**
         * Builds a TreePattern anchored to [datasource] by its UUID.
         *
         * Walks up from [scope] via getDasParent() until the chain terminates (model root
         * has no parent) or a DasDataSource is encountered (DbPsiDataSource case). The
         * root-level node's name is always empty in the internal model; [datasource].uniqueId
         * supplies the stable UUID that SqlResolveMappings stores in sqldialects.xml.
         */
        fun buildPattern(scope: DasObject, datasource: DasDataSource): TreePattern {
            // Walk up from scope. Stop when:
            //   - current is DasDataSource (e.g. DbPsiDataSource passed directly as scope), or
            //   - getDasParent() returns null (plain model-root DasObject with kind=root)
            val chain = mutableListOf<DasObject>()
            var current: DasObject? = scope
            while (current != null) {
                chain.add(current)
                if (current is DasDataSource) break
                current = current.getDasParent()
            }

            // chain[0] = scope (leaf), chain[last] = datasource-level node.
            // The datasource-level node's name is always empty in the model; use
            // datasource.uniqueId (from the DbPsiDataSource wrapper) for the UUID.
            val uuid = datasource.uniqueId

            if (chain.size == 1) {
                // scope is already at the datasource level (e.g. "All" scope)
                return TreePattern(TreePatternUtils.create(ObjectName(uuid, false), chain[0].kind))
            }

            // Build groups from leaf (chain[0]) inward, wrapping each ancestor level.
            // The last element gets the UUID; intermediate elements use their own name.
            var group = TreePatternUtils.create(chain[0])
            for (i in 1 until chain.size) {
                val obj = chain[i]
                group = if (i == chain.size - 1)
                    TreePatternUtils.create(ObjectName(uuid, false), obj.kind, group)
                else
                    TreePatternUtils.create(obj, group)
            }
            return TreePattern(group)
        }
    }
}
