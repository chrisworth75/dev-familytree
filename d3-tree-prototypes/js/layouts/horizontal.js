/**
 * Horizontal Timeline Layout
 *
 * Displays family tree with:
 * - X axis = time (birth year)
 * - Card width = lifespan
 * - Y position = hierarchical layout
 *
 * Features:
 * - Zoom/pan
 * - Collapsible nodes
 * - Click to select
 * - Year markers
 */

import { getYearRange, countDescendants } from '../data-loader.js';

// Layout constants
const CONFIG = {
  cardHeight: 60,
  cardMinWidth: 120,
  cardMaxWidth: 200,
  yearWidth: 4,          // pixels per year
  verticalGap: 20,       // gap between cards
  horizontalPadding: 50,
  yearMarkerInterval: 25,
  animationDuration: 500,
};

/**
 * Create a horizontal timeline tree visualization
 * @param {HTMLElement} container - Container element
 * @param {Object} data - Tree data (hierarchical)
 * @param {Object} options - Configuration options
 */
export function createHorizontalTree(container, data, options = {}) {
  const config = { ...CONFIG, ...options };
  const { min: minYear, max: maxYear } = getYearRange(data);
  const currentYear = new Date().getFullYear();
  const yearRange = Math.max(maxYear, currentYear) - minYear + 20;

  // State
  let root = d3.hierarchy(data);
  let selectedNode = null;

  // Dimensions
  const width = container.clientWidth;
  const height = container.clientHeight;

  // Clear existing
  container.innerHTML = '';

  // Create SVG
  const svg = d3.select(container)
    .append('svg')
    .attr('class', 'tree')
    .attr('width', width)
    .attr('height', height);

  // Create zoom behavior
  const zoom = d3.zoom()
    .scaleExtent([0.2, 3])
    .on('zoom', (event) => {
      g.attr('transform', event.transform);
    });

  svg.call(zoom);

  // Main group for zoom/pan
  const g = svg.append('g')
    .attr('transform', `translate(${config.horizontalPadding}, ${height / 2})`);

  // Create layers
  const yearMarkersGroup = g.append('g').attr('class', 'year-markers');
  const linksGroup = g.append('g').attr('class', 'links');
  const nodesGroup = g.append('g').attr('class', 'nodes');

  // Scales
  const xScale = d3.scaleLinear()
    .domain([minYear - 10, Math.max(maxYear, currentYear) + 10])
    .range([0, yearRange * config.yearWidth]);

  // Draw year markers
  drawYearMarkers();

  // Initial layout
  updateLayout();

  // Public API
  return {
    update: updateLayout,
    reset: resetView,
    expandAll,
    collapseAll,
    getSelectedNode: () => selectedNode,
    onSelect: (callback) => { onSelectCallback = callback; },
  };

  // --- Private functions ---

  let onSelectCallback = null;

  function drawYearMarkers() {
    const startYear = Math.floor(minYear / config.yearMarkerInterval) * config.yearMarkerInterval;
    const endYear = Math.ceil(currentYear / config.yearMarkerInterval) * config.yearMarkerInterval;
    const years = [];

    for (let y = startYear; y <= endYear; y += config.yearMarkerInterval) {
      years.push(y);
    }

    const treeHeight = estimateTreeHeight(root);

    yearMarkersGroup.selectAll('.year-marker')
      .data(years)
      .join('line')
      .attr('class', 'year-marker')
      .attr('x1', d => xScale(d))
      .attr('x2', d => xScale(d))
      .attr('y1', -treeHeight / 2 - 50)
      .attr('y2', treeHeight / 2 + 50);

    yearMarkersGroup.selectAll('.year-label')
      .data(years)
      .join('text')
      .attr('class', 'year-label')
      .attr('x', d => xScale(d))
      .attr('y', -treeHeight / 2 - 60)
      .attr('text-anchor', 'middle')
      .text(d => d);
  }

  function estimateTreeHeight(node) {
    let count = 0;
    node.each(() => count++);
    return count * (config.cardHeight + config.verticalGap);
  }

  function updateLayout() {
    // Calculate tree layout
    const treeLayout = d3.tree()
      .nodeSize([config.cardHeight + config.verticalGap, 200])
      .separation((a, b) => a.parent === b.parent ? 1 : 1.2);

    treeLayout(root);

    // Swap x/y for horizontal layout and use birth year for x
    root.each(d => {
      d.y = d.x; // vertical position
      d.x = d.data.birthYear ? xScale(d.data.birthYear) : 0;
    });

    // Update links
    const links = root.links();

    linksGroup.selectAll('.link')
      .data(links, d => d.target.data.id)
      .join(
        enter => enter.append('path')
          .attr('class', 'link')
          .attr('d', d => linkPath(d.source, d.source))
          .call(enter => enter.transition().duration(config.animationDuration)
            .attr('d', d => linkPath(d.source, d.target))),
        update => update.transition().duration(config.animationDuration)
          .attr('d', d => linkPath(d.source, d.target)),
        exit => exit.transition().duration(config.animationDuration / 2)
          .attr('opacity', 0)
          .remove()
      );

    // Update nodes
    const nodes = root.descendants();

    const nodeGroups = nodesGroup.selectAll('.node-card')
      .data(nodes, d => d.data.id)
      .join(
        enter => createNodeCard(enter),
        update => update,
        exit => exit.transition().duration(config.animationDuration / 2)
          .attr('opacity', 0)
          .remove()
      );

    nodeGroups.transition().duration(config.animationDuration)
      .attr('transform', d => `translate(${d.x}, ${d.y})`);

    // Update year markers
    drawYearMarkers();
  }

  function createNodeCard(enter) {
    const node = enter.append('g')
      .attr('class', d => `node-card ${getGenderClass(d.data.gender)}`)
      .attr('transform', d => {
        const parent = d.parent;
        const startX = parent ? parent.x : d.x;
        const startY = parent ? parent.y : d.y;
        return `translate(${startX}, ${startY})`;
      })
      .attr('opacity', 0)
      .on('click', handleNodeClick);

    node.transition().duration(config.animationDuration)
      .attr('opacity', 1);

    // Card background
    node.append('rect')
      .attr('x', 0)
      .attr('y', -config.cardHeight / 2)
      .attr('width', d => calculateCardWidth(d.data))
      .attr('height', config.cardHeight);

    // Name
    node.append('text')
      .attr('class', 'name')
      .attr('x', 8)
      .attr('y', -config.cardHeight / 2 + 18)
      .text(d => truncateName(d.data.name, 20));

    // Dates
    node.append('text')
      .attr('class', 'dates')
      .attr('x', 8)
      .attr('y', -config.cardHeight / 2 + 34)
      .text(d => d.data.displayDates || formatDates(d.data));

    // Details (birthplace/occupation)
    node.append('text')
      .attr('class', 'details')
      .attr('x', 8)
      .attr('y', -config.cardHeight / 2 + 48)
      .text(d => d.data.birthPlace || d.data.occupation || '');

    // Collapse/expand button (if has children)
    const toggleBtn = node.filter(d => d.data.children && d.data.children.length > 0)
      .append('g')
      .attr('class', 'toggle-btn')
      .attr('transform', d => `translate(${calculateCardWidth(d.data) + 8}, 0)`)
      .on('click', handleToggle);

    toggleBtn.append('circle')
      .attr('r', 10);

    toggleBtn.append('text')
      .text(d => d.data._children ? '+' : '−');

    return node;
  }

  function handleNodeClick(event, d) {
    event.stopPropagation();

    // Toggle selection
    if (selectedNode === d) {
      selectedNode = null;
      nodesGroup.selectAll('.node-card').classed('selected', false);
    } else {
      selectedNode = d;
      nodesGroup.selectAll('.node-card')
        .classed('selected', n => n === d);
    }

    if (onSelectCallback) {
      onSelectCallback(selectedNode ? selectedNode.data : null);
    }
  }

  function handleToggle(event, d) {
    event.stopPropagation();

    if (d.data._children) {
      // Expand
      d.data.children = d.data._children;
      d.data._children = null;
    } else if (d.data.children && d.data.children.length > 0) {
      // Collapse
      d.data._children = d.data.children;
      d.data.children = [];
    }

    // Rebuild hierarchy and update
    root = d3.hierarchy(root.data);
    updateLayout();
  }

  function calculateCardWidth(data) {
    const lifespan = data.deathYear
      ? data.deathYear - data.birthYear
      : (data.birthYear ? currentYear - data.birthYear : 50);
    const width = lifespan * config.yearWidth;
    return Math.max(config.cardMinWidth, Math.min(config.cardMaxWidth, width));
  }

  function linkPath(source, target) {
    const sourceX = source.x + calculateCardWidth(source.data);
    const sourceY = source.y;
    const targetX = target.x;
    const targetY = target.y;

    // Curved path
    const midX = (sourceX + targetX) / 2;

    return `M ${sourceX} ${sourceY}
            C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`;
  }

  function resetView() {
    svg.transition().duration(config.animationDuration)
      .call(zoom.transform, d3.zoomIdentity
        .translate(config.horizontalPadding, height / 2));
  }

  function expandAll() {
    function expand(d) {
      if (d._children) {
        d.children = d._children;
        d._children = null;
      }
      if (d.children) {
        d.children.forEach(expand);
      }
    }
    expand(root.data);
    root = d3.hierarchy(root.data);
    updateLayout();
  }

  function collapseAll() {
    function collapse(d) {
      if (d.children && d.children.length > 0) {
        d._children = d.children;
        d.children = [];
      }
    }

    // Keep root expanded, collapse children
    if (root.data.children) {
      root.data.children.forEach(collapse);
    }
    root = d3.hierarchy(root.data);
    updateLayout();
  }
}

// --- Helper functions ---

function getGenderClass(gender) {
  if (gender === 'M') return 'male';
  if (gender === 'F') return 'female';
  return 'unknown';
}

function truncateName(name, maxLength) {
  if (!name) return 'Unknown';
  if (name.length <= maxLength) return name;
  return name.substring(0, maxLength - 1) + '…';
}

function formatDates(data) {
  const birth = data.birthYear;
  const death = data.deathYear;
  if (!birth) return 'dates unknown';
  if (!death) return `b. ${birth}`;
  return `${birth}–${death}`;
}
