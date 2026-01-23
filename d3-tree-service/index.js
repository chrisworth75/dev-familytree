const express = require('express');
const { JSDOM } = require('jsdom');
const d3 = require('d3');

const app = express();
const PORT = 3300;

app.use(express.json());

function renderTree(data) {
  const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
  const document = dom.window.document;

  // Calculate dimensions based on tree structure
  const root = d3.hierarchy(data);
  const nodeCount = root.descendants().length;
  const treeDepth = root.height;

  // Dynamic sizing
  const nodeHeight = 40;
  const nodeWidth = 180;
  const margin = { top: 20, right: 120, bottom: 20, left: 80 };
  const width = (treeDepth + 1) * nodeWidth + margin.left + margin.right;
  const height = Math.max(nodeCount * nodeHeight, 200) + margin.top + margin.bottom;

  // Create SVG in jsdom
  const body = d3.select(document.body);
  const svg = body.append('svg')
    .attr('xmlns', 'http://www.w3.org/2000/svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`);

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  // Horizontal tree layout (root left, descendants right)
  const treeLayout = d3.tree()
    .size([height - margin.top - margin.bottom, width - margin.left - margin.right]);

  treeLayout(root);

  // Curved bezier links
  const linkGenerator = d3.linkHorizontal()
    .x(d => d.y)
    .y(d => d.x);

  g.selectAll('.link')
    .data(root.links())
    .enter()
    .append('path')
    .attr('class', 'link')
    .attr('d', linkGenerator)
    .attr('fill', 'none')
    .attr('stroke', '#999')
    .attr('stroke-width', 1.5);

  // Nodes
  const nodes = g.selectAll('.node')
    .data(root.descendants())
    .enter()
    .append('g')
    .attr('class', 'node')
    .attr('transform', d => `translate(${d.y},${d.x})`);

  // Circle nodes with gender colors
  nodes.append('circle')
    .attr('r', 8)
    .attr('fill', d => {
      const gender = d.data.gender || d.data.sex;
      if (gender === 'M' || gender === 'male') return '#2196f3';
      if (gender === 'F' || gender === 'female') return '#e91e63';
      return '#9e9e9e';
    })
    .attr('stroke', '#fff')
    .attr('stroke-width', 2);

  // Text labels: left of node if has children, right if leaf
  nodes.append('text')
    .attr('dy', '0.35em')
    .attr('x', d => d.children ? -12 : 12)
    .attr('text-anchor', d => d.children ? 'end' : 'start')
    .attr('font-family', 'Arial, sans-serif')
    .attr('font-size', '12px')
    .attr('fill', '#333')
    .text(d => d.data.name || d.data.label || `ID: ${d.data.id}`);

  return document.body.innerHTML;
}

app.post('/render', (req, res) => {
  try {
    const treeData = req.body;

    if (!treeData || typeof treeData !== 'object') {
      return res.status(400).json({ error: 'Invalid tree data' });
    }

    const svg = renderTree(treeData);
    res.set('Content-Type', 'image/svg+xml');
    res.send(svg);
  } catch (error) {
    console.error('Render error:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.listen(PORT, () => {
  console.log(`D3 Tree Service running on http://localhost:${PORT}`);
});
