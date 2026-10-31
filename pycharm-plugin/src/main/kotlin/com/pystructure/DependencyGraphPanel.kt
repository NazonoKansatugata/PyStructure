package com.pystructure

import java.awt.BasicStroke
import java.awt.BorderLayout
import java.awt.Color
import java.awt.Dimension
import java.awt.Font
import java.awt.Graphics
import java.awt.Graphics2D
import java.awt.RenderingHints
import java.awt.event.MouseAdapter
import java.awt.event.MouseEvent
import java.awt.event.MouseWheelEvent
import javax.swing.JButton
import javax.swing.JLabel
import javax.swing.JPanel
import javax.swing.JTextField
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

data class DependencyGraphNode(
    val id: String,
    val label: String,
    val path: String,
    val inCycle: Boolean,
    val unreachable: Boolean,
    val isEntry: Boolean,
)

data class DependencyGraphEdge(val source: String, val target: String)

class DependencyGraphPanel(
    private val openFile: (String) -> Unit,
) : JPanel(BorderLayout()) {
    private val searchField = JTextField()
    private val canvas = GraphCanvas(openFile)

    init {
        val toolbar = JPanel().apply {
            add(searchField)
            add(JButton("Fit").apply { addActionListener { canvas.fitGraph() } })
            add(JButton("Re-layout").apply { addActionListener { canvas.resetLayout() } })
            add(JLabel("Cycle: red  Unreachable: gray  Entry: yellow  Module: blue"))
        }
        searchField.columns = 24
        searchField.toolTipText = "Search modules"
        searchField.document.addDocumentListener(object : javax.swing.event.DocumentListener {
            override fun insertUpdate(event: javax.swing.event.DocumentEvent) = updateFilter()
            override fun removeUpdate(event: javax.swing.event.DocumentEvent) = updateFilter()
            override fun changedUpdate(event: javax.swing.event.DocumentEvent) = updateFilter()
        })

        add(toolbar, BorderLayout.NORTH)
        add(canvas, BorderLayout.CENTER)
    }

    fun setGraph(nodes: List<DependencyGraphNode>, edges: List<DependencyGraphEdge>) {
        canvas.setGraph(nodes, edges)
    }

    private fun updateFilter() {
        canvas.setFilter(searchField.text.trim())
    }
}

private class GraphCanvas(
    private val openFile: (String) -> Unit,
) : JPanel() {
    private data class PositionedNode(val data: DependencyGraphNode, var x: Double, var y: Double)

    private val nodes = mutableListOf<PositionedNode>()
    private var edges = emptyList<DependencyGraphEdge>()
    private var filter = ""
    private var scale = 1.0
    private var offsetX = 0.0
    private var offsetY = 0.0
    private var fitPending = false
    private var draggedNode: PositionedNode? = null
    private var lastMouseX = 0
    private var lastMouseY = 0
    private var panning = false

    init {
        background = Color(0x1E, 0x1E, 0x1E)
        preferredSize = Dimension(640, 480)
        isFocusable = true
        addComponentListener(object : java.awt.event.ComponentAdapter() {
            override fun componentResized(event: java.awt.event.ComponentEvent) {
                if (fitPending) fitGraph()
            }
        })
        addMouseListener(object : MouseAdapter() {
            override fun mousePressed(event: MouseEvent) {
                requestFocusInWindow()
                lastMouseX = event.x
                lastMouseY = event.y
                draggedNode = findNodeAt(event.x, event.y)
                panning = draggedNode == null
            }

            override fun mouseReleased(event: MouseEvent) {
                draggedNode = null
                panning = false
            }

            override fun mouseClicked(event: MouseEvent) {
                if (event.clickCount == 2) {
                    findNodeAt(event.x, event.y)?.data?.path?.takeIf(String::isNotBlank)?.let(openFile)
                }
            }
        })
        addMouseMotionListener(object : MouseAdapter() {
            override fun mouseDragged(event: MouseEvent) {
                val deltaX = event.x - lastMouseX
                val deltaY = event.y - lastMouseY
                val node = draggedNode
                if (node != null) {
                    node.x += deltaX / scale
                    node.y += deltaY / scale
                } else if (panning) {
                    offsetX += deltaX
                    offsetY += deltaY
                }
                lastMouseX = event.x
                lastMouseY = event.y
                repaint()
            }

            override fun mouseMoved(event: MouseEvent) {
                cursor = if (findNodeAt(event.x, event.y) != null) {
                    java.awt.Cursor.getPredefinedCursor(java.awt.Cursor.HAND_CURSOR)
                } else {
                    java.awt.Cursor.getPredefinedCursor(java.awt.Cursor.DEFAULT_CURSOR)
                }
            }
        })
        addMouseWheelListener { event: MouseWheelEvent -> zoomAt(event) }
    }

    fun setGraph(graphNodes: List<DependencyGraphNode>, graphEdges: List<DependencyGraphEdge>) {
        nodes.clear()
        val radius = 35.0 * sqrt(graphNodes.size.toDouble().coerceAtLeast(1.0))
        graphNodes.forEachIndexed { index, node ->
            val angle = index * 2.399963229728653
            nodes.add(PositionedNode(node, kotlin.math.cos(angle) * radius, kotlin.math.sin(angle) * radius))
        }
        val nodeIds = nodes.mapTo(HashSet()) { it.data.id }
        edges = graphEdges.filter { it.source in nodeIds && it.target in nodeIds }
        fitPending = true
        if (width > 0 && height > 0) fitGraph()
        repaint()
    }

    fun setFilter(value: String) {
        filter = value.lowercase()
        repaint()
    }

    fun resetLayout() {
        val graphNodes = nodes.map { it.data }
        val radius = 35.0 * sqrt(graphNodes.size.toDouble().coerceAtLeast(1.0))
        nodes.forEachIndexed { index, node ->
            val angle = index * 2.399963229728653
            node.x = kotlin.math.cos(angle) * radius
            node.y = kotlin.math.sin(angle) * radius
        }
        fitGraph()
    }

    fun fitGraph() {
        if (nodes.isEmpty() || width <= 0 || height <= 0) {
            fitPending = true
            return
        }
        val extentX = nodes.maxOf { kotlin.math.abs(it.x) } + NODE_RADIUS
        val extentY = nodes.maxOf { kotlin.math.abs(it.y) } + NODE_RADIUS
        scale = min((width - 48.0) / (extentX * 2), (height - 48.0) / (extentY * 2)).coerceIn(0.1, 3.0)
        offsetX = 0.0
        offsetY = 0.0
        fitPending = false
        repaint()
    }

    override fun paintComponent(graphics: Graphics) {
        super.paintComponent(graphics)
        val g = graphics.create() as Graphics2D
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON)
        val visibleNodes = nodes.filter { matchesFilter(it.data) }
        val visibleIds = visibleNodes.mapTo(HashSet()) { it.data.id }
        val byId = nodes.associateBy { it.data.id }

        g.stroke = BasicStroke(1.2f)
        edges.forEach { edge ->
            if (edge.source !in visibleIds || edge.target !in visibleIds) return@forEach
            val source = byId[edge.source] ?: return@forEach
            val target = byId[edge.target] ?: return@forEach
            val start = screenPoint(source)
            val end = screenPoint(target)
            g.color = Color(0x68, 0x75, 0x82, 150)
            g.drawLine(start.first, start.second, end.first, end.second)
            drawArrow(g, start.first, start.second, end.first, end.second)
        }

        visibleNodes.forEach { node ->
            val (x, y) = screenPoint(node)
            val radius = max(6, (NODE_RADIUS * scale).toInt())
            g.color = nodeColor(node.data)
            g.fillOval(x - radius, y - radius, radius * 2, radius * 2)
            g.color = Color(0xF0, 0xF0, 0xF0)
            g.drawOval(x - radius, y - radius, radius * 2, radius * 2)
            g.font = Font(Font.SANS_SERIF, Font.PLAIN, 12)
            g.drawString(node.data.label, x + radius + 5, y + 4)
        }

        g.color = Color(0xC0, 0xC0, 0xC0)
        g.drawString("${visibleNodes.size} modules  |  ${edges.count { it.source in visibleIds && it.target in visibleIds }} imports", 12, height - 14)
        if (visibleNodes.isEmpty()) {
            g.color = Color(0xC0, 0xC0, 0xC0)
            g.drawString(if (nodes.isEmpty()) "No modules to display." else "No modules match the search.", 20, 32)
        }
        g.dispose()
    }

    private fun matchesFilter(node: DependencyGraphNode): Boolean =
        filter.isEmpty() || node.label.lowercase().contains(filter) || node.path.lowercase().contains(filter)

    private fun nodeColor(node: DependencyGraphNode): Color = when {
        node.inCycle -> Color(0xE5, 0x53, 0x4B)
        node.unreachable -> Color(0x8B, 0x94, 0x9E)
        node.isEntry -> Color(0xF0, 0xB4, 0x29)
        else -> Color(0x4C, 0x8D, 0xFF)
    }

    private fun screenPoint(node: PositionedNode): Pair<Int, Int> =
        (width / 2.0 + offsetX + node.x * scale).toInt() to
            (height / 2.0 + offsetY + node.y * scale).toInt()

    private fun findNodeAt(x: Int, y: Int): PositionedNode? {
        val radius = max(10, (NODE_RADIUS * scale).toInt() + 4)
        return nodes.asReversed().firstOrNull { node ->
            if (!matchesFilter(node.data)) return@firstOrNull false
            val point = screenPoint(node)
            val dx = x - point.first
            val dy = y - point.second
            dx * dx + dy * dy <= radius * radius
        }
    }

    private fun zoomAt(event: MouseWheelEvent) {
        val oldScale = scale
        val newScale = (scale * if (event.preciseWheelRotation < 0) 1.1 else 0.9).coerceIn(0.1, 4.0)
        val centerX = width / 2.0 + offsetX
        val centerY = height / 2.0 + offsetY
        offsetX = event.x - (event.x - centerX) * newScale / oldScale - width / 2.0
        offsetY = event.y - (event.y - centerY) * newScale / oldScale - height / 2.0
        scale = newScale
        repaint()
    }

    private fun drawArrow(g: Graphics2D, x1: Int, y1: Int, x2: Int, y2: Int) {
        val angle = kotlin.math.atan2((y2 - y1).toDouble(), (x2 - x1).toDouble())
        val tipX = x2 - (NODE_RADIUS * scale * kotlin.math.cos(angle)).toInt()
        val tipY = y2 - (NODE_RADIUS * scale * kotlin.math.sin(angle)).toInt()
        val arrowLength = 8.0
        val leftX = tipX - arrowLength * kotlin.math.cos(angle - 0.45)
        val leftY = tipY - arrowLength * kotlin.math.sin(angle - 0.45)
        val rightX = tipX - arrowLength * kotlin.math.cos(angle + 0.45)
        val rightY = tipY - arrowLength * kotlin.math.sin(angle + 0.45)
        g.drawLine(tipX, tipY, leftX.toInt(), leftY.toInt())
        g.drawLine(tipX, tipY, rightX.toInt(), rightY.toInt())
    }

    companion object {
        private const val NODE_RADIUS = 12.0
    }
}
