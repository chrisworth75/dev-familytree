import { test, chromium } from '@playwright/test';

const matchesToScan = [
  { id: 277, name: 'Peter Davies' },
  { id: 5370, name: 'Christopher Bryan' },
  { id: 4461, name: 'pcmtdm' },
  { id: 3599, name: 'Chris Jackson' },
  { id: 4490, name: 'youngcodge2' },
];

test('scan shared matches', async ({ }) => {
  const browser = await chromium.launchPersistentContext(
    '/Users/chris/Library/Application Support/playwright-ancestry',
    { headless: false, viewport: { width: 1280, height: 900 } }
  );
  
  const page = await browser.newPage();
  
  for (const match of matchesToScan) {
    console.log(`\n=== SCANNING: ${match.name} ===`);
    
    // Go to matches page and search
    await page.goto('https://www.ancestry.co.uk/dna/matches');
    await page.waitForTimeout(3000);
    
    // Find and use search
    const searchInput = page.locator('input[type="text"], input[type="search"]').first();
    await searchInput.waitFor({ timeout: 10000 });
    await searchInput.fill(match.name);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(3000);
    
    // Click on the match name
    const matchLink = page.locator(`a:has-text("${match.name}")`).first();
    if (await matchLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await matchLink.click();
      await page.waitForTimeout(3000);
      
      // Click on Shared Matches tab
      const sharedTab = page.locator('button:has-text("Shared"), a:has-text("Shared")').first();
      if (await sharedTab.isVisible({ timeout: 5000 }).catch(() => false)) {
        await sharedTab.click();
        await page.waitForTimeout(4000);
        
        // Scroll to load all
        for (let i = 0; i < 5; i++) {
          await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
          await page.waitForTimeout(1500);
        }
        
        // Get page content and extract matches
        const content = await page.textContent('body') || '';
        
        // Look for patterns like "Name 23 cM"
        const lines = content.split('\n');
        const sharedMatches: string[] = [];
        
        for (let i = 0; i < lines.length; i++) {
          const cmMatch = lines[i].match(/^(\d+)\s*cM/);
          if (cmMatch && i > 0) {
            // Previous non-empty line might be the name
            for (let j = i - 1; j >= Math.max(0, i - 3); j--) {
              const name = lines[j].trim();
              if (name && name.length > 2 && name.length < 40 && 
                  !name.includes('cM') && !name.includes('Shared') &&
                  !name.match(/^\d+$/) && !name.includes('segment')) {
                sharedMatches.push(`${name}|${cmMatch[1]}`);
                console.log(`SHARED|${match.id}|${name}|${cmMatch[1]}`);
                break;
              }
            }
          }
        }
        
        console.log(`Found ${sharedMatches.length} shared matches`);
        await page.screenshot({ path: `/tmp/shared_${match.id}.png` });
      } else {
        console.log('Shared tab not found');
      }
    } else {
      console.log(`Match "${match.name}" not found`);
      await page.screenshot({ path: `/tmp/search_${match.id}.png` });
    }
  }
  
  await browser.close();
});
