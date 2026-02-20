package com.sqlscope.actions

import com.intellij.database.psi.DbDataSource
import com.intellij.database.util.DasUtil
import com.intellij.openapi.actionSystem.ActionGroup
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.Separator

/**
 * Per-data-source popup submenu inside "Set Resolution Scope".
 *
 * Menu structure:
 *   ▶ My Server (MySQL @ localhost)
 *       Whole data source
 *       ──────────────────
 *       information_schema
 *       my_app_db
 *       sys
 *
 * "Whole data source" scopes to the entire server so IntelliJ searches all
 * schemas for symbol resolution. Selecting an individual schema restricts
 * resolution to that schema only — useful when multiple databases share table
 * names or when you want tighter completion.
 */
class DataSourceResolutionGroup(private val dataSource: DbDataSource) :
    ActionGroup(dataSource.name, true) {

    override fun getChildren(e: AnActionEvent?): Array<AnAction> {
        val actions = mutableListOf<AnAction>()

        // First entry scopes to the whole server.
        actions.add(SetResolutionAction("Whole data source", dataSource))

        // Enumerate schemas (DasNamespace) available under this data source.
        // DasUtil.getSchemas() returns an in-memory JBIterable — safe on EDT.
        val schemas = DasUtil.getSchemas(dataSource).toList()
        if (schemas.isNotEmpty()) {
            actions.add(Separator.getInstance())
            schemas.forEach { schema ->
                actions.add(SetResolutionAction(schema.name, schema))
            }
        }

        return actions.toTypedArray()
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT
}
