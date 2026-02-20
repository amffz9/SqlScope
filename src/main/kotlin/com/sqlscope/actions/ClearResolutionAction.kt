package com.sqlscope.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.sqlscope.services.SqlScopeService

/**
 * Removes the data source resolution scope mapping for the selected directory.
 * After clearing, IntelliJ will fall back to the parent's scope or no scope.
 */
class ClearResolutionAction : AnAction("Clear Resolution Scope") {

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val directory = SetDialectActionGroup.getSelectedDirectory(e) ?: return
        SqlScopeService.getInstance(project).clearResolutionScope(directory)
    }

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabledAndVisible =
            e.project != null && SetDialectActionGroup.getSelectedDirectory(e) != null
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT
}
