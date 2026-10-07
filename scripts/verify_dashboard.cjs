const { chromium } = require(
  process.env.PLAYWRIGHT_MODULE || "../frontend/node_modules/playwright",
);
const base = process.env.BASE_URL || "http://127.0.0.1:8000";
const output = require("os").tmpdir();
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  let errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (r.headers()["x-api-key"]) throw Error("Browser sent API key");
  });
  await page.goto(base);
  await page.getByText("● Service ready").waitFor();
  await page
    .getByRole("button", { name: "Late delivery ↗", exact: true })
    .click();
  await page.getByRole("button", { name: "Classify & route ↗" }).click();
  await page.getByTestId("ticket-panel").waitFor();
  await page
    .getByRole("button", { name: "Confirm routing", exact: true })
    .click();
  await page.getByText("Review saved for this session.").waitFor();
  await page
    .getByRole("button", { name: "Live operations", exact: false })
    .click();
  await page.getByTestId("ticket-panel").waitFor();
  await page
    .getByRole("button", { name: "Ticket intake", exact: false })
    .click();
  await page.getByRole("button", { name: "Safety concern ↗" }).click();
  await page.getByRole("button", { name: "Classify & route ↗" }).click();
  await page.getByText("Urgent attention", { exact: true }).waitFor();
  await page
    .getByRole("button", { name: "Support queue", exact: false })
    .click();
  await page.getByTestId("ticket-panel").waitFor();
  await page
    .getByRole("button", { name: "Batch workbench", exact: false })
    .click();
  await page.getByRole("button", { name: "Run batch ↗" }).click();
  await page
    .getByRole("heading", { name: "4 predictions", exact: true })
    .waitFor();
  const tickets = Array.from({ length: 2001 }, (_, i) => ({
    ticket_id: "WEB-" + i,
    channel: "chat",
    text: "My food order is late",
  }));
  await page.getByLabel("Batch request JSON").fill(JSON.stringify({ tickets }));
  await page.getByRole("button", { name: "Run batch ↗" }).click();
  await page
    .getByRole("heading", { name: "2001 predictions", exact: true })
    .waitFor({ timeout: 30000 });
  const downloadPromise = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download JSON ↓", exact: true })
    .click();
  const downloaded = await downloadPromise;
  await downloaded.saveAs(output + "/tensorforge-resolvex-predictions.json");
  const data = JSON.parse(
    require("fs").readFileSync(
      output + "/tensorforge-resolvex-predictions.json",
    ),
  );
  if (
    data.predictions.length !== 2001 ||
    data.predictions[2000].ticket_id !== "WEB-2000"
  )
    throw Error("Incomplete download");
  await page.getByRole("button", { name: "Model lab", exact: false }).click();
  await page
    .getByRole("heading", { name: "Secondary Category", exact: true })
    .waitFor();
  await page.screenshot({
    path: output + "/tensorforge-resolvex-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByRole("button", { name: "Ticket intake", exact: false })
    .click();
  await page.screenshot({
    path: output + "/tensorforge-resolvex-mobile.png",
    fullPage: true,
  });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > innerWidth,
  );
  if (overflow || errors.length)
    throw Error(JSON.stringify({ overflow, errors }));
  const auth = await page.request.post(base + "/predict", {
    data: { channel: "chat", text: "late order" },
  });
  if (auth.status() !== 401) throw Error("Canonical endpoint open");
  console.log(
    JSON.stringify({
      single: true,
      review: true,
      urgentQueue: true,
      syncBatch: 4,
      asyncBatch: 2001,
      downloadOrdered: true,
      threeModelLab: true,
      mobileOverflow: false,
      browserErrors: errors,
      unauthorizedStatus: auth.status(),
    }),
  );
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
