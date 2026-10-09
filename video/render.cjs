// Renders [[html, png], ...] at 1920x1080.
const { chromium } = require(require("path").join(__dirname, "../frontend/node_modules/playwright"));
const jobs = JSON.parse(require("fs").readFileSync(process.argv[2], "utf8"));
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  for (const [html, png] of jobs) {
    await p.goto("file://" + html);
    await p.evaluate(() => document.fonts.ready);
    await p.screenshot({ path: png });
  }
  await b.close();
})().catch((e) => { console.error(e); process.exit(1); });
