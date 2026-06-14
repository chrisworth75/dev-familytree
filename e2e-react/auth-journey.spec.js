// @ts-check
// Data-driven e2e: the real gate. Drives a genuine Keycloak login, then asserts the
// app renders SEEDED data — dashboard stats + a person's family. Runs against any
// full stack (Postgres + Keycloak + API + React + seed); BASE_URL selects which tier.
const { test, expect } = require('@playwright/test');

const USER = process.env.KC_USER || 'dev-owner';
const PASS = process.env.KC_PASS || 'dev-owner';

// keycloak-js uses onLoad:'login-required', so a fresh context lands on the Keycloak
// login form. If an SSO session already exists, no form shows — handle both.
async function fillLoginIfPresent(page) {
  const user = page.locator('#username');
  if (await user.isVisible().catch(() => false)) {
    await user.fill(USER);
    await page.locator('#password').fill(PASS);
    await page.locator('#kc-login').click();
  }
}

test('logs in via Keycloak and sees seeded data + a family', async ({ page }) => {
  // 1) Login-required redirects us to Keycloak; sign in as the seeded owner.
  await page.goto('/');
  await page.waitForSelector('#username', { timeout: 30000 });
  await fillLoginIfPresent(page);

  // 2) Back on the app, authenticated — the dashboard renders REAL data (not the
  //    "Failed to load stats" error the unauthenticated app showed).
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: 30000 });
  await expect(page.getByText('Failed to load stats')).toHaveCount(0);

  // The seeded tree is the British Royal Family: 6 people (Charles + Philip +
  // Elizabeth + Diana + William + Harry).
  const peopleCard = page.locator('.stat-card', { hasText: 'People in Tree' });
  await expect(peopleCard.locator('.stat-value')).toHaveText('6');

  // 3) Open person 1 (the root, Charles) and see the family resolved from the DB.
  await page.goto('/person/1');
  await fillLoginIfPresent(page); // in case the reload needed a silent re-auth fallback
  await expect(page.getByRole('heading', { name: /Charles Windsor/ })).toBeVisible({ timeout: 30000 });
  await expect(page.getByRole('heading', { name: 'Family' })).toBeVisible();
  // Parents (Philip + Elizabeth), spouse (Diana), and children (William, Harry).
  await expect(page.getByRole('heading', { name: 'Parents' })).toBeVisible();
  await expect(page.getByText('Father:')).toBeVisible();
  await expect(page.getByText('Mother:')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Spouse' })).toBeVisible();
  await expect(page.getByText('Diana Spencer')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Children' })).toBeVisible();
  await expect(page.getByText('William Windsor')).toBeVisible();

  // 4) The ancestor tree section renders (proves the d3-tree-service path: the API
  //    proxies to it for /api/tree-svg, and Charles has 2 ancestors).
  await expect(page.getByRole('heading', { name: /Ancestors \(2\)/ })).toBeVisible({ timeout: 20000 });
});
