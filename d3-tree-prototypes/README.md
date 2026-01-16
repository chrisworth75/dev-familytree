# D3 Family Tree Prototypes

Vanilla JavaScript prototypes for visualizing family trees using D3.js.

## Quick Start

ES modules require a local server. Use any of these:

```bash
# Python 3
cd d3-tree-prototypes
python -m http.server 8080

# Node.js (npx)
npx serve .

# PHP
php -S localhost:8080
```

Then open: http://localhost:8080

## Project Structure

```
d3-tree-prototypes/
├── index.html              # Landing page with all prototypes
├── css/
│   └── tree.css            # Shared styles (responsive)
├── js/
│   ├── data-loader.js      # Load/transform tree data
│   └── layouts/
│       └── horizontal.js   # Horizontal timeline layout
├── prototypes/
│   ├── timeline/           # Horizontal timeline (ready)
│   ├── radial/             # Radial/circular (planned)
│   ├── vertical/           # Traditional top-down (planned)
│   └── mobile/             # Mobile-optimized (planned)
└── data/
    └── sample-tree.json    # Sample family data
```

## Layouts

### Horizontal Timeline (Ready)
- X axis = birth year
- Card width = lifespan
- Features: zoom/pan, collapsible nodes, click-to-select, year markers

### Vertical Tree (Planned)
- Traditional ancestor chart (root at top)
- Spouse positioning

### Radial/Circular (Planned)
- Root at center, generations radiate outward
- Good for large trees

### Indented List (Planned)
- Collapsible outline view
- Mobile-friendly

## Data Format

```json
{
  "id": 1,
  "name": "Person Name",
  "birthYear": 1900,
  "deathYear": 1980,
  "gender": "M",
  "birthPlace": "City, County",
  "occupation": "Occupation",
  "children": [...]
}
```

## Adding New Layouts

1. Create layout module in `js/layouts/`
2. Export a `create*Tree(container, data, options)` function
3. Create prototype page in `prototypes/<name>/index.html`
4. Add to landing page

## Mobile Support

CSS includes responsive breakpoints (`@media (max-width: 768px)`).

Future plans:
- Separate mobile-optimized layouts
- Touch gesture support
- React Native version

## Dependencies

- D3.js v7 (loaded from CDN)

No build tools required.
