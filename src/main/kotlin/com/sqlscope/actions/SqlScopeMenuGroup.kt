package com.sqlscope.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.actionSystem.DefaultActionGroup

/**
 * Top-level "SQLScope" group injected into the Project View popup menu.
 *
 * The group is only visible when the selection contains at least one directory.
 * Child groups (Set SQL Dialect, Set Resolution Scope) are added via plugin.xml
 * <add-to-group> declarations, so this class inherits DefaultActionGroup's
 * getChildren() without modification.
 */
class SqlScopeMenuGroup : DefaultActionGroup() {

    override fun update(e: AnActionEvent) {
        super.update(e)
        val files = e.getData(CommonDataKeys.VIRTUAL_FILE_ARRAY)
        e.presentation.isEnabledAndVisible = files?.any { it.isDirectory } == true
    }

    // BGT = runs update() on a background thread, satisfying IntelliJ's threading
    // requirement for actions that do not touch the UI/model in update().
    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT
}
