import { test, chromium } from '@playwright/test';

test('login to ancestry', async ({ }) => {
  const browser = await chromium.launchPersistentContext(
    '/Users/chris/Library/Application Support/playwright-ancestry',
    { headless: false, viewport: { width: 1280, height: 900 } }
  );
  
  const page = await browser.newPage();
  await page.goto('https://www.ancestry.co.uk/account/signin');
  
  console.log('Please log in to Ancestry in the browser window...');
  console.log('Once logged in, press Enter in this terminal to continue.');
  
  // Wait for navigation to matches page (indicates successful login)
  try {
    await page.waitForURL(/dna|account|home/, { timeout: 300000 });
    console.log('Login detected! Saving session...');
    await page.waitForTimeout(3000);
  } catch (e) {
    console.log('Timeout waiting for login');
  }
  
  await browser.close();
  console.log('Session saved. You can now run the shared match scan.');
});
