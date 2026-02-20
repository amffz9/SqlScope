package com.sqlscope.util

import com.intellij.sql.dialects.SqlLanguageDialect

/**
 * Discovers available SQL dialects dynamically from the IntelliJ Platform's
 * language registry at runtime.
 *
 * This is better than a hardcoded list because:
 *  - It picks up every dialect registered by the database plugin (and any
 *    third-party plugins that add dialects) without code changes.
 *  - The display names and IDs come directly from the Language objects,
 *    so they're always correct for the running IDE version.
 */
object DialectRegistry {

    /**
     * Returns all SQL dialects registered in the current IDE, sorted
     * alphabetically by display name for a consistent menu order.
     *
     * SqlLanguageDialect is the common base class for MySQL, PostgreSQL,
     * SQLite, etc. — filtering by it automatically excludes non-SQL languages.
     */
    fun availableDialects(): List<SqlLanguageDialect> =
        SqlLanguageDialect.getRegisteredLanguages()
            .filterIsInstance<SqlLanguageDialect>()
            .sortedBy { it.displayName }

    /**
     * Returns a debug-friendly list of all discovered dialects.
     * Useful when a dialect is missing from the menu — call this from
     * an action and log/notify the result.
     */
    fun logAvailableDialects(): String =
        availableDialects()
            .joinToString("\n") { "  ${it.id} → ${it.displayName}" }
            .ifBlank { "  (no SqlLanguageDialect instances registered)" }
}
