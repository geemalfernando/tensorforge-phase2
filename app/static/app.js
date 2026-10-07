const form = document.querySelector("#classify-form");
const textField = document.querySelector("#text");
const count = document.querySelector("#char-count");
const keyDialog = document.querySelector("#key-dialog");
const keyField = document.querySelector("#api-key");
const errorBox = document.querySelector("#form-error");
const classifyButton = document.querySelector("#classify-button");
const keyButton = document.querySelector("#open-key");
const batchEditor = document.querySelector("#batch-json");
const batchError = document.querySelector("#batch-error");
const runBatchButton = document.querySelector("#run-batch");
let apiKey = "";
let lastPrediction = null;
let healthRequest = null;
let activeBatchJobId = null;
let batchCancelled = false;
let batchPredictions = null;
let sessionCounts = { total: 0, urgent: 0, review: 0 };
let batchFilter = "all";

function recordActivity(predictions) {
  sessionCounts.total += predictions.length;
  sessionCounts.urgent += predictions.filter((p) => p.is_urgent).length;
  sessionCounts.review += predictions.filter((p) => p.needs_human_review).length;
  for (const [name, value] of Object.entries(sessionCounts)) {
    document.querySelector(`#session-${name}`).textContent = value.toLocaleString();
  }
}

function renderBatchResults() {
  if (!batchPredictions) return;
  document.querySelector("#batch-results").hidden = false;
  const filtered = batchPredictions.filter((p) =>
    batchFilter === "urgent" ? p.is_urgent : batchFilter === "review" ? p.needs_human_review : true,
  );
  document.querySelector("#batch-results-summary").textContent = `${filtered.length.toLocaleString()} TICKETS`;
  const rows = document.querySelector("#batch-results-body");
  rows.replaceChildren();
  for (const prediction of filtered.slice(0, 100)) {
    const row = document.createElement("tr");
    const values = [prediction.ticket_id, titleCase(prediction.category), `${Math.round(prediction.confidence * 100)}%`,
      prediction.is_urgent ? "Urgent" : "Standard"];
    for (const [index, value] of values.entries()) {
      const cell = document.createElement("td");
      cell.textContent = value;
      if (index === 1) {
        const team = document.createElement("small");
        team.textContent = prediction.team;
        cell.append(team);
      }
      if (index === 3) {
        cell.className = prediction.is_urgent ? "urgent-value" : "safe-value";
        if (prediction.needs_human_review) {
          const review = document.createElement("small");
          review.textContent = "Human review recommended";
          cell.append(review);
        }
      }
      row.append(cell);
    }
    rows.append(row);
  }
  document.querySelector("#batch-results-note").textContent = filtered.length
    ? `Showing ${Math.min(100, filtered.length)} of ${filtered.length.toLocaleString()} matching tickets. Download JSON for all predictions.`
    : "No tickets match this filter.";
}

function completeBatch() {
  recordActivity(batchPredictions);
  renderBatchResults();
}

const examples = {
  delay: {
    channel: "chat",
    subject: "",
    text: "bro mage order eka hour ekakata wada late, driver call ganne na. refund ekak denna",
  },
  "lost-item": {
    channel: "chat",
    subject: "",
    text: "කාර් එකේ මගේ බෑග් එක අමතක වුණා, ඩ්‍රයිවර්ට කතා කරන්න පුළුවන්ද?",
  },
  urgent: {
    channel: "email",
    subject: "Urgent: insulin pack not delivered",
    text: "Hello, my father is diabetic and the insulin pack in my order has not arrived. The rider's phone is off. Kindly advise.",
  },
};
const batchExample = {
  tickets: [
    {
      ticket_id: "TF-DEMO-001",
      channel: "chat",
      subject: "",
      text: "My order is over an hour late. Please refund the delivery fee.",
    },
    {
      ticket_id: "TF-DEMO-002",
      channel: "chat",
      subject: "",
      text: "I left my backpack in the car. Could you contact the driver?",
    },
  ],
};

function showKeyDialog(message = "") {
  keyField.value = apiKey;
  const keyError = document.querySelector("#key-error");
  keyError.textContent = message;
  keyError.hidden = !message;
  if (!keyDialog.open) keyDialog.showModal();
  requestAnimationFrame(() => keyField.focus());
}

async function setServiceHealth() {
  if (healthRequest) healthRequest.abort();
  healthRequest = new AbortController();
  try {
    const response = await fetch("/health", { signal: healthRequest.signal });
    const body = await response.json();
    const healthy = response.ok && body.status === "ok";
    document.querySelector("#sidebar-health").textContent = healthy ? "Model is online" : "Model unavailable";
    document.querySelector(".status-light").classList.toggle("online", healthy);
    document.querySelector("#service-status").textContent = healthy ? "Online" : "Offline";
    document.querySelector(".big-status-dot").classList.toggle("online", healthy);
    document.querySelector("#service-status-caption").textContent = healthy
      ? "Ready to classify tickets"
      : "Check model deployment";
    document.querySelector("#model-version").textContent = body.model_version || "Model loading";
    document.querySelector(".version-dot").classList.toggle("online", healthy);
  } catch (error) {
    if (error.name === "AbortError") return;
    document.querySelector("#sidebar-health").textContent = "API unavailable";
    document.querySelector("#service-status").textContent = "Offline";
    document.querySelector("#service-status-caption").textContent = "Could not reach the API";
  }
}

function setKeyConnected(connected) {
  keyButton.classList.toggle("connected", connected);
  keyButton.innerHTML = connected
    ? '<span class="key-connected-dot"></span> Key connected <span class="key-icon">Change</span>'
    : 'Connect API key <span class="key-icon">Secure</span>';
}

function titleCase(value) {
  return value.replaceAll("_", " ").replace(/\b[a-z]/g, (letter) => letter.toUpperCase());
}

function clearResult() {
  lastPrediction = null;
  document.querySelector("#result-empty").hidden = false;
  document.querySelector("#result-content").hidden = true;
}

function setFormMessage(message) {
  errorBox.textContent = message;
  errorBox.hidden = !message;
}

function setBatchError(message) {
  batchError.textContent = message;
  batchError.hidden = !message;
}

function setBatchProgress(status, processed, total, message) {
  document.querySelector("#batch-progress").hidden = false;
  document.querySelector("#batch-status").textContent = status;
  document.querySelector("#batch-progress-count").textContent = `${processed} / ${total}`;
  document.querySelector("#batch-progress-message").textContent = message;
  document.querySelector("#batch-progress-fill").style.width =
    `${total ? Math.min(100, (processed / total) * 100) : 0}%`;
}

function updateBatchCount() {
  try {
    const payload = JSON.parse(batchEditor.value);
    const tickets = payload?.tickets;
    const count = Array.isArray(tickets) ? tickets.length : 0;
    const suffix = count === 1 ? "ticket" : "tickets";
    document.querySelector("#batch-count").textContent = count
      ? `${count.toLocaleString()} ${suffix} · ${count > 100 ? "background job" : "ready to run"}`
      : "Add at least one ticket";
    document.querySelector("#batch-count").classList.remove("invalid-count");
  } catch {
    document.querySelector("#batch-count").textContent = "JSON needs attention";
    document.querySelector("#batch-count").classList.add("invalid-count");
  }
}

async function authorizedFetch(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      "X-API-Key": apiKey,
    },
  });
  if (response.status === 401) {
    apiKey = "";
    setKeyConnected(false);
    showKeyDialog("Your API key was rejected. Reconnect to continue.");
  }
  return response;
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function fetchJobPredictions(jobId, total) {
  const response = await authorizedFetch(
    `/batch/jobs/${encodeURIComponent(jobId)}/results?offset=0&limit=5000`,
  );
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error?.message || "Could not download batch results.");
  }
  batchPredictions = body.predictions;
  completeBatch();
  setBatchProgress(
    "Batch complete",
    total,
    total,
    `${batchPredictions.length.toLocaleString()} predictions are ready to download.`,
  );
  document.querySelector("#download-batch").hidden = false;
  document.querySelector("#cancel-batch").hidden = true;
}

async function pollBatchJob(jobId, total) {
  activeBatchJobId = jobId;
  batchCancelled = false;
  document.querySelector("#cancel-batch").hidden = false;
  const deadline = Date.now() + 31 * 60 * 1000;
  while (!batchCancelled && Date.now() < deadline) {
    await sleep(2000);
    if (batchCancelled) return;
    const response = await authorizedFetch(`/batch/jobs/${encodeURIComponent(jobId)}`);
    const status = await response.json();
    if (!response.ok) {
      throw new Error(status.error?.message || "Could not read batch job status.");
    }
    if (status.status === "succeeded") {
      await fetchJobPredictions(jobId, total);
      return;
    }
    if (status.status === "failed" || status.status === "cancelled") {
      throw new Error(
        status.error?.message || `The batch job ${status.status}. No results are available.`,
      );
    }
    const elapsed = status.started_at
      ? ` · Started ${new Date(status.started_at).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })}`
      : "";
    setBatchProgress(
      status.status === "queued" ? "Waiting in queue" : "Classifying tickets",
      status.processed,
      status.total,
      `Job ${status.job_id.slice(0, 8)}…${elapsed}`,
    );
  }
  if (!batchCancelled) throw new Error("Polling timed out. The job may still be running.");
}

async function runBatch() {
  setBatchError("");
  try {
    const payload = JSON.parse(batchEditor.value);
    const tickets = payload?.tickets;
    if (!Array.isArray(tickets) || tickets.length < 1 || tickets.length > 5000) {
      throw new Error("Add between 1 and 5,000 tickets to the tickets array.");
    }
    const payloadBytes = new TextEncoder().encode(JSON.stringify(payload)).byteLength;
    const maxBytes = tickets.length <= 100 ? 5 * 1024 * 1024 : 25 * 1024 * 1024;
    if (payloadBytes > maxBytes) {
      throw new Error(
        `This request is ${Math.ceil(payloadBytes / (1024 * 1024))} MB. The ${
          tickets.length <= 100 ? "synchronous batch" : "job"
        } limit is ${maxBytes / (1024 * 1024)} MB.`,
      );
    }
    if (!apiKey) {
      showKeyDialog();
      throw new Error("Connect your team API key before running a batch.");
    }

    batchPredictions = null;
    document.querySelector("#batch-results").hidden = true;
    document.querySelector("#download-batch").hidden = true;
    document.querySelector("#batch-progress").hidden = false;
    runBatchButton.disabled = true;
    runBatchButton.setAttribute("aria-busy", "true");
    runBatchButton.innerHTML = '<span class="loading-spinner"></span> Starting batch…';
    setBatchProgress("Submitting batch", 0, tickets.length, "Validating tickets before inference.");

    if (tickets.length <= 100) {
      const response = await authorizedFetch("/predict/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await response.json();
      if (!response.ok) {
        const error = body.error;
        if (error?.details?.length) {
          const first = error.details[0];
          throw new Error(
            `Ticket ${Number.isInteger(first.index) ? first.index + 1 : ""} ${first.field || ""}: ${first.issue || error.message}`.trim(),
          );
        }
        throw new Error(error?.message || "Could not classify this batch.");
      }
      batchPredictions = body.predictions;
      completeBatch();
      setBatchProgress(
        "Batch complete",
        batchPredictions.length,
        tickets.length,
        `${batchPredictions.length.toLocaleString()} predictions are ready to download.`,
      );
      document.querySelector("#download-batch").hidden = false;
      return;
    }

    const response = await authorizedFetch("/batch/jobs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      "Idempotency-Key": crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      },
      body: JSON.stringify(payload),
    });
    const job = await response.json();
    if (!response.ok) {
      throw new Error(job.error?.message || "Could not submit the batch job.");
    }
    setBatchProgress("Batch accepted", job.processed, job.total, "Background classification started.");
    await pollBatchJob(job.job_id, tickets.length);
  } catch (error) {
    setBatchError(error.message || "Could not run this batch.");
    if (!document.querySelector("#batch-progress").hidden && !batchPredictions) {
      document.querySelector("#batch-status").textContent = "Needs attention";
      document.querySelector("#cancel-batch").hidden = true;
    }
  } finally {
    activeBatchJobId = null;
    runBatchButton.disabled = false;
    runBatchButton.removeAttribute("aria-busy");
    runBatchButton.innerHTML =
      '<span class="button-spark">✳</span> Run batch <span class="button-arrow">↗</span>';
  }
}

function markResultStale() {
  if (!lastPrediction) return;
  document.querySelector("#result-intro").textContent =
    "This is the previous result. Classify again to update the routing.";
  document.querySelector("#result-content").classList.add("result-stale");
}

function renderPrediction(prediction) {
  lastPrediction = prediction;
  document.querySelector("#result-empty").hidden = true;
  document.querySelector("#result-content").hidden = false;
  document.querySelector("#result-content").classList.remove("result-stale");
  document.querySelector("#result-intro").textContent =
    "Recommended routing based on the message you submitted.";
  document.querySelector("#result-category").textContent = titleCase(prediction.category);
  document.querySelector("#result-team").textContent = prediction.team;
  const confidence = Math.round(prediction.confidence * 100);
  document.querySelector("#result-confidence").textContent = `${confidence}%`;
  document.querySelector("#confidence-fill").style.width = `${confidence}%`;
  document.querySelector("#result-secondary").textContent = prediction.secondary_category
    ? titleCase(prediction.secondary_category)
    : "None detected";
  const urgent = document.querySelector("#result-urgent");
  urgent.textContent = prediction.is_urgent ? "Immediate attention" : "Standard queue";
  urgent.className = prediction.is_urgent ? "urgent-value" : "safe-value";
  document.querySelector("#review-row").hidden = !prediction.needs_human_review;
  document.querySelector("#result-version").textContent = prediction.model_version;
  document.querySelector("#result-panel").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function setGreeting() {
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  document.querySelector("#greeting").innerHTML =
    `${greeting}<span class="heading-period">.</span>`;
}

function syncChannelFields() {
  const email = form.elements.channel.value === "email";
  document.querySelector("#subject-field").hidden = !email;
}

function updateCount() {
  const length = textField.value.length;
  count.textContent = length.toLocaleString();
  count.classList.toggle("near-limit", length >= 9000);
  count.classList.toggle("at-limit", length >= 9900);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setFormMessage("");
  const ticket = {
    channel: form.elements.channel.value,
    subject: form.elements.subject.value,
    text: textField.value,
  };
  if (form.elements.ticket_id.value.trim()) {
    ticket.ticket_id = form.elements.ticket_id.value.trim();
  }
  if (!ticket.text.trim()) {
    setFormMessage("Add a customer message before classifying.");
    textField.focus();
    return;
  }
  if (!apiKey) {
    setFormMessage("Connect your team API key to classify this ticket.");
    showKeyDialog();
    return;
  }

  classifyButton.disabled = true;
  classifyButton.innerHTML = '<span class="loading-spinner"></span> Analyzing ticket…';
  classifyButton.setAttribute("aria-busy", "true");
  let rejectedKey = false;
  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify(ticket),
    });
    const body = await response.json();
    if (response.status === 401) {
      apiKey = "";
      setKeyConnected(false);
      rejectedKey = true;
      throw new Error("That key was not accepted. Check it and connect again.");
    }
    if (!response.ok) {
      throw new Error(body.error?.message || "Could not classify this ticket.");
    }
    renderPrediction(body);
    recordActivity([body]);
  } catch (error) {
    setFormMessage(error.message || "Could not reach the classification service.");
    if (rejectedKey) showKeyDialog("That key was not accepted. Check it and try again.");
  } finally {
    classifyButton.disabled = false;
    classifyButton.removeAttribute("aria-busy");
    classifyButton.innerHTML = '<span class="button-spark">✳</span> Classify ticket <span class="button-arrow">↗</span>';
  }
});

textField.addEventListener("input", () => {
  updateCount();
  markResultStale();
});
form.elements.subject.addEventListener("input", markResultStale);
form.elements.ticket_id.addEventListener("input", markResultStale);
form.elements.channel.addEventListener("change", () => {
  syncChannelFields();
  markResultStale();
});
document.querySelector("#clear-form").addEventListener("click", () => {
  form.reset();
  syncChannelFields();
  updateCount();
  setFormMessage("");
  clearResult();
  form.elements.channel.focus();
});
document.querySelectorAll(".example-chip").forEach((button) => {
  button.addEventListener("click", () => {
    const example = examples[button.dataset.example];
    form.elements.channel.value = example.channel;
    form.elements.subject.value = example.subject;
    syncChannelFields();
    textField.value = example.text;
    form.elements.ticket_id.value = "";
    updateCount();
    setFormMessage("");
    clearResult();
    textField.focus();
  });
});
document.querySelector("#open-key").addEventListener("click", () => showKeyDialog());
document.querySelector("#save-key").addEventListener("click", async (event) => {
  const candidate = keyField.value.trim();
  const keyError = document.querySelector("#key-error");
  if (!candidate) {
    keyError.textContent = "Enter your API key to connect.";
    keyError.hidden = false;
    return;
  }
  const button = event.currentTarget;
  button.disabled = true;
  button.textContent = "Verifying…";
  try {
    const response = await fetch("/auth/verify", { method: "POST", headers: { "X-API-Key": candidate } });
    if (!response.ok) {
      const body = await response.json();
      throw new Error(body.error?.message || "Could not verify API access.");
    }
    apiKey = candidate;
    setKeyConnected(true);
    keyField.value = "";
    keyField.type = "password";
    document.querySelector("#toggle-key").textContent = "Show";
    document.querySelector("#toggle-key").setAttribute("aria-label", "Show API key");
    keyDialog.close();
    setFormMessage("");
    setBatchError("");
  } catch (error) {
    keyError.textContent = error.message || "Could not reach the API.";
    keyError.hidden = false;
  } finally {
    button.disabled = false;
    button.innerHTML = 'Use key <span class="button-arrow">↗</span>';
  }
});
document.querySelector("#clear-key").addEventListener("click", () => {
  apiKey = "";
  keyField.value = "";
  setKeyConnected(false);
  keyDialog.close();
});
document.querySelector("#toggle-key").addEventListener("click", (event) => {
  const visible = keyField.type === "text";
  keyField.type = visible ? "password" : "text";
  event.currentTarget.textContent = visible ? "Show" : "Hide";
  event.currentTarget.setAttribute("aria-label", visible ? "Show API key" : "Hide API key");
});
document.querySelector("#copy-result").addEventListener("click", async (event) => {
  if (!lastPrediction) return;
  const button = event.currentTarget;
  try {
    await navigator.clipboard.writeText(JSON.stringify(lastPrediction, null, 2));
    button.textContent = "Copied";
    setTimeout(() => (button.textContent = "Copy JSON"), 1200);
  } catch {
    button.textContent = "Copy blocked";
    setTimeout(() => (button.textContent = "Copy JSON"), 1600);
  }
});

document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    if (keyDialog.open) return;
    if (!document.querySelector("#batch-mode").hidden) {
      if (!runBatchButton.disabled) runBatch();
    } else if (!classifyButton.disabled) form.requestSubmit();
  }
});

document.querySelectorAll(".nav-item").forEach((link) => {
  link.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
    link.classList.add("active");
  });
});

document.querySelectorAll(".mode-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const singleSelected = tab.id === "single-tab";
    document.querySelector("#single-tab").classList.toggle("active", singleSelected);
    document.querySelector("#batch-tab").classList.toggle("active", !singleSelected);
    document.querySelector("#single-tab").setAttribute("aria-selected", String(singleSelected));
    document.querySelector("#batch-tab").setAttribute("aria-selected", String(!singleSelected));
    document.querySelector("#single-mode").hidden = !singleSelected;
    document.querySelector("#batch-mode").hidden = singleSelected;
    if (singleSelected) textField.focus();
    else batchEditor.focus();
  });
});

batchEditor.value = JSON.stringify(batchExample, null, 2);
batchEditor.addEventListener("input", updateBatchCount);
document.querySelector("#batch-example").addEventListener("click", () => {
  batchEditor.value = JSON.stringify(batchExample, null, 2);
  updateBatchCount();
  setBatchError("");
});
document.querySelector("#batch-file").addEventListener("change", async (event) => {
  const file = event.currentTarget.files?.[0];
  event.currentTarget.value = "";
  if (!file) return;
  if (file.size > 25 * 1024 * 1024) {
    setBatchError("Choose a JSON file smaller than 25 MB.");
    return;
  }
  try {
    const text = await file.text();
    JSON.parse(text);
    batchEditor.value = text;
    updateBatchCount();
    setBatchError("");
  } catch {
    setBatchError("That file is not valid JSON. Check it and try again.");
  }
});
document.querySelector("#run-batch").addEventListener("click", runBatch);
document.querySelector("#cancel-batch").addEventListener("click", async (event) => {
  if (!activeBatchJobId) return;
  const cancelButton = event.currentTarget;
  batchCancelled = true;
  cancelButton.disabled = true;
  try {
    const response = await authorizedFetch(
      `/batch/jobs/${encodeURIComponent(activeBatchJobId)}`,
      { method: "DELETE" },
    );
    if (!response.ok && response.status !== 404) {
      const body = await response.json();
      throw new Error(body.error?.message || "Could not cancel the batch job.");
    }
    setBatchProgress("Job cancelled", 0, 0, "The job was cancelled. No results were downloaded.");
  } catch (error) {
    batchCancelled = false;
    setBatchError(error.message || "Could not cancel the batch job.");
  } finally {
    cancelButton.hidden = true;
    cancelButton.disabled = false;
  }
});
document.querySelector("#download-batch").addEventListener("click", () => {
  if (!batchPredictions) return;
  const data = JSON.stringify(
    {
      model_version: document.querySelector("#model-version").textContent,
      count: batchPredictions.length,
      predictions: batchPredictions,
    },
    null,
    2,
  );
  const url = URL.createObjectURL(new Blob([data], { type: "application/json" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "tensorforge-predictions.json";
  anchor.click();
  URL.revokeObjectURL(url);
});

document.querySelector("#current-date").textContent = new Intl.DateTimeFormat("en", {
  weekday: "short",
  month: "short",
  day: "numeric",
  year: "numeric",
}).format(new Date());
setGreeting();
syncChannelFields();
updateCount();
updateBatchCount();
setServiceHealth();
setInterval(setServiceHealth, 30000);

document.querySelector("#reset-session").addEventListener("click", () => {
  sessionCounts = { total: 0, urgent: 0, review: 0 };
  recordActivity([]);
});
document.querySelectorAll(".result-filter").forEach((button) => {
  button.addEventListener("click", () => {
    batchFilter = button.dataset.filter;
    document.querySelectorAll(".result-filter").forEach((item) => {
      const active = item === button;
      item.classList.toggle("active", active);
      item.setAttribute("aria-pressed", String(active));
    });
    renderBatchResults();
  });
});
