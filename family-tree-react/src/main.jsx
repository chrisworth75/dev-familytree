import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import keycloak from './keycloak'

const root = createRoot(document.getElementById('root'))

// Require a Keycloak login before the app renders; PKCE for the public SPA client.
// After redirect-back we're authenticated and api.js attaches the Bearer token.
keycloak
  .init({ onLoad: 'login-required', pkceMethod: 'S256', checkLoginIframe: false })
  .then(() => {
    root.render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
  })
  .catch((err) => {
    console.error('Keycloak init failed', err)
    root.render(
      <div style={{ padding: 24, font: '14px system-ui' }}>
        <h2>Sign-in unavailable</h2>
        <p>Could not reach Keycloak at <code>{keycloak.authServerUrl}</code>.</p>
      </div>,
    )
  })
