package com.sqlscope.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.sqlscope.services.SqlScopeService

/**
 * Removes the data source resolution scope mapping for the selected file(s)
 * or directory(ies). After clearing, IntelliJ will fall back to the parent's
 * scope or no scope.
 */
class ClearResolutionAction : AnAction("Clear Resolution Scope") {

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val files = SqlScopeMenuGroup.getSelectedFiles(e)
        files.forEach { SqlScopeService.getInstance(project).clearResolutionScope(it) }
    }

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabledAndVisible =
            e.project != null && SqlScopeMenuGroup.getSelectedFiles(e).isNotEmpty()
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT
}
