package com.sqlscope.actions

import com.intellij.database.psi.DbPsiFacade
import com.intellij.openapi.actionSystem.ActionGroup
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.Separator

/**
 * "Set Resolution Scope" submenu.
 *
 * Each configured data source appears as a nested popup (DataSourceResolutionGroup)
 * that lets the user choose between scoping to the whole server or to a specific
 * schema / database within it.
 *
 * Menu structure:
 *   Set Resolution Scope
 *   ├── ▶ MySQL @ localhost
 *   │       Whole data source
 *   │       ──────────────
 *   │       my_app_db
 *   │       sys
 *   ├── ▶ PostgreSQL @ prod
 *   │       Whole data source
 *   │       ──────────────
 *   │       public
 *   ├── ──────────────────────
 *   └── Clear Resolution Scope
 */
class SetResolutionActionGroup : ActionGroup() {

    override fun getChildren(e: AnActionEvent?): Array<AnAction> {
        val project = e?.project ?: return AnAction.EMPTY_ARRAY

        val dataSources = try {
            DbPsiFacade.getInstance(project).dataSources.toList()
        } catch (_: Exception) {
            emptyList()
        }

        val actions = mutableListOf<AnAction>()
        // One submenu per data source — each expands to show the server and its schemas.
        dataSources.forEach { ds -> actions.add(DataSourceResolutionGroup(ds)) }

        if (actions.isNotEmpty()) actions.add(Separator.getInstance())
        actions.add(ClearResolutionAction())

        return actions.toTypedArray()
    }

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabledAndVisible = SetDialectActionGroup.getSelectedDirectory(e) != null
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT
}
