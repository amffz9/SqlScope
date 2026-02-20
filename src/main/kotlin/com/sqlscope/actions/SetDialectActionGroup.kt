package com.sqlscope.actions

import com.intellij.openapi.actionSystem.ActionGroup
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.actionSystem.Separator
import com.intellij.openapi.vfs.VirtualFile
import com.sqlscope.util.DialectRegistry

/**
 * "Set SQL Dialect" submenu.
 *
 * Children are built dynamically from the live Language registry each time the
 * menu opens, so any dialect the database plugin (or a third-party plugin) has
 * registered will appear automatically — no hardcoded list required.
 *
 * getChildren() runs on the EDT; DialectRegistry.availableDialects() only reads
 * in-memory Language registry state, so it is safe and fast.
 */
class SetDialectActionGroup : ActionGroup() {

    override fun getChildren(e: AnActionEvent?): Array<AnAction> {
        val dialectActions: List<AnAction> = DialectRegistry.availableDialects()
            .map { dialect -> SetDialectAction(dialect) }
        // Separator + "Clear Dialect" at the bottom
        return (dialectActions + Separator.getInstance() + ClearDialectAction()).toTypedArray()
    }

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabledAndVisible = getSelectedDirectory(e) != null
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT

    companion object {
        /**
         * Returns the single selected directory from the Project View, or null when:
         *  - nothing is selected
         *  - a file (not a directory) is selected
         *  - multiple items are selected
         */
        fun getSelectedDirectory(e: AnActionEvent): VirtualFile? =
            e.getData(CommonDataKeys.VIRTUAL_FILE_ARRAY)?.singleOrNull { it.isDirectory }
    }
}
