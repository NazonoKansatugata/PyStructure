package com.pystructure

import com.intellij.openapi.components.Service
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.project.Project
import javax.swing.JTextArea

@Service(Service.Level.PROJECT)
class PyStructureOutputService(private val project: Project) {
    @Volatile
    private var outputArea: JTextArea? = null

    fun attach(area: JTextArea) {
        outputArea = area
    }

    fun showText(text: String) {
        ApplicationManager.getApplication().invokeLater {
            outputArea?.text = text
        }
    }

    companion object {
        fun getInstance(project: Project): PyStructureOutputService = project.getService(PyStructureOutputService::class.java)
    }
}
