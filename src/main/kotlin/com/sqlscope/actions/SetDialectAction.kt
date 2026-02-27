package com.sqlscope.actions

import com.intellij.icons.AllIcons
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.sql.dialects.SqlDialectMappings
import com.intellij.sql.dialects.SqlLanguageDialect
import com.sqlscope.services.SqlScopeService

/**
 * Applies a specific SQL dialect to the selected file(s) or directory(ies) by
 * calling SqlDialectMappings.setMapping(). Directory mappings are recursive —
 * all SQL files under the directory inherit this dialect.
 *
 * The [dialect] is a live Language object from the registry, not a string ID,
 * so there's no lookup step and no risk of the ID being wrong.
 */
class SetDialectAction(private val dialect: SqlLanguageDialect) : AnAction(dialect.displayName) {

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val files = SqlScopeMenuGroup.getSelectedFiles(e)
        if (files.isEmpty()) return
        val service = SqlScopeService.getInstance(project)
        val current = SqlDialectMappings.getInstance(project).getMapping(files.first())
        if (current == dialect) {
            files.forEach { service.clearDialect(it) }
        } else {
            files.forEach { service.setDialect(it, dialect) }
        }
    }

    override fun update(e: AnActionEvent) {
        val project = e.project
        val files = SqlScopeMenuGroup.getSelectedFiles(e)
        e.presentation.isEnabledAndVisible = project != null && files.isNotEmpty()
        if (project != null && files.isNotEmpty()) {
            val current = SqlDialectMappings.getInstance(project).getMapping(files.first())
            e.presentation.icon = if (current == dialect) AllIcons.Actions.Checked else null
        }
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT
}
