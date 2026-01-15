/**
 * D3.js Family Tree Timeline Visualization - Horizontal Layout
 *
 * Features:
 * - Horizontal timeline: X position = birth year, width = lifespan
 * - Tree structure on Y axis
 * - Zoom and pan with mouse/touch
 * - Collapsible nodes
 * - Full screen layout
 */

class FamilyTree {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.options = {
            nodeHeight: 24,
            verticalSpacing: 6,
            pixelsPerYear: 1.5,
            duration: 750,
            currentYear: new Date().getFullYear(),
            defaultLifespan: 40,
            ...options
        };

        this.svg = null;
        this.g = null;
        this.zoom = null;
        this.root = null;
        this.treeLayout = null;
        this.onPersonClick = null;
        this.nodeId = 0;
        this.yearScale = null;
        this.minYear = null;
        this.maxYear = null;
    }

    async init(treeSlug) {
        try {
            const response = await fetch(`/api/trees/${treeSlug}/hierarchy`);
            if (!response.ok) throw new Error('Failed to load tree data');
            const data = await response.json();
            this.render(data);
        } catch (error) {
            console.error('Error loading tree:', error);
            document.getElementById(this.containerId).innerHTML =
                '<p class="error">Error loading family tree</p>';
        }
    }

    parseDates(dates) {
        if (!dates) return { birth: null, death: null };
        const parts = dates.split('-');
        return {
            birth: parts[0] ? parseInt(parts[0]) : null,
            death: parts[1] ? parseInt(parts[1]) : null
        };
    }

    getLifespan(d) {
        const dates = this.parseDates(d.data.dates);
        if (!dates.birth) return this.options.defaultLifespan;
        const death = dates.death || this.options.currentYear;
        return Math.max(10, Math.min(110, death - dates.birth));
    }

    getNodeWidth(d) {
        const lifespan = this.getLifespan(d);
        return lifespan * this.options.pixelsPerYear;
    }

    render(data) {
        const container = document.getElementById(this.containerId);

        // Full screen dimensions
        const width = window.innerWidth - 40;
        const height = window.innerHeight - 200;

        container.innerHTML = '';

        this.root = d3.hierarchy(data);

        // Calculate year range
        let allNodes = this.root.descendants();
        let years = allNodes.map(d => this.parseDates(d.data.dates).birth).filter(y => y);
        let deathYears = allNodes.map(d => this.parseDates(d.data.dates).death).filter(y => y);

        this.minYear = Math.min(...years) - 5;
        this.maxYear = Math.max(...years, ...deathYears) + 20;

        // X scale: year to pixel position
        this.yearScale = year => (year - this.minYear) * this.options.pixelsPerYear + 100;

        const svgWidth = Math.max(width, (this.maxYear - this.minYear) * this.options.pixelsPerYear + 200);
        const svgHeight = Math.max(height, allNodes.length * (this.options.nodeHeight + this.options.verticalSpacing) + 100);

        // Create SVG
        this.svg = d3.select(`#${this.containerId}`)
            .append('svg')
            .attr('width', svgWidth)
            .attr('height', svgHeight);

        // Add zoom
        this.zoom = d3.zoom()
            .scaleExtent([0.2, 3])
            .on('zoom', (event) => {
                this.g.attr('transform', event.transform);
            });

        this.svg.call(this.zoom);

        // Main group
        this.g = this.svg.append('g')
            .attr('transform', 'translate(0, 50)');

        // Add timeline axis
        this.addTimelineAxis(svgHeight);

        // Add gradients
        this.addDefs();

        // Tree layout for Y positioning only
        this.treeLayout = d3.tree()
            .nodeSize([this.options.nodeHeight + this.options.verticalSpacing, 100]);

        this.root.x0 = 50;
        this.root.y0 = this.yearScale(this.parseDates(this.root.data.dates).birth || this.minYear);

        // Expand all nodes
        this.root.descendants().forEach(d => {
            if (d._children) {
                d.children = d._children;
                d._children = null;
            }
        });
        this.update(this.root);
    }

    addTimelineAxis(height) {
        const axisGroup = this.g.append('g')
            .attr('class', 'timeline-axis');

        // Year markers every 25 years
        for (let year = Math.ceil(this.minYear / 25) * 25; year <= this.maxYear; year += 25) {
            const x = this.yearScale(year);

            // Vertical line
            axisGroup.append('line')
                .attr('x1', x)
                .attr('x2', x)
                .attr('y1', -30)
                .attr('y2', height)
                .attr('stroke', '#e0e0e0')
                .attr('stroke-width', 1)
                .attr('stroke-dasharray', year % 100 === 0 ? 'none' : '4,4');

            // Year label at top
            axisGroup.append('text')
                .attr('x', x)
                .attr('y', -35)
                .attr('text-anchor', 'middle')
                .attr('font-size', '11px')
                .attr('fill', year % 100 === 0 ? '#333' : '#999')
                .attr('font-weight', year % 100 === 0 ? '600' : '400')
                .text(year);
        }
    }

    addDefs() {
        const defs = this.svg.append('defs');

        const maleGradient = defs.append('linearGradient')
            .attr('id', 'maleGradient')
            .attr('x1', '0%').attr('y1', '0%')
            .attr('x2', '100%').attr('y2', '0%');
        maleGradient.append('stop').attr('offset', '0%').attr('stop-color', '#6b8e9f');
        maleGradient.append('stop').attr('offset', '100%').attr('stop-color', '#4a7085');

        const femaleGradient = defs.append('linearGradient')
            .attr('id', 'femaleGradient')
            .attr('x1', '0%').attr('y1', '0%')
            .attr('x2', '100%').attr('y2', '0%');
        femaleGradient.append('stop').attr('offset', '0%').attr('stop-color', '#c48b9f');
        femaleGradient.append('stop').attr('offset', '100%').attr('stop-color', '#a06b7f');
    }

    collapse(d) {
        if (d.children) {
            d._children = d.children;
            d._children.forEach(child => this.collapse(child));
            d.children = null;
        }
    }

    toggle(d) {
        if (d.children) {
            d._children = d.children;
            d.children = null;
        } else if (d._children) {
            d.children = d._children;
            d._children = null;
        }
    }

    update(source) {
        const duration = this.options.duration;
        const nodeHeight = this.options.nodeHeight;

        // Compute tree layout for Y positions
        const treeData = this.treeLayout(this.root);
        const nodes = treeData.descendants();
        const links = treeData.links();

        // Set positions: X = birth year, Y = tree structure
        nodes.forEach(d => {
            const dates = this.parseDates(d.data.dates);
            const birthYear = dates.birth || (this.minYear + d.depth * 25);
            d.x = this.yearScale(birthYear);  // X = timeline position
            d.y = d.x;  // Store original tree x as y (swap axes)
            d.x = this.yearScale(birthYear);
            // Use tree layout's x for vertical position (renamed to y for horizontal layout)
            d.yPos = treeData.descendants().indexOf(d) * (nodeHeight + this.options.verticalSpacing);
            d.nodeWidth = this.getNodeWidth(d);
        });

        // Recalculate Y positions based on tree structure
        let yOffset = 0;
        const assignY = (node, depth = 0) => {
            node.yPos = yOffset;
            yOffset += nodeHeight + this.options.verticalSpacing;
            if (node.children) {
                node.children.forEach(child => assignY(child, depth + 1));
            }
        };
        yOffset = 0;
        assignY(this.root);

        // ========== NODES ==========
        const node = this.g.selectAll('g.node')
            .data(nodes, d => d.id || (d.id = ++this.nodeId));

        const nodeEnter = node.enter().append('g')
            .attr('class', 'node')
            .attr('transform', d => `translate(${source.x0 || 100},${source.yPos || 0})`)
            .attr('cursor', 'pointer')
            .on('click', (event, d) => {
                event.stopPropagation();
                if (event.shiftKey || d.children || d._children) {
                    this.toggle(d);
                    this.update(d);
                } else if (this.onPersonClick) {
                    this.onPersonClick(d.data.id, event.target);
                }
            });

        // Card - width = lifespan
        nodeEnter.append('rect')
            .attr('class', 'card')
            .attr('x', 0)
            .attr('y', 0)
            .attr('width', d => d.nodeWidth || 100)
            .attr('height', nodeHeight)
            .attr('rx', 3)
            .attr('fill', d => d.data.gender === 'F' ? 'url(#femaleGradient)' : 'url(#maleGradient)')
            .attr('stroke', '#fff')
            .attr('stroke-width', 1.5)
            .attr('opacity', 0.9);

        // Name
        nodeEnter.append('text')
            .attr('class', 'name')
            .attr('x', 5)
            .attr('y', 12)
            .attr('font-size', '10px')
            .attr('font-weight', '600')
            .attr('fill', '#fff')
            .text(d => truncate(d.data.name, 25));

        // Dates
        nodeEnter.append('text')
            .attr('class', 'dates')
            .attr('x', 5)
            .attr('y', 23)
            .attr('font-size', '9px')
            .attr('fill', 'rgba(255,255,255,0.85)')
            .text(d => d.data.dates);

        // Toggle indicator
        nodeEnter.append('text')
            .attr('class', 'toggle-indicator')
            .attr('x', d => (d.nodeWidth || 100) - 12)
            .attr('y', 12)
            .attr('font-size', '11px')
            .attr('font-weight', 'bold')
            .attr('fill', '#fff')
            .text(d => d._children ? '+' : (d.children ? '−' : ''));

        // UPDATE
        const nodeUpdate = nodeEnter.merge(node);

        nodeUpdate.transition()
            .duration(duration)
            .attr('transform', d => `translate(${d.x},${d.yPos})`);

        nodeUpdate.select('.card')
            .transition()
            .duration(duration)
            .attr('width', d => d.nodeWidth || 100)
            .attr('stroke', d => d.data.selected ? '#ffeb3b' : '#fff')
            .attr('stroke-width', d => d.data.selected ? 3 : 1.5);

        nodeUpdate.select('.toggle-indicator')
            .attr('x', d => (d.nodeWidth || 100) - 12)
            .text(d => d._children ? '+' : (d.children ? '−' : ''));

        // EXIT
        const nodeExit = node.exit().transition()
            .duration(duration)
            .attr('transform', d => `translate(${source.x},${source.yPos || 0})`)
            .remove();

        nodeExit.select('.card').attr('opacity', 0);
        nodeExit.selectAll('text').attr('opacity', 0);

        // ========== LINKS ==========
        const link = this.g.selectAll('path.link')
            .data(links, d => d.target.id);

        const linkEnter = link.enter().insert('path', 'g')
            .attr('class', 'link')
            .attr('fill', 'none')
            .attr('stroke', '#999')
            .attr('stroke-width', 1.5)
            .attr('stroke-opacity', 0.5)
            .attr('d', d => {
                const o = {x: source.x0 || 100, yPos: source.yPos || 0, nodeWidth: 100};
                return this.diagonal(o, o);
            });

        const linkUpdate = linkEnter.merge(link);

        linkUpdate.transition()
            .duration(duration)
            .attr('d', d => this.diagonal(d.source, d.target));

        link.exit().transition()
            .duration(duration)
            .attr('d', d => {
                const o = {x: source.x, yPos: source.yPos || 0, nodeWidth: 100};
                return this.diagonal(o, o);
            })
            .remove();

        // Store positions
        nodes.forEach(d => {
            d.x0 = d.x;
            d.yPos0 = d.yPos;
        });
    }

    diagonal(s, d) {
        // Connect bottom of parent to top of child
        const sourceX = s.x + (s.nodeWidth || 100) / 2;
        const sourceY = s.yPos + this.options.nodeHeight;
        const targetX = d.x + (d.nodeWidth || 100) / 2;
        const targetY = d.yPos;
        const midY = (sourceY + targetY) / 2;

        return `M ${sourceX} ${sourceY} C ${sourceX} ${midY}, ${targetX} ${midY}, ${targetX} ${targetY}`;
    }

    selectPerson(personId) {
        this.root.descendants().forEach(d => d.data.selected = false);
        const node = this.root.descendants().find(d => d.data.id === personId);
        if (node) node.data.selected = true;
        this.update(this.root);
    }

    expandAll() {
        this.root.descendants().forEach(d => {
            if (d._children) {
                d.children = d._children;
                d._children = null;
            }
        });
        this.update(this.root);
    }

    collapseAll() {
        this.root.descendants().forEach(d => {
            if (d.depth > 0 && d.children) {
                d._children = d.children;
                d.children = null;
            }
        });
        this.update(this.root);
    }

    resetZoom() {
        this.svg.transition()
            .duration(750)
            .call(this.zoom.transform, d3.zoomIdentity);
    }
}

function truncate(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength - 1) + '...' : text;
}
