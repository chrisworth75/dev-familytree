/**
 * Data Loader Module
 * Handles loading and transforming family tree data
 */

/**
 * Load tree data from a JSON file
 * @param {string} url - Path to JSON file
 * @returns {Promise<Object>} Tree data
 */
export async function loadTreeData(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load tree data: ${response.status}`);
  }
  return response.json();
}

/**
 * Convert flat array of people to hierarchical tree structure
 * @param {Array} people - Flat array of person objects with parentId
 * @param {number|null} rootId - ID of root person (null for auto-detect)
 * @returns {Object} Hierarchical tree
 */
export function flatToHierarchy(people, rootId = null) {
  const map = new Map();
  people.forEach(p => map.set(p.id, { ...p, children: [] }));

  let root = null;

  people.forEach(p => {
    const node = map.get(p.id);
    if (p.parentId && map.has(p.parentId)) {
      map.get(p.parentId).children.push(node);
    } else if (rootId === null || p.id === rootId) {
      if (root === null) root = node;
    }
  });

  return root;
}

/**
 * Calculate derived properties for tree visualization
 * @param {Object} node - Tree node
 * @param {number} depth - Current depth
 * @returns {Object} Node with calculated properties
 */
export function enrichTreeData(node, depth = 0) {
  const currentYear = new Date().getFullYear();

  const enriched = {
    ...node,
    depth,
    lifespan: node.deathYear
      ? node.deathYear - node.birthYear
      : (node.birthYear ? currentYear - node.birthYear : null),
    isLiving: !node.deathYear && node.birthYear,
    displayDates: formatDates(node.birthYear, node.deathYear),
    _children: null, // For collapse state
  };

  if (node.children && node.children.length > 0) {
    enriched.children = node.children.map(child => enrichTreeData(child, depth + 1));
  } else {
    enriched.children = [];
  }

  return enriched;
}

/**
 * Format birth/death years for display
 * @param {number|null} birth
 * @param {number|null} death
 * @returns {string}
 */
function formatDates(birth, death) {
  if (!birth) return 'dates unknown';
  if (!death) return `b. ${birth}`;
  return `${birth}–${death}`;
}

/**
 * Count total descendants
 * @param {Object} node
 * @returns {number}
 */
export function countDescendants(node) {
  if (!node.children || node.children.length === 0) return 0;
  return node.children.reduce((sum, child) =>
    sum + 1 + countDescendants(child), 0
  );
}

/**
 * Find min/max birth years in tree
 * @param {Object} node
 * @returns {{min: number, max: number}}
 */
export function getYearRange(node) {
  let min = node.birthYear || Infinity;
  let max = node.birthYear || -Infinity;

  function traverse(n) {
    if (n.birthYear) {
      min = Math.min(min, n.birthYear);
      max = Math.max(max, n.birthYear);
    }
    if (n.deathYear) {
      max = Math.max(max, n.deathYear);
    }
    if (n.children) {
      n.children.forEach(traverse);
    }
  }

  traverse(node);
  return { min, max };
}

/**
 * Get all nodes as flat array (for searching etc)
 * @param {Object} root
 * @returns {Array}
 */
export function flattenTree(root) {
  const nodes = [];

  function traverse(node) {
    nodes.push(node);
    if (node.children) {
      node.children.forEach(traverse);
    }
  }

  traverse(root);
  return nodes;
}

/**
 * Find a node by ID
 * @param {Object} root
 * @param {number} id
 * @returns {Object|null}
 */
export function findNodeById(root, id) {
  if (root.id === id) return root;

  if (root.children) {
    for (const child of root.children) {
      const found = findNodeById(child, id);
      if (found) return found;
    }
  }

  return null;
}
