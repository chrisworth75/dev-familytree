const express = require('express');
const { JSDOM } = require('jsdom');
const d3 = require('d3');

const app = express();
const PORT = 3300;

app.use(express.json());

// ===== Shared helpers =====

function genderColor(d) {
  const g = d.data.gender || d.data.sex;
  if (g === 'M' || g === 'male') return '#2196f3';
  if (g === 'F' || g === 'female') return '#e91e63';
  return '#9e9e9e';
}

function genderBg(gender) {
  if (gender === 'M' || gender === 'male') return '#e3f2fd';
  if (gender === 'F' || gender === 'female') return '#fce4ec';
  return '#f5f5f5';
}

function oppositeGender(gender) {
  if (gender === 'M' || gender === 'male') return 'F';
  if (gender === 'F' || gender === 'female') return 'M';
  return '';
}

// ===== Theme: Horizontal =====

const horizontal = {
  nodeSize: [25, 200],
  margin: { top: 20, right: 20, bottom: 20, left: 20 },

  computeBounds(root) {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    root.each(d => {
      x0 = Math.min(x0, d.y - 10);
      x1 = Math.max(x1, d.y + 150);
      y0 = Math.min(y0, d.x - 12);
      y1 = Math.max(y1, d.x + 12);
    });
    return { x0, x1, y0, y1 };
  },

  renderLinks(g, root) {
    g.selectAll('.link')
      .data(root.links())
      .enter()
      .append('path')
      .attr('d', d => {
        const sx = d.source.y, sy = d.source.x;
        const tx = d.target.y, ty = d.target.x;
        const mx = (sx + tx) / 2;
        return `M${sx},${sy}C${mx},${sy} ${mx},${ty} ${tx},${ty}`;
      })
      .attr('fill', 'none')
      .attr('stroke', '#999')
      .attr('stroke-width', 1.5);
  },

  renderNodes(g, root) {
    const nodes = g.selectAll('.node')
      .data(root.descendants())
      .enter()
      .append('g')
      .attr('class', 'node')
      .attr('data-person-id', d => d.data.id)
      .attr('transform', d => `translate(${d.y},${d.x})`);

    nodes.append('circle')
      .attr('r', 8)
      .attr('fill', genderColor)
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

    nodes.append('text')
      .attr('dy', '0.35em')
      .attr('x', 12)
      .attr('text-anchor', 'start')
      .attr('font-family', 'Arial, sans-serif')
      .attr('font-size', '12px')
      .attr('fill', '#333')
      .text(d => d.data.name || `ID: ${d.data.id}`);
  }
};

// ===== Theme: Vertical =====

const vertical = {
  nodeSize: [180, 150],
  margin: { top: 40, right: 40, bottom: 40, left: 40 },

  computeBounds(root) {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    root.each(d => {
      x0 = Math.min(x0, d.x - 90);
      x1 = Math.max(x1, d.x + 90);
      y0 = Math.min(y0, d.y - 20);
      y1 = Math.max(y1, d.y + 20);
    });
    return { x0, x1, y0, y1 };
  },

  renderLinks(g, root) {
    g.selectAll('.link')
      .data(root.links())
      .enter()
      .append('path')
      .attr('d', d => {
        const sx = d.source.x, sy = d.source.y;
        const tx = d.target.x, ty = d.target.y;
        const my = (sy + ty) / 2;
        return `M${sx},${sy}C${sx},${my} ${tx},${my} ${tx},${ty}`;
      })
      .attr('fill', 'none')
      .attr('stroke', '#999')
      .attr('stroke-width', 1.5);
  },

  renderNodes(g, root) {
    const nodes = g.selectAll('.node')
      .data(root.descendants())
      .enter()
      .append('g')
      .attr('class', 'node')
      .attr('data-person-id', d => d.data.id)
      .attr('transform', d => `translate(${d.x},${d.y})`);

    nodes.append('circle')
      .attr('r', 8)
      .attr('fill', genderColor)
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

    nodes.append('text')
      .attr('dy', -12)
      .attr('text-anchor', 'middle')
      .attr('font-family', 'Arial, sans-serif')
      .attr('font-size', '12px')
      .attr('fill', '#333')
      .text(d => d.data.name || `ID: ${d.data.id}`);
  }
};

// ===== Theme: Card =====

function renderCard(parent, x, y, w, h, r, data) {
  const bg = genderBg(data.gender);
  const group = parent.append('g');
  if (data.id) group.attr('class', 'node').attr('data-person-id', data.id);

  group.append('rect')
    .attr('x', x).attr('y', y)
    .attr('width', w).attr('height', h)
    .attr('rx', r)
    .attr('fill', bg)
    .attr('stroke', '#ccc')
    .attr('stroke-width', 1);

  group.append('text')
    .attr('x', x + w / 2).attr('y', y + 28)
    .attr('text-anchor', 'middle')
    .attr('font-family', 'Arial, sans-serif')
    .attr('font-size', '13px')
    .attr('font-weight', 'bold')
    .attr('fill', '#333')
    .text(data.name || `ID: ${data.id}`);

  if (data.dates && data.dates !== '-') {
    group.append('text')
      .attr('x', x + w / 2).attr('y', y + 46)
      .attr('text-anchor', 'middle')
      .attr('font-family', 'Arial, sans-serif')
      .attr('font-size', '11px')
      .attr('fill', '#666')
      .text(data.dates);
  }
}

const card = {
  nodeSize: [180, 120],
  margin: { top: 40, right: 40, bottom: 40, left: 40 },

  separation(a, b) {
    const aW = a.data.spouse ? 2 : 1;
    const bW = b.data.spouse ? 2 : 1;
    return (aW + bW) / 2;
  },

  computeBounds(root) {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    root.each(d => {
      const halfW = d.data.spouse ? 175 : 85;
      x0 = Math.min(x0, d.x - halfW);
      x1 = Math.max(x1, d.x + halfW);
      y0 = Math.min(y0, d.y - 40);
      y1 = Math.max(y1, d.y + 40);
    });
    return { x0, x1, y0, y1 };
  },

  renderLinks(g, root) {
    g.selectAll('.link')
      .data(root.links())
      .enter()
      .append('path')
      .attr('d', d => {
        const sx = d.source.x, sy = d.source.y + 35;
        const tx = d.target.x, ty = d.target.y - 35;
        const my = (sy + ty) / 2;
        return `M${sx},${sy}C${sx},${my} ${tx},${my} ${tx},${ty}`;
      })
      .attr('fill', 'none')
      .attr('stroke', '#999')
      .attr('stroke-width', 1.5);
  },

  renderNodes(g, root) {
    const W = 160, H = 70, GAP = 20, R = 8;

    const groups = g.selectAll('.card-group')
      .data(root.descendants())
      .enter()
      .append('g')
      .attr('transform', d => `translate(${d.x},${d.y})`);

    groups.each(function (d) {
      const node = d3.select(this);

      if (d.data.spouse) {
        renderCard(node, -(W + GAP / 2), -H / 2, W, H, R, d.data);

        renderCard(node, GAP / 2, -H / 2, W, H, R, {
          name: d.data.spouse,
          dates: d.data.spouseDates || '',
          gender: d.data.spouseGender || oppositeGender(d.data.gender),
          id: d.data.spouseId
        });

        node.append('line')
          .attr('x1', -GAP / 2).attr('x2', GAP / 2)
          .attr('y1', 0).attr('y2', 0)
          .attr('stroke', '#999').attr('stroke-width', 1.5);
      } else {
        renderCard(node, -W / 2, -H / 2, W, H, R, d.data);
      }
    });
  }
};

// ===== Theme registry =====

const themes = { horizontal, vertical, card };

// ===== Main render function =====

function renderTree(data, themeName) {
  const theme = themes[themeName] || themes.vertical;
  const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
  const document = dom.window.document;

  const root = d3.hierarchy(data);

  const treeLayout = d3.tree().nodeSize(theme.nodeSize);
  if (theme.separation) treeLayout.separation(theme.separation);
  treeLayout(root);

  const { x0, x1, y0, y1 } = theme.computeBounds(root);
  const m = theme.margin;
  const width = (x1 - x0) + m.left + m.right;
  const height = (y1 - y0) + m.top + m.bottom;

  const body = d3.select(document.body);
  const svg = body.append('svg')
    .attr('xmlns', 'http://www.w3.org/2000/svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`);

  const g = svg.append('g')
    .attr('transform', `translate(${m.left - x0},${m.top - y0})`);

  theme.renderLinks(g, root);
  theme.renderNodes(g, root);

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
    const gc = gender === 'M' || gender === 'male' ? '#2196f3'
                      : gender === 'F' || gender === 'female' ? '#e91e63'
                      : '#9e9e9e';

    if (d.data.avatarPath) {
      node.append('circle')
        .attr('r', nodeRadius)
        .attr('fill', gc)
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
        .attr('fill', gc)
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

// ===== Routes =====

app.post('/render', (req, res) => {
  try {
    const treeData = req.body;
    const themeName = req.query.theme || 'vertical';

    if (!treeData || typeof treeData !== 'object') {
      return res.status(400).json({ error: 'Invalid tree data' });
    }

    const svg = renderTree(treeData, themeName);
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
