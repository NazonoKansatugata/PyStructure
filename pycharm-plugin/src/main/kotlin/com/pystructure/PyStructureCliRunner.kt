package com.pystructure

import java.io.File

data class CliRunResult(
    val exitCode: Int,
    val stdout: String,
    val stderr: String,
)

object PyStructureCliRunner {
    fun run(projectBasePath: String, command: String = "pystructure"): CliRunResult {
        val process = ProcessBuilder(
            command,
            "analyze",
            projectBasePath,
            "--json",
        )
            .directory(File(projectBasePath))
            .start()

        val stdout = process.inputStream.bufferedReader().use { reader -> reader.readText() }
        val stderr = process.errorStream.bufferedReader().use { reader -> reader.readText() }
        val exitCode = process.waitFor()

        return CliRunResult(
            exitCode = exitCode,
            stdout = stdout,
            stderr = stderr,
        )
    }
}
