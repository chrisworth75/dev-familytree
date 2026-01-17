// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Family Tree App', () => {

  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('input[name="username"]', 'chris');
    await page.fill('input[name="password"]', 'chris');
    await page.click('button[type="submit"]');
    // Wait for redirect to home
    await page.waitForURL('/');
  });

  test('login and see tree list', async ({ page }) => {
    // Should see the home page with tree cards
    await expect(page.locator('h1, h2').first()).toBeVisible();
    // Should see at least one tree card
    await expect(page.locator('.card, [class*="tree"]').first()).toBeVisible();
  });

  test('click Worthington tree and verify content', async ({ page }) => {
    // Click on Worthington tree
    await page.click('text=Worthington');

    // Wait for tree to load
    await page.waitForLoadState('networkidle');

    // Should see Henry Worthington (the root) somewhere in the tree
    await expect(page.locator('text=Henry Worthington').first()).toBeVisible({ timeout: 10000 });
  });

  test('click My Direct Line tree and verify content', async ({ page }) => {
    // Click on My Direct Line tree
    await page.click('text=My Direct Line');

    // Wait for tree to load
    await page.waitForLoadState('networkidle');

    // Should see Arthur Worthington (root of my-family tree)
    await expect(page.locator('text=Arthur Worthington').first()).toBeVisible({ timeout: 10000 });
  });

  test('verify tree contains Chris Worthington', async ({ page }) => {
    // Click on My Direct Line tree
    await page.click('text=My Direct Line');

    // Wait for tree to load
    await page.waitForLoadState('networkidle');

    // Should see Chris in the tree
    await expect(page.locator('text=Chris Worthington').first()).toBeVisible({ timeout: 10000 });
  });

  test('verify tree contains multiple generations', async ({ page }) => {
    // Click on Worthington tree
    await page.click('text=Worthington');

    // Wait for tree to load
    await page.waitForLoadState('networkidle');

    // Verify multiple generations are visible
    await expect(page.locator('text=Henry Worthington').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=James Worthington').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=George Worthington').first()).toBeVisible({ timeout: 10000 });
  });

});

test.describe('API Tests', () => {

  test('hierarchy API returns valid tree data', async ({ request }) => {
    const response = await request.get('/api/trees/my-family/hierarchy');
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('id');
    expect(data).toHaveProperty('name');
    expect(data).toHaveProperty('children');
  });

  test('person API returns person with relationships', async ({ request }) => {
    const response = await request.get('/api/persons/1000');
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('person');
    expect(data.person.forename).toBe('Chris');
    expect(data.person.surname).toBe('Worthington');
  });

  test('search API finds people with Worthington in name', async ({ request }) => {
    const response = await request.get('/api/persons/search?name=Worthington&limit=10');
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(Array.isArray(data)).toBeTruthy();
    expect(data.length).toBeGreaterThan(0);
    // Check that results contain 'Worthington' in forename or surname
    const matches = data.filter(p =>
      (p.forename && p.forename.includes('Worthington')) ||
      (p.surname && p.surname.includes('Worthington'))
    );
    expect(matches.length).toBeGreaterThan(0);
  });

});
