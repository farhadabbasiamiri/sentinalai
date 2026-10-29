const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const outDir = path.resolve(__dirname, '..', 'docs', 'screenshots');
  fs.mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });

  const shots = [
    { name: 'overview', action: async () => { await page.goto('http://127.0.0.1:5173'); } },
    { name: 'agent-registry', action: async () => {
        await page.goto('http://127.0.0.1:5173');
        await page.getByRole('button', { name: 'Agent registry' }).click();
        await page.waitForTimeout(800);
    } },
    { name: 'governance-findings', action: async () => {
        await page.goto('http://127.0.0.1:5173');
        await page.getByRole('button', { name: 'Governance findings' }).click();
        await page.waitForTimeout(800);
    } },
    { name: 'reports-evaluation', action: async () => {
        await page.goto('http://127.0.0.1:5173');
        await page.getByRole('button', { name: 'Reports & evaluation' }).click();
        await page.waitForTimeout(800);
    } },
  ];

  for (const shot of shots) {
    await shot.action();
    const outPath = path.join(outDir, `${shot.name}.png`);
    await page.screenshot({ path: outPath, fullPage: true });
    console.log(`Saved ${outPath}`);
  }

  await browser.close();
  console.log('Captured screenshots into docs/screenshots');
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
