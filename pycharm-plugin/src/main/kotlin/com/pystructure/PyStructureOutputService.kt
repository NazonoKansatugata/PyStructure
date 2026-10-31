package com.pystructure

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.project.Project
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.contentOrNull
import javax.swing.JTree
import javax.swing.JTextArea
import javax.swing.tree.DefaultMutableTreeNode
import javax.swing.tree.DefaultTreeModel

@Service(Service.Level.PROJECT)
class PyStructureOutputService(private val project: Project) {
    @Volatile
    private var treeModel: DefaultTreeModel? = null

    @Volatile
    private var statusArea: JTextArea? = null

    @Volatile
    private var graphPanel: DependencyGraphPanel? = null

    fun attach(tree: JTree, status: JTextArea, graph: DependencyGraphPanel) {
        treeModel = tree.model as DefaultTreeModel
        statusArea = status
        graphPanel = graph
    }

    fun showJson(stdout: String, projectBasePath: String, command: String) {
        ApplicationManager.getApplication().invokeLater {
            try {
                val root = parseAnalysis(stdout, projectBasePath, command)
                treeModel?.setRoot(root)
                treeModel?.reload()
                statusArea?.text = "PyStructure analysis completed"
            } catch (error: Exception) {
                showFailure("PyStructure CLI JSON の解析に失敗しました: ${error.message ?: error::class.java.simpleName}")
            }
        }
    }

    fun showFailure(text: String) {
        ApplicationManager.getApplication().invokeLater {
            val root = DefaultMutableTreeNode("PyStructure analysis failed")
            root.add(DefaultMutableTreeNode(text))
            treeModel?.setRoot(root)
            treeModel?.reload()
            statusArea?.text = text
        }
    }

    private fun parseAnalysis(stdout: String, projectBasePath: String, command: String): DefaultMutableTreeNode {
        val json = Json { ignoreUnknownKeys = true }
        val payload = json.parseToJsonElement(stdout).jsonObject
        val analysis = payload["analysis"]?.jsonObject ?: JsonObject(emptyMap())
        val graph = payload["graph"]?.jsonObject ?: JsonObject(emptyMap())
        val graphNodes = graph["nodes"]?.jsonArray.orEmpty().mapNotNull { element ->
            val node = element.jsonObject
            if (node["kind"]?.jsonPrimitive?.contentOrNull != "module") return@mapNotNull null
            val metrics = node["metrics"]?.jsonObject
            DependencyGraphNode(
                id = node["id"]?.jsonPrimitive?.contentOrNull ?: return@mapNotNull null,
                label = node["label"]?.jsonPrimitive?.contentOrNull ?: "(module)",
                path = node["path"]?.jsonPrimitive?.contentOrNull.orEmpty(),
                inCycle = metrics?.get("in_cycle")?.jsonPrimitive?.booleanOrNull ?: false,
                unreachable = metrics?.get("unreachable")?.jsonPrimitive?.booleanOrNull ?: false,
                isEntry = metrics?.get("is_entry")?.jsonPrimitive?.booleanOrNull ?: false,
                lineCount = metrics?.get("line_count")?.jsonPrimitive?.intOrNull ?: 0,
                sizeBytes = metrics?.get("size_bytes")?.jsonPrimitive?.intOrNull ?: 0,
                fanIn = metrics?.get("fan_in")?.jsonPrimitive?.intOrNull ?: 0,
                fanOut = metrics?.get("fan_out")?.jsonPrimitive?.intOrNull ?: 0,
                depth = metrics?.get("depth")?.jsonPrimitive?.intOrNull,
            )
        }
        val graphEdges = graph["edges"]?.jsonArray.orEmpty().mapNotNull { element ->
            val edge = element.jsonObject
            if (edge["kind"]?.jsonPrimitive?.contentOrNull != "imports") return@mapNotNull null
            val source = edge["source"]?.jsonPrimitive?.contentOrNull ?: return@mapNotNull null
            val target = edge["target"]?.jsonPrimitive?.contentOrNull ?: return@mapNotNull null
            DependencyGraphEdge(source, target)
        }
        graphPanel?.setGraph(graphNodes, graphEdges)

        val root = DefaultMutableTreeNode("PyStructure analysis completed")
        root.add(DefaultMutableTreeNode("Project: $projectBasePath"))
        root.add(DefaultMutableTreeNode("Command: $command"))

        val analysisNode = DefaultMutableTreeNode("Analysis")
        analysisNode.add(DefaultMutableTreeNode("Root: ${analysis["root"]?.jsonPrimitive?.contentOrNull ?: "(unknown)"}"))

        val modulesNode = DefaultMutableTreeNode("Modules")
        analysis["modules"]?.jsonArray?.forEach { moduleElement ->
            modulesNode.add(buildModuleNode(moduleElement.jsonObject))
        }
        analysisNode.add(modulesNode)

        analysisNode.add(DefaultMutableTreeNode("Nodes: ${graph["nodes"]?.jsonArray?.size ?: 0}"))
        analysisNode.add(DefaultMutableTreeNode("Edges: ${graph["edges"]?.jsonArray?.size ?: 0}"))
        root.add(analysisNode)
        return root
    }

    private fun buildModuleNode(module: JsonObject): DefaultMutableTreeNode {
        val moduleName = module["module_name"]?.jsonPrimitive?.contentOrNull ?: "(module)"
        val moduleNode = DefaultMutableTreeNode(moduleName)

        val importsNode = DefaultMutableTreeNode("Imports")
        module["imports"]?.jsonArray?.forEach { importElement ->
            val importObject = importElement.jsonObject
            val source = importObject["module"]?.jsonPrimitive?.contentOrNull ?: "(absolute)"
            val bindings = importObject["bindings"]?.jsonArray?.joinToString(", ") { bindingElement ->
                val binding = bindingElement.jsonObject
                val name = binding["name"]?.jsonPrimitive?.contentOrNull ?: "?"
                val asname = binding["asname"]?.jsonPrimitive?.contentOrNull
                if (asname.isNullOrBlank()) name else "$name as $asname"
            }.orEmpty()
            importsNode.add(DefaultMutableTreeNode("$source: $bindings"))
        }
        moduleNode.add(importsNode)

        val classesNode = DefaultMutableTreeNode("Classes")
        module["classes"]?.jsonArray?.forEach { classElement ->
            val classObject = classElement.jsonObject
            val className = classObject["name"]?.jsonPrimitive?.contentOrNull ?: "(class)"
            val classNode = DefaultMutableTreeNode(className)
            classObject["methods"]?.jsonArray?.forEach { methodElement ->
                val method = methodElement.jsonObject
                val kind = method["kind"]?.jsonPrimitive?.contentOrNull ?: "method"
                val name = method["name"]?.jsonPrimitive?.contentOrNull ?: "?"
                classNode.add(DefaultMutableTreeNode("$kind $name"))
            }
            classesNode.add(classNode)
        }
        moduleNode.add(classesNode)

        val functionsNode = DefaultMutableTreeNode("Functions")
        module["functions"]?.jsonArray?.forEach { functionElement ->
            val function = functionElement.jsonObject
            val kind = function["kind"]?.jsonPrimitive?.contentOrNull ?: "function"
            val name = function["name"]?.jsonPrimitive?.contentOrNull ?: "?"
            functionsNode.add(DefaultMutableTreeNode("$kind $name"))
        }
        moduleNode.add(functionsNode)

        val callsNode = DefaultMutableTreeNode("Calls")
        module["calls"]?.jsonArray?.forEach { callElement ->
            val call = callElement.jsonObject
            val caller = call["caller"]?.jsonPrimitive?.contentOrNull ?: "?"
            val callee = call["resolved_callee"]?.jsonPrimitive?.contentOrNull
                ?: call["callee"]?.jsonPrimitive?.contentOrNull
                ?: "?"
            callsNode.add(DefaultMutableTreeNode("$caller -> $callee"))
        }
        moduleNode.add(callsNode)

        return moduleNode
    }

    companion object {
        fun getInstance(project: Project): PyStructureOutputService = project.getService(PyStructureOutputService::class.java)
    }
}
