package com.pystructure

import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.content.ContentFactory
import java.awt.BorderLayout
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
        }

        val statusArea = JTextArea().apply {
            isEditable = false
            lineWrap = true
            wrapStyleWord = true
            text = "PyStructure の解析結果をここに表示します。"
        }

        val panel = JPanel(BorderLayout()).apply {
            add(JScrollPane(tree), BorderLayout.CENTER)
            add(JScrollPane(statusArea), BorderLayout.SOUTH)
        }

        PyStructureOutputService.getInstance(project).attach(tree, statusArea)

        val content = ContentFactory.getInstance().createContent(panel, null, false)
        toolWindow.contentManager.addContent(content)
    }
}
