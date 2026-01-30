import { test, chromium } from '@playwright/test';
import * as fs from 'fs';
import * as readline from 'readline';

test('interactive scan', async ({ }) => {
  const browser = await chromium.launchPersistentContext(
    '/Users/chris/Library/Application Support/playwright-ancestry',
    { 
      headless: false, 
      viewport: { width: 1400, height: 900 },
      args: ['--disable-blink-features=AutomationControlled']
    }
  );
  
  const page = await browser.newPage();
  
  // Navigate to Ancestry
  await page.goto('https://www.ancestry.co.uk');
  
  console.log('');
  console.log('=============================================');
  console.log('MANUAL STEP REQUIRED');
  console.log('=============================================');
  console.log('');
  console.log('1. Log in to Ancestry in the browser window');
  console.log('2. Navigate to DNA -> DNA Matches');
  console.log('3. Search for "Peter Davies" and click on the match');
  console.log('4. Click on "Shared matches" tab');
  console.log('');
  console.log('When you are on the shared matches page, the script');
  console.log('will automatically capture the data.');
  console.log('');
  console.log('Waiting for you to navigate to a shared matches page...');
  
  // Wait for user to navigate to shared matches page
  await page.waitForURL(/sharedmatches|shared-matches/, { timeout: 600000 });
  
  console.log('Detected shared matches page! Extracting data...');
  await page.waitForTimeout(3000);
  
  // Scroll to load all matches
  for (let i = 0; i < 8; i++) {
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(2000);
  }
  
  // Save the page content
  const content = await page.content();
  const textContent = await page.textContent('body') || '';
  
  fs.writeFileSync('/tmp/shared_page.html', content);
  fs.writeFileSync('/tmp/shared_page.txt', textContent);
  
  await page.screenshot({ path: '/tmp/shared_manual.png', fullPage: true });
  
  console.log('');
  console.log('Data saved! Check /tmp/shared_page.txt');
  console.log('');
  console.log('You can now navigate to another match\'s shared matches,');
  console.log('or close the browser to finish.');
  
  // Keep browser open for more manual navigation
  await page.waitForTimeout(300000);
  
  await browser.close();
});
