package com.sqlscope.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.sqlscope.services.SqlScopeService

/**
 * Removes the SQL dialect mapping for the selected directory by calling
 * SqlDialectMappings.setMapping(file, null).
 *
 * After clearing, IntelliJ will fall back to the parent directory's dialect
 * or the project-wide default.
 */
class ClearDialectAction : AnAction("Clear Dialect") {

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val directory = SetDialectActionGroup.getSelectedDirectory(e) ?: return
        SqlScopeService.getInstance(project).clearDialect(directory)
    }

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabledAndVisible =
            e.project != null && SetDialectActionGroup.getSelectedDirectory(e) != null
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT
}
