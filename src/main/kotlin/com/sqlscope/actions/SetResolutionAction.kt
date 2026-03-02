package com.sqlscope.actions

import com.intellij.database.model.DasDataSource
import com.intellij.database.model.DasObject
import com.intellij.icons.AllIcons
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.sql.dialects.SqlResolveMappings
import com.sqlscope.services.SqlScopeService

/**
 * Associates the selected file(s) or directory(ies) with a specific resolution scope.
 *
 * [scope] is the DasObject representing the schema, database, or datasource to target.
 * [datasource] is the DbPsiDataSource that owns [scope]; its UUID is needed to build
 * a correctly anchored TreePattern (the model-level ancestor chain does not expose it).
 */
class SetResolutionAction(
    private val displayName: String,
    private val scope: DasObject,
    private val datasource: DasDataSource,
) : AnAction(displayName) {

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val files = SqlScopeMenuGroup.getSelectedFiles(e)
        if (files.isEmpty()) return
        val service = SqlScopeService.getInstance(project)
        val current = SqlResolveMappings.getInstance(project).getMapping(files.first())
        val thisPattern = SqlScopeService.buildPattern(scope, datasource)
        if (current != null && current.toString() == thisPattern.toString()) {
            files.forEach { service.clearResolutionScope(it) }
        } else {
            files.forEach { service.setResolutionScope(it, scope, datasource, displayName) }
        }
    }

    override fun update(e: AnActionEvent) {
        val project = e.project
        val files = SqlScopeMenuGroup.getSelectedFiles(e)
        e.presentation.isEnabledAndVisible = project != null && files.isNotEmpty()
        if (project != null && files.isNotEmpty()) {
            val current = SqlResolveMappings.getInstance(project).getMapping(files.first())
            if (current != null && current.isNotEmpty()) {
                val thisPattern = SqlScopeService.buildPattern(scope, datasource)
                e.presentation.icon = if (current.toString() == thisPattern.toString()) AllIcons.Actions.Checked else null
            } else {
                e.presentation.icon = null
            }
        }
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT
}
