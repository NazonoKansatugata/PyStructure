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
import java.awt.event.MouseMotionAdapter
import javax.swing.JButton
import javax.swing.JComboBox
import javax.swing.JLabel
import javax.swing.JPanel
import javax.swing.JTextField
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt
import kotlin.random.Random

data class DependencyGraphNode(
    val id: String,
    val label: String,
    val path: String,
    val inCycle: Boolean,
    val unreachable: Boolean,
    val isEntry: Boolean,
    val lineCount: Int = 0,
    val sizeBytes: Int = 0,
    val fanIn: Int = 0,
    val fanOut: Int = 0,
    val depth: Int? = null,
)

data class DependencyGraphEdge(val source: String, val target: String)

enum class ColorMode(private val label: String, val legend: String) {
    STATUS("Color: status", "Module: blue  Cycle: red  Unreachable: gray  Entry: yellow ring"),
    PACKAGE("Color: package", "Top-level package (hue)  Entry: yellow ring"),
    DEPTH("Color: depth", "Near entry: light  Deep: dark  Unreachable: gray  Entry: yellow ring");

    override fun toString(): String = label
}

class DependencyGraphPanel(
    private val openFile: (String) -> Unit,
) : JPanel(BorderLayout()) {
    private val searchField = JTextField()
    private val canvas = GraphCanvas(openFile)
    private val legendLabel = JLabel()
    private val colorSelect = JComboBox(ColorMode.entries.toTypedArray())

    init {
        val toolbar = JPanel().apply {
            add(searchField)
            add(colorSelect)
            add(JButton("Fit").apply { addActionListener { canvas.fitGraph() } })
            add(JButton("Re-layout").apply { addActionListener { canvas.resetLayout() } })
            add(legendLabel)
        }
        colorSelect.addActionListener {
            val mode = colorSelect.selectedItem as ColorMode
            canvas.setColorMode(mode)
            legendLabel.text = mode.legend
        }
        legendLabel.text = ColorMode.STATUS.legend
        canvas.addKeyListener(object : java.awt.event.KeyAdapter() {
            override fun keyPressed(event: java.awt.event.KeyEvent) {
                if (event.keyCode == java.awt.event.KeyEvent.VK_ESCAPE) {
                    searchField.text = ""
                    canvas.clearSelection()
                }
            }
        })
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

    fun highlightModules(moduleNames: List<String>) {
        canvas.highlightModules(moduleNames)
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
    private var colorMode = ColorMode.STATUS
    private var scale = 1.0
    private var offsetX = 0.0
    private var offsetY = 0.0
    private var fitPending = false
    private var draggedNode: PositionedNode? = null
    private var selectedNodeId: String? = null
    private var highlightedIds: Set<String> = emptySet()
    private var hoveredNodeId: String? = null
    private var neighbors = emptyMap<String, Set<String>>()
    private var lastMouseX = 0
    private var lastMouseY = 0
    private var panning = false

    init {
        background = Color(0x1E, 0x1E, 0x1E)
        preferredSize = Dimension(640, 480)
        isFocusable = true
        toolTipText = ""
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
                val node = findNodeAt(event.x, event.y)
                if (event.clickCount == 2) {
                    node?.data?.path?.takeIf(String::isNotBlank)?.let(openFile)
                } else {
                    selectedNodeId = node?.data?.id?.takeIf { it != selectedNodeId }
                    repaint()
                }
            }
        })
        addMouseMotionListener(object : MouseMotionAdapter() {
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
                val node = findNodeAt(event.x, event.y)
                val nodeId = node?.data?.id
                if (hoveredNodeId != nodeId) {
                    hoveredNodeId = nodeId
                    repaint()
                }
                cursor = if (node != null) {
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
        neighbors = nodes.associate { node ->
            node.data.id to buildSet {
                edges.forEach { edge ->
                    if (edge.source == node.data.id) add(edge.target)
                    if (edge.target == node.data.id) add(edge.source)
                }
            }
        }
        selectedNodeId = null
        highlightedIds = emptySet()
        hoveredNodeId = null
        fitPending = true
        if (width > 0 && height > 0) fitGraph()
        repaint()
    }

    fun setFilter(value: String) {
        filter = value.lowercase()
        repaint()
    }

    fun setColorMode(mode: ColorMode) {
        colorMode = mode
        repaint()
    }

    fun clearSelection() {
        selectedNodeId = null
        highlightedIds = emptySet()
        repaint()
    }

    // 助言の対象モジュールを強調する。ノード ID は "module::<モジュール名>"。
    fun highlightModules(moduleNames: List<String>) {
        val wanted = moduleNames.mapTo(HashSet()) { "module::$it" }
        selectedNodeId = null
        highlightedIds = nodes.map { it.data.id }.filterTo(HashSet()) { it in wanted }
        repaint()
    }

    fun resetLayout() {
        if (nodes.isEmpty()) return

        val random = Random(System.nanoTime())
        val initialRadius = 45.0 * sqrt(nodes.size.toDouble())
        nodes.forEach { node ->
            val angle = random.nextDouble() * 2 * Math.PI
            val radius = initialRadius * sqrt(random.nextDouble())
            node.x = kotlin.math.cos(angle) * radius
            node.y = kotlin.math.sin(angle) * radius
        }

        if (nodes.size <= MAX_FORCE_LAYOUT_NODES) {
            runForceLayout()
        }
        fitGraph()
    }

    override fun getToolTipText(event: MouseEvent): String? {
        val node = findNodeAt(event.x, event.y)?.data ?: return null
        val depth = node.depth?.toString() ?: "unreachable"
        val state = listOfNotNull(
            "cycle".takeIf { node.inCycle },
            "entry point".takeIf { node.isEntry },
        ).joinToString(", ").ifEmpty { "normal" }
        return "<html><b>${escapeHtml(node.label)}</b><br>" +
            "${escapeHtml(node.path)}<br>" +
            "Lines: ${node.lineCount} &nbsp; Size: ${node.sizeBytes} B<br>" +
            "Fan-in: ${node.fanIn} &nbsp; Fan-out: ${node.fanOut}<br>" +
            "Depth: $depth &nbsp; Status: $state</html>"
    }

    private fun runForceLayout() {
        val positions = nodes.associate { it.data.id to it }
        val iterations = 100
        for (iteration in 0 until iterations) {
            val forces = nodes.associate { it.data.id to (0.0 to 0.0) }.toMutableMap()

            for (i in nodes.indices) {
                val first = nodes[i]
                for (j in i + 1 until nodes.size) {
                    val second = nodes[j]
                    var dx = second.x - first.x
                    var dy = second.y - first.y
                    var distanceSquared = dx * dx + dy * dy
                    if (distanceSquared < 0.01) {
                        dx = 0.1
                        dy = 0.1
                        distanceSquared = 0.02
                    }
                    val distance = sqrt(distanceSquared)
                    val force = 1800.0 / distanceSquared
                    val fx = dx / distance * force
                    val fy = dy / distance * force
                    val firstForce = forces.getValue(first.data.id)
                    val secondForce = forces.getValue(second.data.id)
                    forces[first.data.id] = (firstForce.first - fx) to (firstForce.second - fy)
                    forces[second.data.id] = (secondForce.first + fx) to (secondForce.second + fy)
                }
            }

            edges.forEach { edge ->
                val source = positions[edge.source] ?: return@forEach
                val target = positions[edge.target] ?: return@forEach
                val dx = target.x - source.x
                val dy = target.y - source.y
                val distance = sqrt(dx * dx + dy * dy).coerceAtLeast(0.01)
                val force = (distance - LINK_DISTANCE) * 0.018
                val fx = dx / distance * force
                val fy = dy / distance * force
                val sourceForce = forces.getValue(source.data.id)
                val targetForce = forces.getValue(target.data.id)
                forces[source.data.id] = (sourceForce.first + fx) to (sourceForce.second + fy)
                forces[target.data.id] = (targetForce.first - fx) to (targetForce.second - fy)
            }

            val temperature = 6.0 * (1.0 - iteration.toDouble() / iterations) + 0.15
            nodes.forEach { node ->
                val (forceX, forceY) = forces.getValue(node.data.id)
                val movementX = forceX - node.x * 0.004
                val movementY = forceY - node.y * 0.004
                val movement = sqrt(movementX * movementX + movementY * movementY)
                val scale = if (movement > temperature) temperature / movement else 1.0
                node.x += movementX * scale
                node.y += movementY * scale
            }
        }
    }

    fun fitGraph() {
        if (nodes.isEmpty() || width <= 0 || height <= 0) {
            fitPending = true
            return
        }
        val extentX = nodes.maxOf { kotlin.math.abs(it.x) } + NODE_RADIUS
        val extentY = nodes.maxOf { kotlin.math.abs(it.y) } + NODE_RADIUS
        scale = min((width - 48.0) / (extentX * 2), (height - 48.0) / (extentY * 2)).coerceIn(0.05, 2.0)
        offsetX = 0.0
        offsetY = 0.0
        fitPending = false
        repaint()
    }

    override fun paintComponent(graphics: Graphics) {
        super.paintComponent(graphics)
        val g = graphics.create() as Graphics2D
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON)
        val visibleNodes = nodes
        val byId = nodes.associateBy { it.data.id }
        val selected = selectedNodeId
        val activeIds: Set<String>? = when {
            selected != null -> setOf(selected) + neighbors[selected].orEmpty()
            highlightedIds.isNotEmpty() -> highlightedIds
            filter.isNotEmpty() -> nodes.filter { matchesFilter(it.data) }.mapTo(HashSet()) { it.data.id }
            else -> null
        }

        edges.forEach { edge ->
            val source = byId[edge.source] ?: return@forEach
            val target = byId[edge.target] ?: return@forEach
            val start = screenPoint(source)
            val end = screenPoint(target)
            val isSelectedEdge = edge.source == selected || edge.target == selected
            val isVisible = when {
                activeIds == null -> true
                selected != null -> isSelectedEdge
                else -> edge.source in activeIds && edge.target in activeIds
            }
            g.stroke = BasicStroke(if (isSelectedEdge) 2.5f else 1.2f)
            g.color = when {
                !isVisible -> Color(0x68, 0x75, 0x82, 25)
                isSelectedEdge -> Color(0xF0, 0xB4, 0x29, 230)
                else -> Color(0x68, 0x75, 0x82, 150)
            }
            g.drawLine(start.first, start.second, end.first, end.second)
            drawArrow(g, start.first, start.second, end.first, end.second, screenRadius(target))
        }

        val showAllLabels = nodes.size <= 80 || scale >= 1.2
        g.font = Font(Font.SANS_SERIF, Font.PLAIN, 12)
        visibleNodes.forEach { node ->
            val (x, y) = screenPoint(node)
            val radius = screenRadius(node)
            val isSelected = node.data.id == selected
            val isActive = activeIds == null || node.data.id in activeIds
            g.color = nodeColor(node.data, if (isActive) 255 else 45)
            g.fillOval(x - radius, y - radius, radius * 2, radius * 2)
            if (node.data.isEntry) {
                g.color = Color(0xF0, 0xB4, 0x29, if (isActive) 255 else 45)
                g.stroke = BasicStroke(3.0f)
                g.drawOval(x - radius, y - radius, radius * 2, radius * 2)
            }
            if (isSelected || node.data.id == hoveredNodeId) {
                g.color = if (isSelected) Color(0xFF, 0xFF, 0xFF) else Color(0xF0, 0xF0, 0xF0)
                g.stroke = BasicStroke(2.0f)
                g.drawOval(x - radius, y - radius, radius * 2, radius * 2)
            }
            val showLabel = isActive && (showAllLabels || node.data.id == hoveredNodeId || activeIds != null)
            if (showLabel) {
                g.color = Color(0xF0, 0xF0, 0xF0, 230)
                g.drawString(node.data.label, x + radius + 5, y + 4)
            }
        }

        g.color = Color(0xC0, 0xC0, 0xC0)
        val cycles = nodes.count { it.data.inCycle }
        val unreachable = nodes.count { it.data.unreachable }
        g.drawString("${nodes.size} modules | ${edges.size} imports | $cycles in cycles | $unreachable unreachable", 12, height - 14)
        if (nodes.isEmpty()) {
            g.drawString("No modules to display.", 20, 32)
        }
        g.dispose()
    }

    private fun matchesFilter(node: DependencyGraphNode): Boolean =
        filter.isEmpty() || node.label.lowercase().contains(filter) || node.path.lowercase().contains(filter)

    private fun nodeColor(node: DependencyGraphNode, alpha: Int): Color = when (colorMode) {
        ColorMode.PACKAGE -> hsl(hueOf(node.label.substringBefore('.')), 0.6, 0.55, alpha)
        ColorMode.DEPTH -> {
            val depth = node.depth
            if (depth == null) {
                Color(0x8B, 0x94, 0x9E, alpha)
            } else {
                hsl(210, 0.7, (72 - min(depth, 8) / 8.0 * 36) / 100.0, alpha)
            }
        }
        ColorMode.STATUS -> when {
            node.inCycle -> Color(0xE5, 0x53, 0x4B, alpha)
            node.unreachable -> Color(0x8B, 0x94, 0x9E, alpha)
            else -> Color(0x4C, 0x8D, 0xFF, alpha)
        }
    }

    private fun hueOf(text: String): Int {
        var hash = 0
        for (ch in text) hash = (hash * 31 + ch.code) % 360
        return hash
    }

    private fun hsl(hue: Int, saturation: Double, lightness: Double, alpha: Int): Color {
        val c = (1 - kotlin.math.abs(2 * lightness - 1)) * saturation
        val x = c * (1 - kotlin.math.abs((hue / 60.0) % 2 - 1))
        val m = lightness - c / 2
        val (r, g, b) = when (hue / 60) {
            0 -> Triple(c, x, 0.0)
            1 -> Triple(x, c, 0.0)
            2 -> Triple(0.0, c, x)
            3 -> Triple(0.0, x, c)
            4 -> Triple(x, 0.0, c)
            else -> Triple(c, 0.0, x)
        }
        fun channel(value: Double) = ((value + m) * 255).toInt().coerceIn(0, 255)
        return Color(channel(r), channel(g), channel(b), alpha)
    }

    private fun worldRadius(node: PositionedNode): Double =
        max(6.0, min(26.0, 4 + sqrt(node.data.lineCount.toDouble()) * 0.6))

    private fun screenRadius(node: PositionedNode): Int = max(6, (worldRadius(node) * scale).toInt())

    private fun escapeHtml(value: String): String =
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    private fun screenPoint(node: PositionedNode): Pair<Int, Int> =
        (width / 2.0 + offsetX + node.x * scale).toInt() to
            (height / 2.0 + offsetY + node.y * scale).toInt()

    private fun findNodeAt(x: Int, y: Int): PositionedNode? {
        return nodes.asReversed().firstOrNull { node ->
            val radius = screenRadius(node) + 4
            val point = screenPoint(node)
            val dx = x - point.first
            val dy = y - point.second
            dx * dx + dy * dy <= radius * radius
        }
    }

    private fun zoomAt(event: MouseWheelEvent) {
        val oldScale = scale
        val newScale = (scale * if (event.preciseWheelRotation < 0) 1.1 else 0.9).coerceIn(0.05, 4.0)
        val centerX = width / 2.0 + offsetX
        val centerY = height / 2.0 + offsetY
        offsetX = event.x - (event.x - centerX) * newScale / oldScale - width / 2.0
        offsetY = event.y - (event.y - centerY) * newScale / oldScale - height / 2.0
        scale = newScale
        repaint()
    }

    private fun drawArrow(g: Graphics2D, x1: Int, y1: Int, x2: Int, y2: Int, targetRadius: Int) {
        val angle = kotlin.math.atan2((y2 - y1).toDouble(), (x2 - x1).toDouble())
        val tipX = x2 - (targetRadius * kotlin.math.cos(angle)).toInt()
        val tipY = y2 - (targetRadius * kotlin.math.sin(angle)).toInt()
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
        private const val LINK_DISTANCE = 85.0
        private const val MAX_FORCE_LAYOUT_NODES = 250
    }
}
