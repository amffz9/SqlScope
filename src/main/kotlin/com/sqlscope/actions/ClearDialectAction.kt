package com.sqlscope.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.sqlscope.services.SqlScopeService

/**
 * Removes the SQL dialect mapping for the selected file(s) or directory(ies)
 * by calling SqlDialectMappings.setMapping(file, null).
 *
 * After clearing, IntelliJ will fall back to the parent's dialect
 * or the project-wide default.
 */
class ClearDialectAction : AnAction("Clear Dialect") {

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val files = SqlScopeMenuGroup.getSelectedFiles(e)
        files.forEach { SqlScopeService.getInstance(project).clearDialect(it) }
    }

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabledAndVisible =
            e.project != null && SqlScopeMenuGroup.getSelectedFiles(e).isNotEmpty()
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT
}
