package com.pystructure

import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.fileEditor.OpenFileDescriptor
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.ui.content.ContentFactory
import java.awt.BorderLayout
import javax.swing.JTabbedPane
import javax.swing.JPanel
import javax.swing.JScrollPane
import javax.swing.JTextArea
import javax.swing.JTree
import javax.swing.tree.DefaultMutableTreeNode
import javax.swing.tree.DefaultTreeModel

class PyStructureToolWindowFactory : ToolWindowFactory, DumbAware {
    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val root = DefaultMutableTreeNode("PyStructure")
        val tree = JTree(DefaultTreeModel(root)).apply {
            showsRootHandles = true
            addMouseListener(object : java.awt.event.MouseAdapter() {
                override fun mouseClicked(event: java.awt.event.MouseEvent) {
                    if (event.clickCount != 2) return
                    val node = getPathForLocation(event.x, event.y)?.lastPathComponent as? DefaultMutableTreeNode
                    val entry = node?.userObject as? SourceEntry ?: return
                    val path = entry.path ?: return
                    val file = LocalFileSystem.getInstance().findFileByPath(path.replace('\\', '/')) ?: return
                    val line = ((entry.line ?: 1) - 1).coerceAtLeast(0)
                    OpenFileDescriptor(project, file, line, 0).navigate(true)
                }
            })
        }

        val statusArea = JTextArea().apply {
            isEditable = false
            lineWrap = true
            wrapStyleWord = true
            text = "PyStructure の解析結果をここに表示します。"
        }

        val graphPanel = DependencyGraphPanel { path ->
            val file = LocalFileSystem.getInstance().findFileByPath(path.replace('\\', '/'))
            if (file != null) {
                FileEditorManager.getInstance(project).openFile(file, true)
            }
        }
        val tabs = JTabbedPane().apply {
            addTab("Analysis", JScrollPane(tree))
            addTab("Dependency Graph", graphPanel)
        }

        // 助言を選択するとグラフ上の対象を強調し、ダブルクリックでグラフタブへ切り替える
        tree.addTreeSelectionListener { event ->
            val node = event.path?.lastPathComponent as? DefaultMutableTreeNode
            val advice = node?.userObject as? AdviceEntry ?: return@addTreeSelectionListener
            graphPanel.highlightModules(advice.targets)
        }
        tree.addMouseListener(object : java.awt.event.MouseAdapter() {
            override fun mouseClicked(event: java.awt.event.MouseEvent) {
                if (event.clickCount != 2) return
                val node = tree.getPathForLocation(event.x, event.y)?.lastPathComponent as? DefaultMutableTreeNode
                if (node?.userObject is AdviceEntry) tabs.selectedIndex = 1
            }
        })
        val panel = JPanel(BorderLayout()).apply {
            add(tabs, BorderLayout.CENTER)
            add(JScrollPane(statusArea), BorderLayout.SOUTH)
        }

        PyStructureOutputService.getInstance(project).attach(tree, statusArea, graphPanel)

        val content = ContentFactory.getInstance().createContent(panel, null, false)
        toolWindow.contentManager.addContent(content)
        com.intellij.openapi.actionSystem.ActionManager.getInstance().getAction("PyStructure.ExportAdvice")
            ?.let { toolWindow.setTitleActions(listOf(it)) }
    }
}
