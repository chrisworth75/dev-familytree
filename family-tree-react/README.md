# Family Tree React

React frontend for the Family Tree genealogy application. Displays family trees with D3.js visualizations.

## Tech Stack

- React 19
- Vite
- D3.js for tree visualization
- React Router

## Running Locally

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

App available at http://localhost:4202

## API Backend

This frontend connects to the Family Tree API. Start the backend first:

```bash
cd ../family-tree-app
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

API runs at http://localhost:3200/api

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server with HMR |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |
