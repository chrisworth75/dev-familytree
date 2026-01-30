import { test, chromium } from '@playwright/test';
import * as fs from 'fs';

const matchesToScan = [
  { id: 277, name: 'Peter Davies' },
  { id: 5370, name: 'Christopher Bryan' },
  { id: 4461, name: 'pcmtdm' },
  { id: 3599, name: 'Chris Jackson' },
  { id: 4490, name: 'youngcodge2' },
];

test('login and scan', async ({ }) => {
  const browser = await chromium.launchPersistentContext(
    '/Users/chris/Library/Application Support/playwright-ancestry',
    { headless: false, viewport: { width: 1280, height: 900 } }
  );
  
  const page = await browser.newPage();
  
  // Go to DNA matches
  await page.goto('https://www.ancestry.co.uk/dna/matches');
  await page.waitForTimeout(5000);
  
  // Check if we need to log in
  const currentUrl = page.url();
  if (currentUrl.includes('signin') || currentUrl.includes('login') || 
      (await page.locator('text="Sign In"').isVisible().catch(() => false))) {
    console.log('=== LOGIN REQUIRED ===');
    console.log('Please log in to Ancestry in the browser window.');
    console.log('The script will continue automatically after you log in.');
    
    // Wait for successful navigation to matches page
    await page.waitForURL('**/dna/matches**', { timeout: 300000 });
    console.log('Login successful!');
    await page.waitForTimeout(5000);
  }
  
  // Verify we're on the matches page
  await page.screenshot({ path: '/tmp/matches_after_login.png' });
  console.log('On DNA matches page. Starting scans...');
  
  const results: any[] = [];
  
  for (const match of matchesToScan) {
    console.log(`\n=== SCANNING: ${match.name} ===`);
    
    // Go back to matches and search
    await page.goto('https://www.ancestry.co.uk/dna/matches');
    await page.waitForTimeout(4000);
    
    // Look for search functionality - try clicking on search icon or filter
    const searchBtn = page.locator('[aria-label*="search" i], [aria-label*="filter" i], button:has-text("Search"), button:has-text("Filter")').first();
    if (await searchBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchBtn.click();
      await page.waitForTimeout(1000);
    }
    
    // Try to find any input field
    const inputField = page.locator('input').first();
    if (await inputField.isVisible({ timeout: 5000 }).catch(() => false)) {
      await inputField.fill(match.name);
      await page.keyboard.press('Enter');
      await page.waitForTimeout(4000);
    } else {
      // Try using the URL search
      await page.goto(`https://www.ancestry.co.uk/dna/matches?search=${encodeURIComponent(match.name)}`);
      await page.waitForTimeout(4000);
    }
    
    await page.screenshot({ path: `/tmp/search_${match.id}.png` });
    
    // Try to click on the match
    const matchLink = page.locator(`text="${match.name}"`).first();
    if (await matchLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await matchLink.click();
      await page.waitForTimeout(4000);
      
      await page.screenshot({ path: `/tmp/profile_${match.id}.png` });
      
      // Look for Shared Matches
      const sharedBtn = page.locator('text="Shared matches"').first();
      if (await sharedBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await sharedBtn.click();
        await page.waitForTimeout(5000);
        
        // Scroll to load all
        for (let i = 0; i < 5; i++) {
          await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
          await page.waitForTimeout(2000);
        }
        
        await page.screenshot({ path: `/tmp/shared_${match.id}.png` });
        
        // Get the content
        const content = await page.textContent('body') || '';
        
        // Extract shared matches - write to file for processing
        fs.writeFileSync(`/tmp/shared_content_${match.id}.txt`, content);
        console.log(`Saved content for ${match.name} (${content.length} chars)`);
        
        results.push({ id: match.id, name: match.name, contentLength: content.length });
      } else {
        console.log('Shared matches button not found');
      }
    } else {
      console.log(`Match "${match.name}" not found in search results`);
    }
  }
  
  console.log('\n=== SCAN COMPLETE ===');
  console.log(JSON.stringify(results, null, 2));
  
  await browser.close();
});
