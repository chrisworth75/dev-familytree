import { test, chromium } from '@playwright/test';
import * as fs from 'fs';

const trees = [
  { name: 'Brenda Davey', id: '173434538', cm: 101 },
  { name: 'Ethel Hull', id: '179644707', cm: 52 },
  { name: 'Peter Ennor', id: '190521133', cm: 34 },
  { name: 'Kenneth Olsen', id: '197338145', cm: 28 },
  { name: 'brenda stephens', id: '162364555', cm: 22 },
  { name: 'marksutherst', id: '185947762', cm: 19 },
  { name: 'ShipmanRichardsonTree', id: '67323932', cm: 18 },
];

test('fetch all trees', async ({ }) => {
  const browser = await chromium.launchPersistentContext(
    '/Users/chris/Library/Application Support/playwright-ancestry',
    { headless: false, viewport: { width: 1400, height: 900 } }
  );

  const page = await browser.newPage();

  // Check login
  await page.goto('https://www.ancestry.co.uk/family-tree');
  await page.waitForTimeout(3000);

  if (page.url().includes('signin') || await page.locator('text="Sign In"').first().isVisible().catch(() => false)) {
    console.log('Please log in to Ancestry...');
    await page.waitForURL(/family-tree|account/, { timeout: 300000 });
    console.log('Login successful!');
  }

  const results: any = {};

  for (const tree of trees) {
    console.log('\n=== Fetching: ' + tree.name + ' (' + tree.cm + ' cM) ===');

    // Try pedigree view first (shows ancestors)
    const pedigreeUrl = 'https://www.ancestry.co.uk/family-tree/tree/' + tree.id + '/family/pedigree';
    await page.goto(pedigreeUrl, { timeout: 60000 });
    await page.waitForTimeout(4000);

    // Check if tree is accessible
    const pageText = await page.textContent('body') || '';

    if (pageText.includes('private') || pageText.includes('not available') || pageText.includes('sorry')) {
      console.log('Tree is private or not accessible');
      results[tree.name] = { status: 'private', surnames: [] };
      continue;
    }

    // Screenshot
    await page.screenshot({ path: '/tmp/tree_' + tree.id + '.png' });

    // Try to extract surnames from the page
    const surnames: string[] = [];

    // Extract potential surnames (UPPERCASE words after first names)
    const namePattern = /([A-Z][a-z]+)\s+([A-Z][A-Z][A-Z]+)/g;
    let match;
    while ((match = namePattern.exec(pageText)) !== null) {
      const surname = match[2];
      if (surname.length > 2 && !surnames.includes(surname)) {
        surnames.push(surname);
      }
    }

    // Also look for names in standard format
    const namePattern2 = /([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+([A-Z][a-z]+)\n/g;
    while ((match = namePattern2.exec(pageText)) !== null) {
      const surname = match[2].toUpperCase();
      if (surname.length > 2 && !surnames.includes(surname)) {
        surnames.push(surname);
      }
    }

    console.log('Found ' + surnames.length + ' surnames: ' + surnames.slice(0, 20).join(', '));
    results[tree.name] = { status: 'accessible', surnames, cm: tree.cm, treeId: tree.id };

    // Save full text for later analysis
    fs.writeFileSync('/tmp/tree_' + tree.id + '.txt', pageText);
  }

  // Save results
  fs.writeFileSync('/tmp/tree_results.json', JSON.stringify(results, null, 2));
  console.log('\n=== RESULTS SAVED to /tmp/tree_results.json ===');

  await browser.close();
});
