const express = require('express');
const { JSDOM } = require('jsdom');
const d3 = require('d3');

const app = express();
const PORT = 3300;

app.use(express.json());

/**
 * Render a horizontal tree for ancestors/descendants.
 * Root on left, branches extend right.
 */
function renderTree(data) {
  const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
  const document = dom.window.document;

  const root = d3.hierarchy(data);
  const nodeCount = root.descendants().length;
  const treeDepth = root.height;

  const nodeHeight = 40;
  const nodeWidth = 180;
  const margin = { top: 60, right: 60, bottom: 100, left: 60 };
  const width = (treeDepth + 1) * nodeWidth + margin.left + margin.right;
  const height = Math.max(nodeCount * nodeHeight, 200) + margin.top + margin.bottom;

  const body = d3.select(document.body);
  const svg = body.append('svg')
    .attr('xmlns', 'http://www.w3.org/2000/svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`);

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  const treeLayout = d3.tree()
    .size([height - margin.top - margin.bottom, width - margin.left - margin.right]);

  treeLayout(root);

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

  const nodes = g.selectAll('.node')
    .data(root.descendants())
    .enter()
    .append('g')
    .attr('class', 'node')
    .attr('data-person-id', d => d.data.id)
    .attr('transform', d => `translate(${d.y},${d.x})`);

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

/**
 * Render a vertical MRCA tree with large photo nodes.
 * Root (MRCA) at top, descendants branching down.
 */
function renderMrcaTree(data) {
  const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
  const document = dom.window.document;

  const root = d3.hierarchy(data);
  const treeDepth = root.height;

  const nodeRadius = 48;
  const nodeSpacingX = 180;
  const nodeSpacingY = 160;
  const margin = { top: 60, right: 60, bottom: 120, left: 60 };

  const leaves = root.leaves().length;
  const width = Math.max(leaves * nodeSpacingX, 400) + margin.left + margin.right;
  const height = (treeDepth + 1) * nodeSpacingY + margin.top + margin.bottom;

  const body = d3.select(document.body);
  const svg = body.append('svg')
    .attr('xmlns', 'http://www.w3.org/2000/svg')
    .attr('xmlns:xlink', 'http://www.w3.org/1999/xlink')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`);

  const defs = svg.append('defs');

  root.descendants().forEach((d, i) => {
    defs.append('clipPath')
      .attr('id', `clip-${i}`)
      .append('circle')
      .attr('r', nodeRadius)
      .attr('cx', 0)
      .attr('cy', 0);
  });

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  const treeLayout = d3.tree()
    .size([width - margin.left - margin.right, height - margin.top - margin.bottom])
    .separation((a, b) => a.parent === b.parent ? 1.2 : 1.5);

  treeLayout(root);

  const linkGenerator = d3.linkVertical()
    .x(d => d.x)
    .y(d => d.y);

  g.selectAll('.link')
    .data(root.links())
    .enter()
    .append('path')
    .attr('class', 'link')
    .attr('d', linkGenerator)
    .attr('fill', 'none')
    .attr('stroke', '#b0bec5')
    .attr('stroke-width', 2);

  const nodes = g.selectAll('.node')
    .data(root.descendants())
    .enter()
    .append('g')
    .attr('class', 'node')
    .attr('data-person-id', d => d.data.id)
    .attr('transform', d => `translate(${d.x},${d.y})`);

  nodes.each(function(d, i) {
    const node = d3.select(this);
    const gender = d.data.gender || d.data.sex;
    const genderColor = gender === 'M' || gender === 'male' ? '#2196f3'
                      : gender === 'F' || gender === 'female' ? '#e91e63'
                      : '#9e9e9e';

    if (d.data.avatarPath) {
      node.append('circle')
        .attr('r', nodeRadius)
        .attr('fill', genderColor)
        .attr('stroke', '#fff')
        .attr('stroke-width', 3);

      node.append('image')
        .attr('xlink:href', d.data.avatarPath)
        .attr('x', -nodeRadius)
        .attr('y', -nodeRadius)
        .attr('width', nodeRadius * 2)
        .attr('height', nodeRadius * 2)
        .attr('clip-path', `url(#clip-${i})`)
        .attr('preserveAspectRatio', 'xMidYMid slice');
    } else {
      node.append('circle')
        .attr('r', nodeRadius)
        .attr('fill', genderColor)
        .attr('stroke', '#fff')
        .attr('stroke-width', 3);

      const name = d.data.name || '';
      const initials = name.split(' ')
        .filter(part => part.length > 0)
        .map(part => part[0].toUpperCase())
        .slice(0, 2)
        .join('');

      node.append('text')
        .attr('dy', '0.35em')
        .attr('text-anchor', 'middle')
        .attr('font-family', 'Arial, sans-serif')
        .attr('font-size', '20px')
        .attr('font-weight', 'bold')
        .attr('fill', '#fff')
        .text(initials);
    }
  });

  nodes.append('text')
    .attr('y', nodeRadius + 20)
    .attr('text-anchor', 'middle')
    .attr('font-family', 'Arial, sans-serif')
    .attr('font-size', '13px')
    .attr('font-weight', '500')
    .attr('fill', '#333')
    .text(d => d.data.name || `ID: ${d.data.id}`);

  nodes.filter(d => d.data.dates && d.data.dates !== '-')
    .append('text')
    .attr('y', nodeRadius + 36)
    .attr('text-anchor', 'middle')
    .attr('font-family', 'Arial, sans-serif')
    .attr('font-size', '11px')
    .attr('fill', '#666')
    .text(d => d.data.dates);

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

app.post('/render/mrca', (req, res) => {
  try {
    const treeData = req.body;

    if (!treeData || typeof treeData !== 'object') {
      return res.status(400).json({ error: 'Invalid tree data' });
    }

    const svg = renderMrcaTree(treeData);
    res.set('Content-Type', 'image/svg+xml');
    res.send(svg);
  } catch (error) {
    console.error('MRCA render error:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.listen(PORT, () => {
  console.log(`D3 Tree Service running on http://localhost:${PORT}`);
});
