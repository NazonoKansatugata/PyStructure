package com.pystructure

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage

@State(name = "PyStructureSettings", storages = [Storage("PyStructure.xml")])
@Service(Service.Level.APP)
class PyStructureSettings : PersistentStateComponent<PyStructureSettings.State> {
    data class State(
        var cliCommand: String = "pystructure",
    )

    var settingsState = State()

    override fun getState(): State = settingsState

    override fun loadState(state: State) {
        settingsState = state
    }

    companion object {
        fun getInstance(): PyStructureSettings = ApplicationManager.getApplication().getService(PyStructureSettings::class.java)
    }
}