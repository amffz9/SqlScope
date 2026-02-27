package com.sqlscope.actions

import com.intellij.icons.AllIcons
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.sql.dialects.SqlDialectMappings
import com.intellij.sql.dialects.SqlLanguageDialect
import com.sqlscope.services.SqlScopeService

/**
 * Applies a specific SQL dialect to the selected directory by calling
 * SqlDialectMappings.setMapping(). The mapping is recursive — all SQL files
 * under the directory inherit this dialect.
 *
 * The [dialect] is a live Language object from the registry, not a string ID,
 * so there's no lookup step and no risk of the ID being wrong.
 */
class SetDialectAction(private val dialect: SqlLanguageDialect) : AnAction(dialect.displayName) {

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val directory = SqlScopeMenuGroup.getSelectedDirectory(e) ?: return
        val service = SqlScopeService.getInstance(project)
        val current = SqlDialectMappings.getInstance(project).getMapping(directory)
        if (current == dialect) {
            service.clearDialect(directory)
        } else {
            service.setDialect(directory, dialect)
        }
    }

    override fun update(e: AnActionEvent) {
        val project = e.project
        val directory = project?.let { SqlScopeMenuGroup.getSelectedDirectory(e) }
        e.presentation.isEnabledAndVisible = project != null && directory != null
        if (project != null && directory != null) {
            val current = SqlDialectMappings.getInstance(project).getMapping(directory)
            e.presentation.icon = if (current == dialect) AllIcons.Actions.Checked else null
        }
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT
}
