package com.sqlscope.actions

import com.intellij.database.Dbms
import com.intellij.database.psi.DbPsiFacade
import com.intellij.database.dataSource.DataSourceSchemaMapping
import com.intellij.database.util.DasUtil
import com.intellij.database.util.DbImplUtilCore
import com.intellij.openapi.actionSystem.ActionGroup
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.actionSystem.DefaultActionGroup
import com.intellij.openapi.actionSystem.Separator
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.sql.dialects.SqlLanguageDialect
import com.sqlscope.util.DialectRegistry

/**
 * Top-level "SQLScope" group injected into the Project View popup menu.
 *
 * Builds the flat menu dynamically each time the menu opens:
 *
 *   ── Dialect ──────────────────────────────
 *   MySQL                  ← matches a configured datasource's DBMS
 *   PostgreSQL             ← matches a configured datasource's DBMS
 *   More Dialects ▶        ← remaining dialects (omitted when no datasources)
 *   Clear Dialect
 *   ── Resolution Scope ─────────────────────  ← only when datasources exist
 *   MySQL @ localhost  ▶   ← datasource submenu (only introspected schemas)
 *     ├ my_app_db
 *     ├ ─────────
 *     └ All (MySQL @ localhost)
 *   Clear Resolution Scope
 *
 * When no datasources are configured all dialects appear flat under the Dialect
 * header with no "More Dialects" submenu, and the Resolution Scope section is
 * omitted (only "Clear Resolution Scope" remains).
 */
class SqlScopeMenuGroup : ActionGroup() {

    override fun getChildren(e: AnActionEvent?): Array<AnAction> {
        val project = e?.project ?: return AnAction.EMPTY_ARRAY
        getSelectedDirectory(e) ?: return AnAction.EMPTY_ARRAY

        val dataSources = try {
            DbPsiFacade.getInstance(project).dataSources.toList()
        } catch (_: Exception) {
            emptyList()
        }

        val allDialects = DialectRegistry.availableDialects()
        val actions = mutableListOf<AnAction>()

        // ── Dialect section ───────────────────────────────────────────────
        actions.add(Separator("Dialect"))

        if (dataSources.isEmpty()) {
            // No datasources configured: show every dialect flat.
            allDialects.forEach { dialect -> actions.add(SetDialectAction(dialect)) }
        } else {
            val (primary, more) = allDialects.partition { dialect ->
                dataSources.any { ds -> matchesDialect(ds.dbms, dialect) }
            }
            primary.forEach { dialect -> actions.add(SetDialectAction(dialect)) }
            if (more.isNotEmpty()) {
                val moreGroup = DefaultActionGroup("More Dialects", true)
                more.forEach { dialect -> moreGroup.add(SetDialectAction(dialect)) }
                actions.add(moreGroup)
            }
        }

        actions.add(ClearDialectAction())

        // ── Resolution Scope section ──────────────────────────────────────
        if (dataSources.isNotEmpty()) {
            actions.add(Separator("Resolution Scope"))

            dataSources.forEach { ds ->
                val scope = DbImplUtilCore.getIntrospectionScope(ds)
                    ?: return@forEach  // no introspection configured → skip

                val schemas = DasUtil.getSchemas(ds)
                    .filter { DataSourceSchemaMapping.isIntrospected(scope, it) }
                    .toList()

                if (schemas.isEmpty()) return@forEach

                val dsGroup = DefaultActionGroup(ds.name, true)
                schemas.forEach { schema ->
                    dsGroup.add(SetResolutionAction(schema.name, schema))
                }
                dsGroup.add(Separator.getInstance())
                dsGroup.add(SetResolutionAction("All (${ds.name})", ds))
                actions.add(dsGroup)
            }
        }

        actions.add(ClearResolutionAction())

        return actions.toTypedArray()
    }

    override fun update(e: AnActionEvent) {
        super.update(e)
        val files = e.getData(CommonDataKeys.VIRTUAL_FILE_ARRAY)
        e.presentation.isEnabledAndVisible = files?.any { it.isDirectory } == true
    }

    // BGT: update() only reads getData() — no model/UI access required.
    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT

    /**
     * Returns true if [dbms] corresponds to the SQL dialect [dialect].
     *
     * Uses bidirectional case-insensitive substring matching, plus an explicit
     * "sql server" alias to map "Microsoft SQL Server" ↔ "SQL Server (T-SQL)".
     */
    private fun matchesDialect(dbms: Dbms, dialect: SqlLanguageDialect): Boolean {
        if (dbms == Dbms.UNKNOWN) return false
        val dbmsName = dbms.displayName.lowercase()
        val dialectName = dialect.displayName.lowercase()
        return dbmsName.contains(dialectName)
            || dialectName.contains(dbmsName)
            || (dbmsName.contains("sql server") && dialectName.contains("sql server"))
    }

    companion object {
        /**
         * Returns the single selected directory from the Project View, or null when:
         *  - nothing is selected
         *  - a file (not a directory) is selected
         *  - multiple items are selected
         */
        fun getSelectedDirectory(e: AnActionEvent?): VirtualFile? =
            e?.getData(CommonDataKeys.VIRTUAL_FILE_ARRAY)?.singleOrNull { it.isDirectory }
    }
}
