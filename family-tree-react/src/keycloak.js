import Keycloak from 'keycloak-js'
import { KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID } from './config'

// Single Keycloak instance shared by main.jsx (login) and api.js (Bearer token).
const keycloak = new Keycloak({
  url: KEYCLOAK_URL,
  realm: KEYCLOAK_REALM,
  clientId: KEYCLOAK_CLIENT_ID,
})

export default keycloak
