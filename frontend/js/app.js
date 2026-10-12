const $ = (id) => document.getElementById(id);
const state = { view: "dashboard", revisionTab: "pending", currentDetail: null, mistakes: [] };
const today = () => new Date().toISOString().slice(0, 10);
const escapeHtml = (value = "") => String(value).replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
const api = async (url, options = {}) => {
  const response = await fetch(url, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.message || `Request failed (${response.status})`);
  return data;
};
function notify(message, kind = "success") {
  const n = $("notice"); n.textContent = message; n.className = `notice ${kind}`;
  window.scrollTo({ top: 0, behavior: "smooth" }); setTimeout(() => n.classList.add("hidden"), 4200);
}
function setView(view) {
  state.view = view;
  document.querySelectorAll(".view").forEach(el => el.classList.add("hidden"));
  $(`${view}View`).classList.remove("hidden");
  document.querySelectorAll(".nav-item").forEach(el => el.classList.toggle("active", el.dataset.view === view));
  $("pageTitle").textContent = ({dashboard:"Dashboard",library:"Mistake library",revisions:"Revision queue",analytics:"Learning analytics"})[view];
  if (view === "dashboard") loadDashboard();
  if (view === "library") loadLibrary();
  if (view === "revisions") loadRevisions();
  if (view === "analytics") loadAnalytics();
}
function badgeDifficulty(d) { return `<span class="badge ${String(d).toLowerCase()}">${escapeHtml(d || "Medium")}</span>`; }
function statusBadge(m) { return m.reviewed ? '<span class="badge reviewed">Reviewed</span>' : '<span class="badge pending">Pending review</span>'; }
function shortDate(d) { return d ? new Date(`${d}T00:00:00`).toLocaleDateString(undefined,{month:"short",day:"numeric",year:"numeric"}) : "Not scheduled"; }
function mistakeRow(m) {
  return `<div class="mistake-row" data-open="${m.id}"><div class="mistake-glyph">${escapeHtml((m.language||"B").slice(0,2).toUpperCase())}</div><div class="mistake-row-main"><strong>${escapeHtml(m.title)}</strong><small>${escapeHtml(m.topic)} · ${escapeHtml(m.language)} · ${shortDate(m.recorded_on)}</small></div>${statusBadge(m)}<span class="row-arrow">›</span></div>`;
}
function mistakeCard(m) {
  return `<article class="mistake-card" data-open="${m.id}"><div class="card-top"><span class="card-language">${escapeHtml(m.language)}</span>${badgeDifficulty(m.difficulty)}</div><h3 class="card-title">${escapeHtml(m.title)} ${m.is_sample ? '<span class="badge">DEMO</span>' : ''}</h3><p class="card-error">${escapeHtml(m.error_message)}</p><div class="card-bottom"><span class="card-topic">${escapeHtml(m.topic)} · ${shortDate(m.recorded_on)}</span>${statusBadge(m)}</div></article>`;
}
function renderBars(target, obj) {
  const entries = Object.entries(obj || {}).sort((a,b)=>b[1]-a[1]);
  if (!entries.length) { $(target).innerHTML = '<div class="empty-chart">No records yet. Add a mistake to see this chart.</div>'; return; }
  const max = Math.max(...entries.map(e=>e[1]),1);
  $(target).innerHTML = entries.slice(0,7).map(([label,count])=>`<div class="bar-row"><span class="bar-label" title="${escapeHtml(label)}">${escapeHtml(label)}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.max(4,count/max*100)}%"></div></div><span class="bar-value">${count}</span></div>`).join("");
}
function renderCompact(target, items, empty, mode) {
  if (!items || !items.length) { $(target).innerHTML = `<div class="empty-message">${empty}</div>`; return; }
  $(target).innerHTML = items.map(item => mode === "weak"
    ? `<div class="compact-item"><span class="compact-dot"></span><div><strong>${escapeHtml(item.topic)}</strong><small>${item.mistakes} mistake(s) · ${item.pending} pending<br>${escapeHtml(item.reason)}</small></div></div>`
    : `<div class="compact-item"><span class="compact-dot"></span><div><strong>${escapeHtml(item.message)}</strong><small>${escapeHtml(item.topic)} · repeated ${item.count} times</small></div></div>`).join("");
}
async function loadDashboard() {
  try {
    const d = await api("/api/dashboard");
    $("statTotal").textContent=d.total; $("statPending").textContent=d.pending_revisions; $("statDue").textContent=d.due_revisions; $("statReviewed").textContent=d.completed_reviews;
    $("navDue").textContent=d.due_revisions; renderBars("languageChart",d.by_language); renderCompact("weakPreview",d.weak_topics,"No focus areas yet. Repeated topics will appear here.","weak");
    $("recentList").innerHTML=d.recent.length?d.recent.map(mistakeRow).join(""):'<div class="empty-message">Your diary is empty. Add your first coding mistake to get started.</div>';
  } catch(e) { notify(e.message,"error"); }
}
async function loadOptions() {
  const options = await api("/api/options");
  [["languageFilter",options.languages,"All languages"],["topicFilter",options.topics,"All topics"]].forEach(([id,values,label])=>{
    const current=$(id).value; $(id).innerHTML=`<option value="">${label}</option>`+values.map(v=>`<option>${escapeHtml(v)}</option>`).join(""); $(id).value=current;
  });
}
function queryForLibrary() {
  const params = new URLSearchParams();
  [["search","searchInput"],["language","languageFilter"],["topic","topicFilter"],["difficulty","difficultyFilter"],["revision","revisionFilter"]].forEach(([key,id])=>{if($(id).value)params.set(key,$(id).value)});
  return params.toString();
}
async function loadLibrary() {
  try {
    await loadOptions();
    const items=await api(`/api/mistakes?${queryForLibrary()}`); state.mistakes=items;
    $("resultCount").textContent=`${items.length} mistake${items.length===1?"":"s"}`;
    $("libraryList").innerHTML=items.length?items.map(mistakeCard).join(""):'<div class="panel empty-message">No matching mistakes. Try another filter or add a new record.</div>';
  } catch(e) { notify(e.message,"error"); }
}
async function loadRevisions() {
  try {
    const items=await api(`/api/mistakes?revision=${state.revisionTab}`);
    $("revisionList").innerHTML=items.length?items.map(mistakeCard).join(""):'<div class="panel empty-message">Nothing in this revision view. Schedule a revision from a mistake detail panel.</div>';
  } catch(e) { notify(e.message,"error"); }
}
async function loadAnalytics() {
  try { const d=await api("/api/dashboard"); renderCompact("repeatedList",d.repeated_errors,"No repeated error messages found yet.","repeated"); renderCompact("weakList",d.weak_topics,"No repeated or unresolved topics detected yet.","weak"); renderBars("topicChart",d.by_topic); }
  catch(e) { notify(e.message,"error"); }
}
function openForm(item = null) {
  $("mistakeForm").reset(); $("mistakeId").value=item?.id||""; $("modalTitle").textContent=item?"Edit mistake":"Add a mistake"; $("saveButton").textContent=item?"Save changes":"Save mistake";
  $("recordedOn").value=item?.recorded_on||today();
  const fields={title:"title",language:"language",topic:"topic",difficulty:"difficulty",error_message:"errorMessage",incorrect_code:"incorrectCode",corrected_code:"correctedCode",explanation:"explanation",root_cause:"rootCause",tags:"tags",next_revision:"nextRevision"};
  Object.entries(fields).forEach(([key,id])=>$(id).value=item?.[key]??(key==="difficulty"?"Medium":""));
  $("modalBackdrop").classList.remove("hidden");
}
function closeForm() { $("modalBackdrop").classList.add("hidden"); }
async function submitForm(event) {
  event.preventDefault();
  const id=$("mistakeId").value;
  const payload={title:$("title").value.trim(),language:$("language").value.trim(),topic:$("topic").value.trim(),difficulty:$("difficulty").value,error_message:$("errorMessage").value.trim(),incorrect_code:$("incorrectCode").value,corrected_code:$("correctedCode").value,explanation:$("explanation").value,root_cause:$("rootCause").value,tags:$("tags").value,recorded_on:$("recordedOn").value||today(),next_revision:$("nextRevision").value||null};
  try { await api(id?`/api/mistakes/${id}`:"/api/mistakes",{method:id?"PUT":"POST",body:JSON.stringify(payload)}); closeForm(); notify(id?"Mistake updated.":"Mistake saved."); await refreshCurrent(); }
  catch(e) { notify(e.message,"error"); }
}
async function openDetail(id) {
  try {
    const m=await api(`/api/mistakes/${id}`); state.currentDetail=m; $("detailTitle").textContent=m.title;
    const code=(title,content)=>`<div class="detail-section"><h4>${title}</h4><pre class="code-block">${escapeHtml(content||"Not provided")}</pre></div>`;
    const text=(title,content)=>`<div class="detail-section"><h4>${title}</h4><p>${escapeHtml(content||"Not provided")}</p></div>`;
    $("detailContent").innerHTML=`<div class="detail-meta"><span class="card-language">${escapeHtml(m.language)}</span><span class="badge">${escapeHtml(m.topic)}</span>${badgeDifficulty(m.difficulty)}${statusBadge(m)}${m.is_sample?'<span class="badge">DEMO DATA</span>':''}</div>
      ${text("Error message",m.error_message)}${code("Incorrect code",m.incorrect_code)}${code("Corrected code",m.corrected_code)}${text("Solution explanation",m.explanation)}${text("Root cause",m.root_cause)}${text("Tags",m.tags)}${text("Recorded on",shortDate(m.recorded_on))}${text("Next revision",shortDate(m.next_revision))}
      <div class="detail-section"><h4>Review history</h4>${m.review_history.length?`<ul class="review-history">${m.review_history.map(r=>`<li>${shortDate(r.reviewed_on)} — ${escapeHtml(r.note||"Marked as reviewed")}</li>`).join("")}</ul>`:'<p>No reviews recorded yet.</p>'}</div>
      <div class="detail-actions"><button class="btn btn-secondary" id="editDetail">Edit</button><button class="btn btn-secondary" id="reviewDetail">${m.reviewed?"Mark pending":"Mark reviewed"}</button><button class="btn btn-secondary" id="scheduleDetail">Schedule revision</button><button class="btn btn-secondary" id="deleteDetail">Delete</button></div>
      <div id="scheduleBox" class="schedule-inline hidden"><label for="scheduleDate">Next revision</label><input type="date" id="scheduleDate" value="${m.next_revision||today()}"><button class="btn btn-primary" id="saveSchedule">Save date</button></div>`;
    $("detailBackdrop").classList.remove("hidden");
    $("editDetail").onclick=()=>{ $("detailBackdrop").classList.add("hidden");openForm(m); };
    $("reviewDetail").onclick=async()=>{try{if(m.reviewed){await api(`/api/mistakes/${m.id}/schedule?next_revision=${m.next_revision||today()}`,{method:"POST"});notify("Mistake moved back to pending review.");}else{await api(`/api/mistakes/${m.id}/review`,{method:"POST",body:JSON.stringify({note:"Reviewed from BugDiary"})});notify("Review completed.");} $("detailBackdrop").classList.add("hidden");await refreshCurrent();}catch(e){notify(e.message,"error")}};
    $("scheduleDetail").onclick=()=> $("scheduleBox").classList.toggle("hidden");
    $("saveSchedule").onclick=async()=>{try{await api(`/api/mistakes/${m.id}/schedule?next_revision=${$("scheduleDate").value}`,{method:"POST"});$("detailBackdrop").classList.add("hidden");notify("Revision date saved.");await refreshCurrent();}catch(e){notify(e.message,"error")}};
    $("deleteDetail").onclick=async()=>{if(!confirm(`Delete "${m.title}" permanently?`))return;try{await api(`/api/mistakes/${m.id}`,{method:"DELETE"});$("detailBackdrop").classList.add("hidden");notify("Mistake deleted.");await refreshCurrent();}catch(e){notify(e.message,"error")}};
  } catch(e) { notify(e.message,"error"); }
}
async function refreshCurrent() { await loadDashboard(); if(state.view==="library")await loadLibrary(); if(state.view==="revisions")await loadRevisions(); if(state.view==="analytics")await loadAnalytics(); }
async function demo(action) {
  try { const d=await api("/api/demo-data",{method:action==="load"?"POST":"DELETE"}); notify(`${d.message}${d.count!==undefined?` (${d.count})`:""}.`); await refreshCurrent(); }
  catch(e) { notify(e.message,"error"); }
}
document.querySelectorAll(".nav-item").forEach(b=>b.addEventListener("click",()=>setView(b.dataset.view)));
document.querySelectorAll("[data-goto]").forEach(b=>b.addEventListener("click",()=>setView(b.dataset.goto)));
$("addTop").onclick=$("addLibrary").onclick=()=>openForm();
$("closeModal").onclick=$("cancelModal").onclick=closeForm;
$("modalBackdrop").addEventListener("click",e=>{if(e.target===$("modalBackdrop"))closeForm()});
$("closeDetail").onclick=()=>$("detailBackdrop").classList.add("hidden");
$("detailBackdrop").addEventListener("click",e=>{if(e.target===$("detailBackdrop"))$("detailBackdrop").classList.add("hidden")});
$("mistakeForm").addEventListener("submit",submitForm);
["searchInput","languageFilter","topicFilter","difficultyFilter","revisionFilter"].forEach(id=>$(id).addEventListener(id==="searchInput"?"input":"change",()=>{if(state.view!=="library")setView("library");else loadLibrary()}));
document.querySelectorAll("[data-revision-tab]").forEach(b=>b.addEventListener("click",()=>{state.revisionTab=b.dataset.revisionTab;document.querySelectorAll("[data-revision-tab]").forEach(x=>x.classList.toggle("active",x===b));loadRevisions()}));
document.addEventListener("click",e=>{const el=e.target.closest("[data-open]");if(el)openDetail(Number(el.dataset.open))});
$("loadDemo").onclick=()=>demo("load"); $("removeDemo").onclick=()=>{if(confirm("Remove all demo records? Your own records will remain."))demo("remove")};
document.addEventListener("keydown",e=>{if(e.key==="Escape"){$("modalBackdrop").classList.add("hidden");$("detailBackdrop").classList.add("hidden")}});
loadDashboard();
