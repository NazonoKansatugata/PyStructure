package com.pystructure

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.ui.Messages
import com.intellij.notification.NotificationType
import com.intellij.notification.NotificationGroupManager

class PyStructureAnalyzeAction : AnAction(), DumbAware {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: run {
            Messages.showErrorDialog("PyStructure: プロジェクトが開かれていません。", "PyStructure")
            return
        }

        val basePath = project.basePath ?: run {
            Messages.showErrorDialog("PyStructure: プロジェクトの basePath を取得できませんでした。", "PyStructure")
            return
        }

        val command = PyStructureSettings.getInstance().settingsState.cliCommand.trim().ifBlank { "pystructure" }

        ApplicationManager.getApplication().executeOnPooledThread {
            val result = PyStructureCliRunner.run(basePath, command, jsonOutput = false)
            val outputService = PyStructureOutputService.getInstance(project)

            ApplicationManager.getApplication().invokeLater {
                if (result.exitCode == 0) {
                    val text = buildString {
                        appendLine("PyStructure analysis completed")
                        appendLine("Project: $basePath")
                        appendLine("Command: $command")
                        appendLine("stdout:")
                        appendLine(result.stdout.ifBlank { "(empty)" })
                    }
                    outputService.showText(text)
                    NotificationGroupManager.getInstance()
                        .getNotificationGroup("PyStructure")
                        .createNotification(
                            "Analysis complete",
                            "PyStructure CLI ran successfully.",
                            NotificationType.INFORMATION,
                        )
                        .notify(project)
                } else {
                    val text = buildString {
                        appendLine("PyStructure analysis failed")
                        appendLine("Project: $basePath")
                        appendLine("Command: $command")
                        appendLine("Exit code: ${result.exitCode}")
                        appendLine("stderr:")
                        appendLine(result.stderr.ifBlank { "(empty)" })
                        appendLine("stdout:")
                        appendLine(result.stdout.ifBlank { "(empty)" })
                    }
                    outputService.showText(text)
                    NotificationGroupManager.getInstance()
                        .getNotificationGroup("PyStructure")
                        .createNotification(
                            "Analysis failed",
                            "Exit code: ${result.exitCode}\nstderr: ${result.stderr.ifBlank { "(empty)" }}",
                            NotificationType.ERROR,
                        )
                        .notify(project)
                }
            }
        }
    }
}
