// Records the live dashboard scenes as 1920x1080 JPEG frames via the Chrome DevTools screencast.
// usage: node live.cjs <base_url> <durations.json> <out_dir> [probe]
// durations.json: {"scene_id": [beat_seconds, ...], ...}; writes <out_dir>/frames/*.jpg and <out_dir>/timeline.json
const { chromium, devices } = require(require("path").join(__dirname, "../frontend/node_modules/playwright"));
const fs = require("fs");
const path = require("path");

const [base, durFile, out, probe] = process.argv.slice(2);
const durations = JSON.parse(fs.readFileSync(durFile, "utf8"));
const GAP = 0.35;
fs.mkdirSync(path.join(out, "frames"), { recursive: true });

const SINGLISH = "bro mage order eka hour ekakata wada late, driver call ganne na. refund ekak denna";
const EMAIL_SUBJECT = "Re: Order #48213";
const EMAIL_TEXT = "Hello, my father is diabetic and the insulin pack in my order has not arrived. The rider's phone is off. Kindly advise.";
const MOBILE_TEXT = "Driver took a long route and charged me double. The app also shows the ride as not completed. Please refund";
const jobTickets = Array.from({ length: 100 }, (_, i) => ({
  ticket_id: "EVAL-" + String(i).padStart(4, "0"),
  channel: ["chat", "email", "call_transcript"][i % 3],
  text: ["my order is two hours late and the rider is not answering", "charged twice for one ride, please refund",
         "I left my phone in the car, can you contact the driver", "app crashes every time I open checkout",
         "kaama eka narakai, smell ekak enawa"][i % 5] + " #" + i,
}));

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1.2, acceptDownloads: true });
  let page = await context.newPage();
  let frameNo = 0;
  const frames = [];
  // Each page gets its own screencast session; frames from all of them share one timeline.
  async function screencast(pg, size) {
    const session = await pg.context().newCDPSession(pg);
    session.on("Page.screencastFrame", async ({ data, metadata, sessionId }) => {
      const name = String(frameNo++).padStart(6, "0") + ".jpg";
      fs.writeFileSync(path.join(out, "frames", name), Buffer.from(data, "base64"));
      frames.push({ name, t: metadata.timestamp });
      try { await session.send("Page.screencastFrameAck", { sessionId }); } catch (e) {}
    });
    await session.send("Page.startScreencast", { format: "jpeg", quality: 88, ...size, everyNthFrame: 1 });
    return session;
  }
  const DESKTOP = { maxWidth: 1920, maxHeight: 1080 };

  const now = () => Date.now() / 1000;
  const sleep = (ms) => page.waitForTimeout(ms);
  async function moveTo(loc) {
    await loc.scrollIntoViewIfNeeded();
    const b = await loc.boundingBox();
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 25 });
    await sleep(180);
  }
  async function click(loc) { await moveTo(loc); await loc.click(); }
  async function typeInto(loc, text, delay = 32) { await click(loc); await loc.fill(""); await loc.pressSequentially(text, { delay }); }
  async function scrollTo(y) { await page.evaluate((y) => window.scrollTo({ top: y, behavior: "smooth" }), y); await sleep(900); }
  async function scrollToEl(loc) {
    await page.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "center" }), await loc.elementHandle());
    await sleep(900);
  }
  const nav = (name) => page.getByRole("navigation", { name: "Workspace navigation" }).getByRole("button", { name, exact: false });
  const classify = async () => {
    await click(page.getByRole("button", { name: "Classify & route ↗" }));
    await page.getByRole("button", { name: "Classify & route ↗" }).waitFor({ timeout: 60000 });
    await page.getByTestId("ticket-panel").waitFor();
    await sleep(700);
  };

  const ACTIONS = {
    demo_intake: [
      async () => {
        await page.goto(base + "/");
        await page.getByText("Service ready").first().waitFor();
        await sleep(1200);
        await page.mouse.move(400, 300, { steps: 30 });
        await sleep(1500);
        await moveTo(page.getByText("Service ready").first());
        await sleep(1200);
        await moveTo(page.getByRole("button", { name: /Open your desk/ }));
      },
      async () => {
        await click(page.getByRole("button", { name: /Open your desk/ }));
        await sleep(900);
        await typeInto(page.getByPlaceholder("TF-1048"), "TF-DEMO-001", 60);
        await typeInto(page.getByPlaceholder(/For example/), SINGLISH, 38);
      },
      async () => {
        await classify();
        await scrollToEl(page.getByTestId("ticket-panel"));
        await sleep(1500);
        await moveTo(page.getByTestId("ticket-panel").getByText("Delivery Operations").first());
      },
      async () => {
        await scrollTo(0);
        await click(page.getByRole("button", { name: "Safety concern ↗" }));
        await typeInto(page.getByPlaceholder("TF-1048"), "TF-DEMO-002", 40);
        await sleep(600);
        await classify();
        await page.getByText("Urgent attention", { exact: true }).first().waitFor();
        await scrollToEl(page.getByTestId("ticket-panel"));
      },
      async () => {
        await scrollTo(0);
        await click(page.getByRole("button", { name: "Tamil message ↗" }));
        await typeInto(page.getByPlaceholder("TF-1048"), "TF-DEMO-003", 40);
        await sleep(600);
        await classify();
        await scrollToEl(page.getByTestId("ticket-panel"));
      },
    ],
    demo_ops: [
      async () => {
        await scrollTo(0);
        await click(nav("Live operations"));
        await sleep(1200);
        await scrollTo(500);
        await sleep(1500);
        await scrollTo(0);
      },
      async () => {
        await click(nav("Support queue"));
        await sleep(1000);
        await typeInto(page.locator("input[type=password]"), process.env.SUPPORT_PASSWORD || "demo-support", 70);
        await click(page.getByRole("button", { name: "Sign in as support" }));
        await page.getByText("Support role").first().waitFor();
        await sleep(1200);
        await scrollTo(450);
      },
      async () => {
        const accept = page.getByRole("button", { name: "Accept ticket" }).first();
        await scrollToEl(accept);
        await typeInto(page.getByPlaceholder("Optional review note").first(), "Checked with the customer: escalate now.", 35);
        await click(accept);
        await page.getByText("Accepted by support").first().waitFor();
        await scrollToEl(page.getByText("Accepted by support").first());
      },
    ],
    demo_judge: [
      async () => {
        await scrollTo(0);
        await click(nav("Judge demo"));
        await page.getByRole("heading", { name: "What the judges evaluate" }).waitFor();
        await sleep(800);
        await scrollToEl(page.getByRole("heading", { name: "What the judges evaluate" }));
        await sleep(2500);
        await page.evaluate(() => window.scrollBy({ top: 350, behavior: "smooth" }));
      },
      async () => {
        await scrollToEl(page.getByRole("heading", { name: "Routes in the evaluation contract" }));
        await sleep(1500);
        await page.evaluate(() => window.scrollBy({ top: 250, behavior: "smooth" }));
      },
      async () => {
        const key = page.getByLabel("Evaluation API key");
        await scrollToEl(key);
        await typeInto(key, process.env.JUDGE_API_KEY, 60);
        await click(page.getByRole("button", { name: "Verify key & open demo" }));
        await page.getByRole("heading", { name: "API evaluation console" }).waitFor({ timeout: 30000 });
        await scrollToEl(page.getByRole("heading", { name: "API evaluation console" }));
      },
      async () => {
        await scrollToEl(page.getByLabel("Single ticket request JSON"));
        await click(page.getByRole("button", { name: "Send prediction" }));
        await page.getByText("HTTP 200").waitFor({ timeout: 30000 });
        await scrollToEl(page.getByText("Latest response"));
      },
      async () => {
        await scrollToEl(page.getByLabel("Judge batch request JSON"));
        await click(page.getByRole("button", { name: "Run synchronous batch" }));
        await page.getByText("POST /predict/batch").waitFor({ timeout: 30000 });
        await scrollToEl(page.getByText("Latest response"));
        await sleep(1200);
        await page.evaluate(() => window.scrollBy({ top: 300, behavior: "smooth" }));
      },
    ],
    demo_batch: [
      async () => {
        await scrollTo(0);
        await click(nav("Batch workbench"));
        await sleep(900);
        await click(page.getByRole("button", { name: "Load sample" }));
        await scrollToEl(page.getByLabel("Batch request JSON"));
      },
      async () => {
        await click(page.getByRole("button", { name: "Run batch ↗" }));
        await page.getByRole("heading", { name: "4 predictions", exact: true }).waitFor();
        await scrollToEl(page.getByRole("heading", { name: "4 predictions", exact: true }));
        await scrollTo(1200);
      },
      async () => {
        await scrollTo(0);
        await scrollToEl(page.getByLabel("Batch request JSON"));
        await page.getByLabel("Batch request JSON").fill(JSON.stringify({ tickets: jobTickets }));
        await sleep(1200);
        await click(page.getByRole("button", { name: "Run batch ↗" }));
        await page.getByRole("heading", { name: "100 predictions", exact: true }).waitFor({ timeout: 120000 });
      },
      async () => {
        await scrollToEl(page.getByRole("heading", { name: "100 predictions", exact: true }));
        const dl = page.waitForEvent("download");
        await click(page.getByRole("button", { name: "Download JSON ↓" }).last());
        await (await dl).saveAs(path.join(out, "predictions-100.json"));
        await scrollTo(1400);
      },
    ],
    demo_mobile: [
      async () => {
        await page.goto(base + "/");
        await page.getByText("Service ready").first().waitFor();
        await sleep(1500);
        await scrollTo(700);
        await sleep(1200);
        await scrollTo(1500);
        await sleep(1000);
        await scrollTo(0);
      },
      async () => {
        await click(page.getByRole("button", { name: /Open your desk/ }));
        await sleep(900);
        await typeInto(page.getByPlaceholder("TF-1048"), "TF-MOBILE-01", 60);
        await typeInto(page.getByPlaceholder(/For example/), MOBILE_TEXT, 30);
      },
      async () => {
        await classify();
        await scrollToEl(page.getByTestId("ticket-panel"));
        await sleep(2200);
        await page.evaluate(() => window.scrollBy({ top: 500, behavior: "smooth" }));
        await sleep(1500);
      },
    ],
  };

  const MOBILE = new Set(["demo_mobile"]);
  const only = process.env.ONLY ? new Set(process.env.ONLY.split(",")) : null;
  let cdp = await screencast(page, DESKTOP);
  const timeline = {};
  if (!process.env.JUDGE_API_KEY) throw new Error("JUDGE_API_KEY is required to record the Judge demo console");
  for (const scene of Object.keys(ACTIONS)) {
    if (only && !only.has(scene)) continue;
    let desktopPage;
    if (MOBILE.has(scene)) {
      await cdp.send("Page.stopScreencast");
      desktopPage = page;
      page = await (await browser.newContext({ ...devices["iPhone 14 Pro"] })).newPage();
      cdp = await screencast(page, { maxWidth: 1080, maxHeight: 1920 });
    }
    const beats = [];
    const durs = durations[scene] || ACTIONS[scene].map(() => 3);
    for (let i = 0; i < ACTIONS[scene].length; i++) {
      const start = now();
      await ACTIONS[scene][i]();
      const actionEnd = now();
      const target = start + durs[i] + GAP;
      if (target > now()) await sleep((target - now()) * 1000);
      beats.push({ start, actionEnd, end: now() });
      if (probe) await page.screenshot({ path: path.join(out, `probe-${scene}-${i}.png`) });
    }
    timeline[scene] = beats;
    if (desktopPage) {
      await cdp.send("Page.stopScreencast");
      await page.context().close();
      page = desktopPage;
      cdp = await screencast(page, DESKTOP);
    }
  }
  await sleep(500);
  await cdp.send("Page.stopScreencast");
  await sleep(300);
  fs.writeFileSync(path.join(out, "timeline.json"), JSON.stringify({ timeline, frames }, null, 1));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
