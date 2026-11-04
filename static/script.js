// Frontend for the Bug Tracker. Talks to the Flask JSON API with fetch().
const $ = (id) => document.getElementById(id);

const els = {
  id: $("bug-id"), title: $("title"), description: $("description"),
  severity: $("severity"), status: $("status"),
  save: $("save-btn"), cancel: $("cancel-btn"), error: $("form-error"),
  formTitle: $("form-title"),
  list: $("bugs"), empty: $("empty"),
  search: $("search"), fSeverity: $("filter-severity"), fStatus: $("filter-status"),
};
const STATUSES = ["Open", "In Progress", "Fixed"];

async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 204) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed.");
  return data;
}

function showError(message) {
  els.error.textContent = message;
  els.error.hidden = !message;
}

// Build text with textContent so user input is never treated as HTML.
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderBug(bug) {
  const li = el("li", `bug ${bug.severity} ${bug.status === "Fixed" ? "Fixed" : ""}`);

  const head = el("div", "bug-head");
  const title = el("h3", "bug-title");
  title.append(el("span", "bug-id", `#${bug.id}`), document.createTextNode(bug.title));
  head.append(title, el("span", `sev-${bug.severity}`, bug.severity));
  li.append(head);

  if (bug.description) li.append(el("p", "bug-desc", bug.description));

  const meta = el("div", "bug-meta");
  const select = el("select");
  select.setAttribute("aria-label", `Status of bug ${bug.id}`);
  STATUSES.forEach((s) => {
    const opt = el("option", "", s);
    opt.selected = s === bug.status;
    select.append(opt);
  });
  select.addEventListener("change", () => changeStatus(bug.id, select.value));

  const edit = el("button", "btn small", "Edit");
  edit.type = "button";
  edit.addEventListener("click", () => startEdit(bug));
  const del = el("button", "btn small danger", "Delete");
  del.type = "button";
  del.addEventListener("click", () => removeBug(bug));

  meta.append(select, el("span", "", `Reported ${bug.created_at} UTC`), el("span", "spacer"), edit, del);
  li.append(meta);
  return li;
}

async function loadBugs() {
  const params = new URLSearchParams();
  if (els.search.value.trim()) params.set("q", els.search.value.trim());
  if (els.fSeverity.value) params.set("severity", els.fSeverity.value);
  if (els.fStatus.value) params.set("status", els.fStatus.value);
  try {
    const bugs = await api(`/api/bugs?${params}`);
    els.list.replaceChildren(...bugs.map(renderBug));
    els.empty.hidden = bugs.length > 0;
  } catch (err) {
    showError(err.message);
  }
  loadStats();
}

async function loadStats() {
  try {
    const s = await api("/api/stats");
    $("count-open").textContent = s.status["Open"];
    $("count-progress").textContent = s.status["In Progress"];
    $("count-fixed").textContent = s.status["Fixed"];
  } catch (err) {
    console.error(err);
  }
}

function resetForm() {
  els.id.value = "";
  els.title.value = "";
  els.description.value = "";
  els.severity.value = "Medium";
  els.status.value = "Open";
  els.formTitle.textContent = "Report a bug";
  els.save.textContent = "Save bug";
  els.cancel.hidden = true;
  showError("");
}

function startEdit(bug) {
  els.id.value = bug.id;
  els.title.value = bug.title;
  els.description.value = bug.description;
  els.severity.value = bug.severity;
  els.status.value = bug.status;
  els.formTitle.textContent = `Edit bug #${bug.id}`;
  els.save.textContent = "Update bug";
  els.cancel.hidden = false;
  showError("");
  els.title.focus();
}

async function saveBug() {
  const payload = {
    title: els.title.value,
    description: els.description.value,
    severity: els.severity.value,
    status: els.status.value,
  };
  try {
    if (els.id.value) {
      await api(`/api/bugs/${els.id.value}`, { method: "PUT", body: JSON.stringify(payload) });
    } else {
      await api("/api/bugs", { method: "POST", body: JSON.stringify(payload) });
    }
    resetForm();
    loadBugs();
  } catch (err) {
    showError(err.message);
  }
}

async function changeStatus(id, status) {
  try {
    await api(`/api/bugs/${id}`, { method: "PUT", body: JSON.stringify({ status }) });
    loadBugs();
  } catch (err) {
    showError(err.message);
  }
}

async function removeBug(bug) {
  if (!confirm(`Delete bug #${bug.id} "${bug.title}"? This cannot be undone.`)) return;
  try {
    await api(`/api/bugs/${bug.id}`, { method: "DELETE" });
    if (els.id.value === String(bug.id)) resetForm();
    loadBugs();
  } catch (err) {
    showError(err.message);
  }
}

let searchTimer;
els.search.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadBugs, 250);
});
els.fSeverity.addEventListener("change", loadBugs);
els.fStatus.addEventListener("change", loadBugs);
els.save.addEventListener("click", saveBug);
els.cancel.addEventListener("click", resetForm);

loadBugs();
