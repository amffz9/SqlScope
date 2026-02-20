package com.sqlscope.actions

import com.intellij.database.model.DasObject
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.sqlscope.services.SqlScopeService

/**
 * Associates the selected directory with a specific resolution scope.
 *
 * [scope] can be a DbDataSource (whole server) or a DasNamespace (individual
 * schema / database on that server). The [displayName] is shown in the menu.
 */
class SetResolutionAction(
    private val displayName: String,
    private val scope: DasObject,
) : AnAction(displayName) {

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val directory = SqlScopeMenuGroup.getSelectedDirectory(e) ?: return
        SqlScopeService.getInstance(project).setResolutionScope(directory, scope, displayName)
    }

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabledAndVisible =
            e.project != null && SqlScopeMenuGroup.getSelectedDirectory(e) != null
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT
}
