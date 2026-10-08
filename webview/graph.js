/* PyStructure dependency graph (IDE-agnostic). Host injects `onOpen` and calls `setData(payload)`. */
(function (global) {
  'use strict';

  const COLORS = { cycle: '#e5534b', unreachable: '#8b949e', normal: '#4c8dff', entry: '#f0b429' };
  const LINK_DISTANCE = 80;
  const REPULSION = 2600;
  const MIN_ALPHA = 0.005;

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function hueOf(text) {
    let hash = 0;
    for (const ch of text) hash = (hash * 31 + ch.charCodeAt(0)) % 360;
    return hash;
  }

  function mount(container, options) {
    const host = Object.assign({ onOpen() {} }, options);
    container.classList.add('ps-graph');
    container.textContent = '';

    const toolbar = el('div', 'ps-toolbar');
    const search = el('input', 'ps-search');
    search.type = 'search';
    search.placeholder = 'Search module';
    const colorSelect = el('select', 'ps-select');
    [['status', 'Color: status'], ['package', 'Color: package'], ['depth', 'Color: depth']].forEach(([value, label]) => {
      const option = el('option', '', label);
      option.value = value;
      colorSelect.appendChild(option);
    });
    const fitButton = el('button', 'ps-button', 'Fit');
    const relayoutButton = el('button', 'ps-button', 'Re-layout');
    const stats = el('span', 'ps-stats');
    toolbar.append(search, colorSelect, fitButton, relayoutButton, stats);

    const legend = el('div', 'ps-legend');
    const canvas = el('canvas', 'ps-canvas');
    const tooltip = el('div', 'ps-tooltip');
    tooltip.hidden = true;
    const empty = el('div', 'ps-empty', 'No modules to display.');
    empty.hidden = true;
    container.append(toolbar, canvas, legend, tooltip, empty);

    const ctx = canvas.getContext('2d');
    let nodes = [];
    let links = [];
    let byId = new Map();
    let neighbors = new Map();
    let view = { x: 0, y: 0, k: 1 };
    let alpha = 0;
    let frame = 0;
    let selected = null;
    let hovered = null;
    let query = '';
    let colorMode = 'status';
    let drag = null;
    let pan = null;
    let dpr = window.devicePixelRatio || 1;

    function schedule() {
      if (!frame) frame = requestAnimationFrame(step);
    }

    function step() {
      frame = 0;
      if (alpha > MIN_ALPHA) {
        tick();
        alpha *= 0.985;
      }
      draw();
      if (alpha > MIN_ALPHA) schedule();
    }

    function setData(payload) {
      const modules = payload.graph.nodes.filter((node) => node.kind === 'module');
      byId = new Map();
      nodes = modules.map((node, index) => {
        const metrics = node.metrics || {};
        const angle = index * 2.399963;
        const radius = 30 * Math.sqrt(index + 1);
        const item = {
          id: node.id,
          label: node.label,
          path: node.path,
          metrics,
          x: Math.cos(angle) * radius,
          y: Math.sin(angle) * radius,
          vx: 0,
          vy: 0,
          fixed: false,
          r: Math.max(6, Math.min(26, 4 + Math.sqrt(metrics.line_count || 0) * 0.6)),
        };
        byId.set(item.id, item);
        return item;
      });

      neighbors = new Map(nodes.map((node) => [node.id, new Set()]));
      links = [];
      for (const edge of payload.graph.edges) {
        if (edge.kind !== 'imports') continue;
        const source = byId.get(edge.source);
        const target = byId.get(edge.target);
        if (!source || !target) continue;
        links.push({ source, target });
        neighbors.get(source.id).add(target.id);
        neighbors.get(target.id).add(source.id);
      }

      selected = null;
      hovered = null;
      empty.hidden = nodes.length > 0;
      const cycles = nodes.filter((node) => node.metrics.in_cycle).length;
      const unreachable = nodes.filter((node) => node.metrics.unreachable).length;
      const skipped = (payload.analysis.skipped || []).length;
      stats.textContent = `${nodes.length} modules / ${links.length} imports / ${cycles} in cycles / ${unreachable} unreachable` + (skipped ? ` / ${skipped} skipped` : '');
      relayout();
    }

    function relayout() {
      alpha = 1;
      const warmup = nodes.length > 800 ? 30 : 150;
      for (let i = 0; i < warmup; i++) {
        tick();
        alpha *= 0.985;
      }
      alpha = Math.max(alpha, 0.05);
      resize();
      fit();
      schedule();
    }

    function tick() {
      const count = nodes.length;
      for (let i = 0; i < count; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < count; j++) {
          const b = nodes[j];
          let dx = b.x - a.x;
          let dy = b.y - a.y;
          let d2 = dx * dx + dy * dy;
          if (d2 === 0) {
            dx = 0.01;
            dy = 0.01;
            d2 = 0.0002;
          }
          const d = Math.sqrt(d2);
          const push = (REPULSION * alpha) / (d2 + 25);
          const overlap = a.r + b.r + 4 - d;
          const extra = overlap > 0 ? overlap * 0.2 : 0;
          const fx = (dx / d) * (push + extra);
          const fy = (dy / d) * (push + extra);
          a.vx -= fx;
          a.vy -= fy;
          b.vx += fx;
          b.vy += fy;
        }
      }
      for (const link of links) {
        const dx = link.target.x - link.source.x;
        const dy = link.target.y - link.source.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const pull = (d - LINK_DISTANCE) * 0.04 * alpha;
        const fx = (dx / d) * pull;
        const fy = (dy / d) * pull;
        link.source.vx += fx;
        link.source.vy += fy;
        link.target.vx -= fx;
        link.target.vy -= fy;
      }
      for (const node of nodes) {
        node.vx -= node.x * 0.01 * alpha;
        node.vy -= node.y * 0.01 * alpha;
        if (node.fixed) {
          node.vx = 0;
          node.vy = 0;
          continue;
        }
        node.vx *= 0.6;
        node.vy *= 0.6;
        node.x += node.vx;
        node.y += node.vy;
      }
    }

    function resize() {
      dpr = window.devicePixelRatio || 1;
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      canvas.width = Math.max(1, Math.floor(width * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));
    }

    function fit() {
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (nodes.length === 0 || width === 0 || height === 0) return;
      let minX = Infinity;
      let minY = Infinity;
      let maxX = -Infinity;
      let maxY = -Infinity;
      for (const node of nodes) {
        minX = Math.min(minX, node.x - node.r);
        minY = Math.min(minY, node.y - node.r);
        maxX = Math.max(maxX, node.x + node.r);
        maxY = Math.max(maxY, node.y + node.r);
      }
      const k = Math.min((width - 80) / Math.max(maxX - minX, 1), (height - 80) / Math.max(maxY - minY, 1), 2);
      view.k = Math.max(0.05, k);
      view.x = width / 2 - ((minX + maxX) / 2) * view.k;
      view.y = height / 2 - ((minY + maxY) / 2) * view.k;
      schedule();
    }

    function colorOf(node) {
      const metrics = node.metrics;
      if (colorMode === 'package') return `hsl(${hueOf(node.label.split('.')[0])}, 60%, 55%)`;
      if (colorMode === 'depth') {
        if (metrics.depth === null || metrics.depth === undefined) return COLORS.unreachable;
        return `hsl(210, 70%, ${72 - (Math.min(metrics.depth, 8) / 8) * 36}%)`;
      }
      if (metrics.in_cycle) return COLORS.cycle;
      if (metrics.unreachable) return COLORS.unreachable;
      return COLORS.normal;
    }

    function renderLegend() {
      legend.textContent = '';
      const rows =
        colorMode === 'package'
          ? [['hsl(210, 60%, 55%)', 'Top-level package (hue)']]
          : colorMode === 'depth'
            ? [['hsl(210, 70%, 72%)', 'Near entry'], ['hsl(210, 70%, 36%)', 'Deep'], [COLORS.unreachable, 'Unreachable']]
            : [[COLORS.normal, 'Module'], [COLORS.cycle, 'In import cycle'], [COLORS.unreachable, 'Unreachable']];
      rows.push([COLORS.entry, 'Entry point (ring)']);
      for (const [color, label] of rows) {
        const row = el('div', 'ps-legend-row');
        const swatch = el('span', 'ps-swatch');
        swatch.style.background = color;
        row.append(swatch, el('span', '', label));
        legend.appendChild(row);
      }
      legend.appendChild(el('div', 'ps-legend-note', 'Size = lines. Double-click opens file.'));
    }

    function activeSet() {
      if (selected) return new Set([selected.id, ...neighbors.get(selected.id)]);
      if (query) return new Set(nodes.filter((node) => node.label.toLowerCase().includes(query)).map((node) => node.id));
      return null;
    }

    function draw() {
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      const foreground = getComputedStyle(container).color || '#ccc';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      ctx.translate(view.x, view.y);
      ctx.scale(view.k, view.k);

      const active = activeSet();
      ctx.lineWidth = 1 / view.k;
      for (const link of links) {
        const incident = selected && (link.source === selected || link.target === selected);
        const visible = !active || (selected ? incident : active.has(link.source.id) && active.has(link.target.id));
        ctx.globalAlpha = visible ? (incident ? 0.9 : 0.35) : 0.05;
        ctx.strokeStyle = incident ? COLORS.entry : foreground;
        ctx.fillStyle = ctx.strokeStyle;
        const dx = link.target.x - link.source.x;
        const dy = link.target.y - link.source.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 1;
        const ux = dx / d;
        const uy = dy / d;
        const startX = link.source.x + ux * link.source.r;
        const startY = link.source.y + uy * link.source.r;
        const endX = link.target.x - ux * link.target.r;
        const endY = link.target.y - uy * link.target.r;
        ctx.beginPath();
        ctx.moveTo(startX, startY);
        ctx.lineTo(endX, endY);
        ctx.stroke();
        const head = 6 / Math.max(view.k, 0.5);
        ctx.beginPath();
        ctx.moveTo(endX, endY);
        ctx.lineTo(endX - ux * head - uy * head * 0.5, endY - uy * head + ux * head * 0.5);
        ctx.lineTo(endX - ux * head + uy * head * 0.5, endY - uy * head - ux * head * 0.5);
        ctx.closePath();
        ctx.fill();
      }

      const showAllLabels = nodes.length <= 80 || view.k >= 1.2;
      ctx.font = `${11 / view.k}px sans-serif`;
      ctx.textAlign = 'center';
      for (const node of nodes) {
        const dimmed = active && !active.has(node.id);
        ctx.globalAlpha = dimmed ? 0.15 : 1;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
        ctx.fillStyle = colorOf(node);
        ctx.fill();
        if (node.metrics.is_entry) {
          ctx.strokeStyle = COLORS.entry;
          ctx.lineWidth = 3 / view.k;
          ctx.stroke();
        }
        if (node === selected || node === hovered) {
          ctx.strokeStyle = foreground;
          ctx.lineWidth = 2 / view.k;
          ctx.stroke();
        }
        if (!dimmed && (showAllLabels || node === hovered || (active && active.has(node.id)))) {
          ctx.fillStyle = foreground;
          ctx.fillText(node.label, node.x, node.y + node.r + 12 / view.k);
        }
      }
      ctx.globalAlpha = 1;
    }

    function toWorld(event) {
      const rect = canvas.getBoundingClientRect();
      return { x: (event.clientX - rect.left - view.x) / view.k, y: (event.clientY - rect.top - view.y) / view.k };
    }

    function hit(point) {
      for (let i = nodes.length - 1; i >= 0; i--) {
        const node = nodes[i];
        const dx = point.x - node.x;
        const dy = point.y - node.y;
        const radius = node.r + 2 / view.k;
        if (dx * dx + dy * dy <= radius * radius) return node;
      }
      return null;
    }

    function showTooltip(node, event) {
      if (!node) {
        tooltip.hidden = true;
        return;
      }
      const m = node.metrics;
      tooltip.textContent = [
        node.label,
        `lines: ${m.line_count}  size: ${m.size_bytes} B`,
        `fan-in: ${m.fan_in}  fan-out: ${m.fan_out}`,
        `depth: ${m.depth === null || m.depth === undefined ? 'unreachable' : m.depth}${m.in_cycle ? '  (in cycle)' : ''}${m.is_entry ? '  (entry)' : ''}`,
      ].join('\n');
      const rect = container.getBoundingClientRect();
      tooltip.style.left = `${event.clientX - rect.left + 14}px`;
      tooltip.style.top = `${event.clientY - rect.top + 14}px`;
      tooltip.hidden = false;
    }

    canvas.addEventListener('mousedown', (event) => {
      const node = hit(toWorld(event));
      if (node) {
        drag = { node, moved: false };
        node.fixed = true;
      } else {
        pan = { startX: event.clientX, startY: event.clientY, viewX: view.x, viewY: view.y, moved: false };
      }
    });

    window.addEventListener('mousemove', (event) => {
      if (drag) {
        const point = toWorld(event);
        drag.node.x = point.x;
        drag.node.y = point.y;
        drag.moved = true;
        alpha = Math.max(alpha, 0.2);
        schedule();
      } else if (pan) {
        const dx = event.clientX - pan.startX;
        const dy = event.clientY - pan.startY;
        if (Math.abs(dx) + Math.abs(dy) > 3) pan.moved = true;
        view.x = pan.viewX + dx;
        view.y = pan.viewY + dy;
        schedule();
      } else if (event.target === canvas) {
        const node = hit(toWorld(event));
        if (node !== hovered) {
          hovered = node;
          canvas.style.cursor = node ? 'pointer' : 'default';
          schedule();
        }
        showTooltip(node, event);
      }
    });

    window.addEventListener('mouseup', () => {
      if (drag) {
        drag.node.fixed = false;
        if (!drag.moved) {
          selected = selected === drag.node ? null : drag.node;
          schedule();
        }
      } else if (pan && !pan.moved) {
        selected = null;
        schedule();
      }
      drag = null;
      pan = null;
    });

    canvas.addEventListener('mouseleave', () => {
      hovered = null;
      tooltip.hidden = true;
      schedule();
    });

    canvas.addEventListener('dblclick', (event) => {
      const node = hit(toWorld(event));
      if (node) host.onOpen({ path: node.path, label: node.label });
    });

    canvas.addEventListener(
      'wheel',
      (event) => {
        event.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const px = event.clientX - rect.left;
        const py = event.clientY - rect.top;
        const k = Math.max(0.05, Math.min(4, view.k * Math.exp(-event.deltaY * 0.0015)));
        view.x = px - ((px - view.x) / view.k) * k;
        view.y = py - ((py - view.y) / view.k) * k;
        view.k = k;
        schedule();
      },
      { passive: false }
    );

    window.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        selected = null;
        search.value = '';
        query = '';
        schedule();
      }
    });

    search.addEventListener('input', () => {
      query = search.value.trim().toLowerCase();
      schedule();
    });
    colorSelect.addEventListener('change', () => {
      colorMode = colorSelect.value;
      renderLegend();
      schedule();
    });
    fitButton.addEventListener('click', fit);
    relayoutButton.addEventListener('click', () => {
      for (const node of nodes) {
        node.vx = 0;
        node.vy = 0;
      }
      relayout();
    });

    new ResizeObserver(() => {
      resize();
      schedule();
    }).observe(canvas);

    renderLegend();
    return { setData };
  }

  global.PyStructureGraph = { mount };
})(window);
