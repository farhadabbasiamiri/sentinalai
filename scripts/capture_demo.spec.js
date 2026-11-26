const { test } = require('playwright/test');

const screenshots = [
  { name: 'overview', action: async (page) => page.goto('http://127.0.0.1:5173') },
  { name: 'agent-registry', action: async (page) => {
      await page.goto('http://127.0.0.1:5173');
      await page.getByRole('button', { name: 'Agent registry' }).click();
      await page.waitForTimeout(800);
  } },
  { name: 'governance-findings', action: async (page) => {
      await page.goto('http://127.0.0.1:5173');
      await page.getByRole('button', { name: 'Governance findings' }).click();
      await page.waitForTimeout(800);
  } },
  { name: 'reports-evaluation', action: async (page) => {
      await page.goto('http://127.0.0.1:5173');
      await page.getByRole('button', { name: 'Reports & evaluation' }).click();
      await page.waitForTimeout(800);
  } },
];

for (const shot of screenshots) {
  test(`capture ${shot.name}`, async ({ page }) => {
    await shot.action(page);
    await page.screenshot({ path: `docs/screenshots/${shot.name}.png`, fullPage: true });
  });
}
