package com.pystructure

import com.intellij.openapi.options.Configurable
import java.awt.BorderLayout
import javax.swing.JComponent
import javax.swing.JLabel
import javax.swing.JPanel
import javax.swing.JTextField

class PyStructureSettingsConfigurable : Configurable {
    private var panel: JPanel? = null
    private var commandField: JTextField? = null

    override fun getDisplayName(): String = "PyStructure"

    override fun createComponent(): JComponent {
        if (panel != null) {
            return panel!!
        }

        val field = JTextField()
        val container = JPanel(BorderLayout(0, 8)).apply {
            add(JLabel("PyStructure CLI command"), BorderLayout.NORTH)
            add(field, BorderLayout.CENTER)
        }

        panel = container
        commandField = field
        reset()
        return container
    }

    override fun isModified(): Boolean {
        val fieldValue = commandField?.text?.trim().orEmpty().ifBlank { "pystructure" }
        return fieldValue != PyStructureSettings.getInstance().settingsState.cliCommand
    }

    override fun apply() {
        PyStructureSettings.getInstance().settingsState = PyStructureSettings.State(
            cliCommand = commandField?.text?.trim().orEmpty().ifBlank { "pystructure" },
        )
    }

    override fun reset() {
        commandField?.text = PyStructureSettings.getInstance().settingsState.cliCommand
    }

    override fun disposeUIResources() {
        panel = null
        commandField = null
    }
}