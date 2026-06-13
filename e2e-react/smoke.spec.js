// @ts-check
// Render smoke test for the React SPA. Auth-light: the API requires auth that React
// doesn't send yet, so /api/** calls 401 — this test only asserts the app shell
// builds, serves, and mounts. Data-driven e2e comes once React does Keycloak.
const { test, expect } = require('@playwright/test');

test.describe('React app shell', () => {
  test('serves and mounts without crashing', async ({ page }) => {
    const resp = await page.goto('/');
    expect(resp, 'page should respond').not.toBeNull();
    expect(resp.status(), 'index served OK').toBeLessThan(400);

    // The document has a title (from index.html)
    await expect(page).toHaveTitle(/.+/);

    // React mounted *something* into #root, even though API data 401s
    await expect(page.locator('#root')).not.toBeEmpty();
  });
});
