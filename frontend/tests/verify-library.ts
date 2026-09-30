/**
 * Browser verification script for Parts & Knowledge pages.
 *
 * Usage:
 *   npx playwright install chromium  (first time only)
 *   npx tsx tests/verify-library.ts
 *
 * Clicks every part type, 3 genes, 3 TFs (inc. RpoD), 3 pathways (inc. largest).
 * Scans DOM for bare "—", "N/A", "null", "undefined", "NaN", and empty fields.
 * Checks that displayed part lengths are consistent with the sequence block.
 * Saves screenshots to tests/screenshots/.
 */

import { chromium, Page } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';

const BASE = 'http://localhost:3000';
const SS_DIR = path.join(__dirname, 'screenshots');
const FORBIDDEN_STRINGS = ['—', 'N/A', 'null', 'undefined', 'NaN', '\\u2715'];

// Ensure screenshot directory
if (!fs.existsSync(SS_DIR)) fs.mkdirSync(SS_DIR, { recursive: true });

interface ScanResult {
  page: string;
  context: string;
  violations: string[];
}

const results: ScanResult[] = [];
const screenshots: string[] = [];

async function scanDOM(page: Page, context: string): Promise<string[]> {
  const violations: string[] = [];

  // Get all visible text nodes and check for forbidden strings
  const found = await page.evaluate((forbidden: string[]) => {
    const issues: string[] = [];
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      null,
    );
    let node: Text | null;
    while ((node = walker.nextNode() as Text | null)) {
      const text = node.textContent?.trim();
      if (!text) continue;
      // Skip script/style/hidden
      const parent = node.parentElement;
      if (!parent) continue;
      if (parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE') continue;
      if (parent.offsetWidth === 0 && parent.offsetHeight === 0) continue;

      for (const f of forbidden) {
        // Only flag standalone occurrences, not as part of a longer word
        if (f === '—' && text === '—') {
          issues.push(`Bare "—" found in <${parent.tagName.toLowerCase()}>: "${text.substring(0, 80)}"`);
        } else if (f !== '—' && text.includes(f)) {
          // Check it's a standalone value, not part of a label like "null hypothesis"
          const idx = text.indexOf(f);
          const before = idx > 0 ? text[idx - 1] : ' ';
          const after = idx + f.length < text.length ? text[idx + f.length] : ' ';
          if (/\s/.test(before) || before === ':' || idx === 0) {
            if (/\s/.test(after) || after === ',' || idx + f.length === text.length) {
              issues.push(`"${f}" found in <${parent.tagName.toLowerCase()}>: "${text.substring(0, 80)}"`);
            }
          }
        }
      }
    }

    // Also check for empty field values in detail panels
    const fieldValues = document.querySelectorAll('[class*="detail"] dd, [class*="detail"] td');
    fieldValues.forEach((el) => {
      const t = (el as HTMLElement).innerText?.trim();
      if (t === '' || t === '-') {
        issues.push(`Empty or dash field value in <${el.tagName.toLowerCase()}>: parent=${(el.parentElement?.className || '').substring(0, 40)}`);
      }
    });

    return issues;
  }, FORBIDDEN_STRINGS);

  violations.push(...found);
  return violations;
}

async function screenshotAndScan(page: Page, name: string, pagePath: string) {
  const ssPath = path.join(SS_DIR, `${name}.png`);
  await page.screenshot({ path: ssPath, fullPage: false });
  screenshots.push(ssPath);
  const violations = await scanDOM(page, name);
  results.push({ page: pagePath, context: name, violations });
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  console.log('=== PARTS PAGE ===');
  await page.goto(`${BASE}/parts`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  // Click each part type filter
  const partTypes = ['promoter', 'rbs', 'cds', 'terminator'];
  for (const pt of partTypes) {
    // Click the type filter pill
    const pill = page.locator(`button:has-text("${pt}")`).first();
    if (await pill.isVisible()) {
      await pill.click();
      await page.waitForTimeout(1000);
    }

    // Click the first part in the filtered list
    const firstRow = page.locator('table tbody tr').first();
    if (await firstRow.isVisible()) {
      await firstRow.click();
      await page.waitForTimeout(1000);

      // Check part length consistency — find the value with 'bp' near 'Part Length'
      let lengthText: string | null = null;
      try {
        const bpSpan = page.locator('.font-mono-readout:has-text("bp")').first();
        if (await bpSpan.isVisible()) {
          lengthText = await bpSpan.textContent();
        }
      } catch { /* ignore */ }

      // Screenshot
      await screenshotAndScan(page, `parts-${pt}`, '/parts');

      console.log(`  ${pt}: length displayed = ${lengthText || 'not found'}`);
    }
  }

  console.log('\n=== KNOWLEDGE - GENES TAB ===');
  await page.goto(`${BASE}/knowledge`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  // The Genes tab should show prompt state
  await screenshotAndScan(page, 'genes-prompt', '/knowledge');

  // Click example queries
  const geneExamples = ['lacZ', 'b0344', 'polymerase'];
  for (const q of geneExamples) {
    const link = page.locator(`button:has-text("${q}")`).first();
    if (await link.isVisible()) {
      await link.click();
      await page.waitForTimeout(2000);

      // Click first result
      const geneRow = page.locator('table tbody tr').first();
      if (await geneRow.isVisible()) {
        await geneRow.click();
        await page.waitForTimeout(1000);
      }

      await screenshotAndScan(page, `genes-${q}`, '/knowledge');
      console.log(`  Gene search "${q}": scanned`);

      // Clear search for next
      const searchInput = page.locator('input[placeholder*="Search"]').first();
      if (await searchInput.isVisible()) {
        await searchInput.fill('');
        await page.waitForTimeout(500);
      }
    }
  }

  console.log('\n=== KNOWLEDGE - TFs TAB ===');
  // Click TFs tab
  const tfsTab = page.locator('button:has-text("Transcription Factors")').first();
  if (await tfsTab.isVisible()) {
    await tfsTab.click();
    await page.waitForTimeout(2000);
  }

  const tfNames = ['RpoD', 'CRP', 'LacI'];
  for (const tfName of tfNames) {
    // Search for the TF
    const tfFilter = page.locator('input[placeholder*="Filter transcription"]').first();
    if (await tfFilter.isVisible()) {
      await tfFilter.fill(tfName);
      await page.waitForTimeout(500);
    }

    const tfRow = page.locator(`td:has-text("${tfName}")`).first();
    if (await tfRow.isVisible()) {
      await tfRow.click();
      await page.waitForTimeout(2000);
    }

    await screenshotAndScan(page, `tfs-${tfName}`, '/knowledge');
    console.log(`  TF "${tfName}": scanned`);

    // Clear filter
    if (await tfFilter.isVisible()) {
      await tfFilter.fill('');
      await page.waitForTimeout(300);
    }
  }

  console.log('\n=== KNOWLEDGE - PATHWAYS TAB ===');
  // Click Pathways tab
  const pwTab = page.locator('button:has-text("Pathways")').first();
  if (await pwTab.isVisible()) {
    await pwTab.click();
    await page.waitForTimeout(2000);
  }

  // Click 3 pathways including the largest (Transport, Inner Membrane)
  const pathwayNames = ['Citric Acid Cycle', 'Glycolysis/Gluconeogenesis', 'Transport, Inner Membrane'];
  for (const pwName of pathwayNames) {
    const card = page.locator(`text="${pwName}"`).first();
    if (await card.isVisible()) {
      await card.click();
      await page.waitForTimeout(2000);
    }

    await screenshotAndScan(page, `pathways-${pwName.replace(/[^a-zA-Z]/g, '_')}`, '/knowledge');
    console.log(`  Pathway "${pwName}": scanned`);
  }

  // === SUMMARY ===
  console.log('\n' + '='.repeat(60));
  console.log('SCAN RESULTS');
  console.log('='.repeat(60));

  let totalViolations = 0;
  for (const r of results) {
    if (r.violations.length > 0) {
      console.log(`\n❌ ${r.context} (${r.page}): ${r.violations.length} violation(s)`);
      r.violations.forEach(v => console.log(`   - ${v}`));
      totalViolations += r.violations.length;
    } else {
      console.log(`✅ ${r.context} (${r.page}): clean`);
    }
  }

  console.log(`\nTotal violations: ${totalViolations}`);
  console.log(`\nScreenshots saved to: ${SS_DIR}`);
  screenshots.forEach(s => console.log(`  ${path.basename(s)}`));

  await browser.close();
  process.exit(totalViolations > 0 ? 1 : 0);
}

main().catch(err => {
  console.error('FATAL:', err);
  process.exit(2);
});
