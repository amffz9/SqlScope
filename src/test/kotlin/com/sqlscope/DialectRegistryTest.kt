package com.sqlscope

import com.sqlscope.util.DialectRegistry
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.assertNotNull

/**
 * Unit tests for DialectRegistry.
 *
 * NOTE: DialectRegistry.availableDialects() calls Language.getRegisteredLanguages(),
 * which requires a running IntelliJ Platform. These tests therefore need to run
 * inside the IDE sandbox (./gradlew runIde + manual trigger, or the Plugin Test
 * framework). A plain JUnit run without the platform will return an empty list,
 * which is expected — there's nothing wrong to assert there.
 *
 * What IS testable without the platform: that the object exists and the method
 * returns a non-null, sorted collection.
 */
class DialectRegistryTest {

    @Test
    fun `availableDialects returns a non-null list`() {
        // Will be empty outside the IDE sandbox — that's fine.
        val dialects = DialectRegistry.availableDialects()
        assertNotNull(dialects)
    }

    @Test
    fun `availableDialects is sorted by display name`() {
        val dialects = DialectRegistry.availableDialects()
        val sorted = dialects.sortedBy { it.displayName }
        assert(dialects == sorted) {
            "Expected dialects sorted by displayName, got: ${dialects.map { it.displayName }}"
        }
    }

    @Test
    fun `logAvailableDialects returns a string`() {
        // Smoke test — just confirm it doesn't throw.
        val log = DialectRegistry.logAvailableDialects()
        assertNotNull(log)
    }
}
