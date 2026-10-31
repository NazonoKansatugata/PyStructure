package com.pystructure

import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.fileChooser.FileSaverDescriptor
import com.intellij.openapi.fileChooser.FileChooserFactory
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.vfs.LocalFileSystem
import java.io.File

class PyStructureExportAdviceAction : AnAction(), DumbAware {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: run {
            Messages.showErrorDialog("PyStructure: プロジェクトが開かれていません。", "PyStructure")
            return
        }
        val basePath = project.basePath ?: run {
            Messages.showErrorDialog("PyStructure: プロジェクトの basePath を取得できませんでした。", "PyStructure")
            return
        }

        val descriptor = FileSaverDescriptor("Export PyStructure Advice", "Save the advice as a Markdown file", "md")
        val wrapper = FileChooserFactory.getInstance()
            .createSaveFileDialog(descriptor, project)
            .save(LocalFileSystem.getInstance().findFileByPath(basePath), "pystructure-advice.md") ?: return
        val target: File = wrapper.file

        val command = PyStructureSettings.getInstance().settingsState.cliCommand.trim().ifBlank { "pystructure" }

        ApplicationManager.getApplication().executeOnPooledThread {
            val result = PyStructureCliRunner.run(basePath, command, markdownOutput = true)
            val saved = result.exitCode == 0 && runCatching { target.writeText(result.stdout, Charsets.UTF_8) }.isSuccess

            ApplicationManager.getApplication().invokeLater {
                val group = NotificationGroupManager.getInstance().getNotificationGroup("PyStructure")
                if (saved) {
                    group.createNotification("Advice exported", target.absolutePath, NotificationType.INFORMATION).notify(project)
                    LocalFileSystem.getInstance().refreshAndFindFileByIoFile(target)?.let {
                        FileEditorManager.getInstance(project).openFile(it, true)
                    }
                } else {
                    group.createNotification(
                        "Advice export failed",
                        "Exit code: ${result.exitCode}\nstderr: ${result.stderr.ifBlank { "(empty)" }}",
                        NotificationType.ERROR,
                    ).notify(project)
                }
            }
        }
    }
}
