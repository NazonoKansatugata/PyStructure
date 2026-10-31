package com.pystructure

import java.io.File

data class CliRunResult(
    val exitCode: Int,
    val stdout: String,
    val stderr: String,
)

object PyStructureCliRunner {
    fun run(projectBasePath: String, command: String = "pystructure", jsonOutput: Boolean = false): CliRunResult {
        val arguments = mutableListOf(command, "analyze", projectBasePath)
        if (jsonOutput) {
            arguments.add("--json")
        }

        arguments[0] = resolveCommand(projectBasePath, command)

        return try {
            val process = ProcessBuilder(arguments)
                .directory(File(projectBasePath))
                .start()

            // stderr を別スレッドで読み、パイプ詰まりによるデッドロックを避ける
            var stderr = ""
            val stderrReader = Thread { stderr = process.errorStream.bufferedReader().use { it.readText() } }
            stderrReader.start()
            val stdout = process.inputStream.bufferedReader().use { reader -> reader.readText() }
            val exitCode = process.waitFor()
            stderrReader.join()

            CliRunResult(exitCode = exitCode, stdout = stdout, stderr = stderr)
        } catch (e: java.io.IOException) {
            CliRunResult(
                exitCode = -1,
                stdout = "",
                stderr = "Failed to start '${arguments[0]}': ${e.message}\n" +
                    "Set the full path to the pystructure executable in Settings | PyStructure.",
            )
        }
    }

    // コマンド名のみの場合は、プロジェクトの仮想環境内の実行ファイルを優先する
    private fun resolveCommand(projectBasePath: String, command: String): String {
        if (command.contains('/') || command.contains('\\')) return command
        for (venv in listOf(".venv", "venv")) {
            for (candidate in listOf("Scripts\\$command.exe", "bin/$command")) {
                val file = File(projectBasePath, "$venv/$candidate")
                if (file.isFile) return file.absolutePath
            }
        }
        return command
    }
}
