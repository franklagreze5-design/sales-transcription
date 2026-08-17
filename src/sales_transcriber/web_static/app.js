const customerInput = document.querySelector("#customerInput");
const customerSelect = document.querySelector("#customerSelect");
const sellerNameInput = document.querySelector("#sellerNameInput");
const industryInput = document.querySelector("#industryInput");
const companySizeInput = document.querySelector("#companySizeInput");
const operationsInput = document.querySelector("#operationsInput");
const meetingDateInput = document.querySelector("#meetingDateInput");
const audioSourceSelect = document.querySelector("#audioSourceSelect");
const saveProfileBtn = document.querySelector("#saveProfileBtn");
const coachFeed = document.querySelector("#coachFeed");
const startBtn = document.querySelector("#startBtn");
const stopBtn = document.querySelector("#stopBtn");
const statusBadge = document.querySelector("#statusBadge");
const transcript = document.querySelector("#transcript");
const queueMetric = document.querySelector("#queueMetric");
const latencyMetric = document.querySelector("#latencyMetric");
const rmsMetric = document.querySelector("#rmsMetric");
const bufferMetric = document.querySelector("#bufferMetric");
const modelMetric = document.querySelector("#modelMetric");
const configList = document.querySelector("#configList");
const scoreBadge = document.querySelector("#scoreBadge");
const stageValue = document.querySelector("#stageValue");
const intentValue = document.querySelector("#intentValue");
const riskValue = document.querySelector("#riskValue");
const summaryValue = document.querySelector("#summaryValue");
const liveAlert = document.querySelector("#liveAlert");
const coachList = document.querySelector("#coachList");
const painList = document.querySelector("#painList");
const goalsList = document.querySelector("#goalsList");
const nextStepValue = document.querySelector("#nextStepValue");
const budgetValue = document.querySelector("#budgetValue");
const timelineValue = document.querySelector("#timelineValue");
const customerTable = document.querySelector("#customerTable");
const meetingSummaryValue = document.querySelector("#meetingSummaryValue");
const meetingIdBadge = document.querySelector("#meetingIdBadge");
const meetingTable = document.querySelector("#meetingTable");
const historyCustomerTitle = document.querySelector("#historyCustomerTitle");
const exportTranscripts = document.querySelector("#exportTranscripts");
const exportMeetingJson = document.querySelector("#exportMeetingJson");
const syncCrmBtn = document.querySelector("#syncCrmBtn");
const toastStack = document.querySelector("#toastStack");
const buyReadinessValue = document.querySelector("#buyReadinessValue");
const buyReadinessHint = document.querySelector("#buyReadinessHint");
const riskHint = document.querySelector("#riskHint");
const starProductValue = document.querySelector("#starProductValue");
const starProductHint = document.querySelector("#starProductHint");
const contextCustomerValue = document.querySelector("#contextCustomerValue");
const contextSellerValue = document.querySelector("#contextSellerValue");
const contextIndustryValue = document.querySelector("#contextIndustryValue");
const contextSizeValue = document.querySelector("#contextSizeValue");
const contextOpsValue = document.querySelector("#contextOpsValue");
const historyCountValue = document.querySelector("#historyCountValue");
const decisionSignalValue = document.querySelector("#decisionSignalValue");
const commercialStatusValue = document.querySelector("#commercialStatusValue");
const activeObjectionsValue = document.querySelector("#activeObjectionsValue");
const aiConfidenceValue = document.querySelector("#aiConfidenceValue");
const momentumValue = document.querySelector("#momentumValue");
const coachReason = document.querySelector("#coachReason");

let partialSegment = null;
let lastSegmentElement = null;
let customerSaveTimer = null;
let contextSaveTimer = null;
let customerInputTouched = false;
let contextInputTouched = false;
let knownCustomers = [];
let lastSavedProfileKey = "";
let latestMeetingId = null;
let latestScore = 0;
let latestInsight = null;
let isRunning = false;
const displayedCoachKeys = new Set();
const displayedCoachStages = new Set();
const displayedToastKeys = new Set();
let highestCoachStageRank = 0;

function selectedCustomerName() {
  return customerInput.value.trim() || "Cliente sin nombre";
}

function hasValidCustomerName() {
  const name = customerInput.value.trim();
  return Boolean(name && name.toLowerCase() !== "cliente sin nombre");
}

function updateStartButtonState() {
  startBtn.disabled = isRunning || !hasValidCustomerName();
}

function requireCustomerBeforeStart() {
  const message = "Selecciona un cliente existente o crea un cliente nuevo antes de iniciar la reunion.";
  liveAlert.textContent = message;
  coachReason.textContent = "Esto evita guardar reuniones en clientes genericos y mantiene limpio el historial comercial.";
  appendCoachCard("Falta cliente", message, "system");
  customerInput.focus();
}

function profileKey(data = currentContext()) {
  return [
    data.name || "",
    data.seller_name || "",
    data.industry || "",
    data.company_size || "",
    data.operations_people || "",
    data.meeting_date || "",
  ].map((value) => String(value).trim()).join("|");
}

function setProfileSaved() {
  lastSavedProfileKey = profileKey();
  updateSaveButtonState();
}

function updateSaveButtonState() {
  const hasName = customerInput.value.trim().length > 0;
  const changed = profileKey() !== lastSavedProfileKey;
  saveProfileBtn.disabled = !hasName || !changed;
  saveProfileBtn.textContent = hasName && !changed ? "Guardado" : "Guardar cliente";
  updateStartButtonState();
}

function setRunning(running) {
  isRunning = running;
  statusBadge.textContent = running ? "En vivo" : "Detenido";
  statusBadge.className = `status ${running ? "live" : "idle"}`;
  updateStartButtonState();
  stopBtn.disabled = !running;
  audioSourceSelect.disabled = running;
}

async function post(path, payload = null) {
  const options = { method: "POST" };
  if (payload) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(payload);
  }
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const errorPayload = await response.json();
      message = errorPayload.error || message;
    } catch (_) {
      // Keep the HTTP status when the server returns a non-JSON error.
    }
    throw new Error(message);
  }
  return response.json();
}

function appendSegment(text, meta = {}) {
  if (!text) return;
  const row = document.createElement("p");
  row.className = "segment";
  const time = document.createElement("time");
  const latency = meta.elapsed ? ` - ${meta.elapsed}s` : "";
  time.textContent = `${new Date().toLocaleTimeString()}${latency}`;
  row.appendChild(time);
  if (meta.speaker) {
    const speaker = document.createElement("span");
    speaker.className = "speaker";
    speaker.textContent = meta.speaker;
    row.appendChild(speaker);
  }
  row.append(document.createTextNode(text));
  transcript.appendChild(row);
  lastSegmentElement = row;
  transcript.scrollTop = transcript.scrollHeight;
}

function appendCoachCard(title, body, kind = "") {
  if (!body) return;
  if (kind !== "system") {
    const key = coachCardKey(body);
    const stage = coachCardStage(key, body);
    const rank = coachStageRank(stage);
    if (isGenericCoachCard(body)) return;
    if (displayedCoachKeys.has(key)) return;
    if (stage && displayedCoachStages.has(stage)) return;
    if (rank && rank < highestCoachStageRank) return;
    displayedCoachKeys.add(key);
    if (stage) displayedCoachStages.add(stage);
    if (rank > highestCoachStageRank) highestCoachStageRank = rank;
  }
  showCoachToast(title, body, kind);
  const card = document.createElement("div");
  card.className = `coach-card ${kind}`;
  const heading = document.createElement("strong");
  heading.textContent = title;
  const detail = document.createElement("div");
  detail.textContent = body;
  const time = document.createElement("span");
  time.textContent = new Date().toLocaleTimeString();
  card.appendChild(heading);
  card.appendChild(detail);
  card.appendChild(time);
  coachFeed.prepend(card);
}

function showCoachToast(title, body, kind = "") {
  if (!toastStack || kind === "system" || !body) return;
  const key = `${coachCardKey(body)}:${normalizeText(body).slice(0, 80)}`;
  if (displayedToastKeys.has(key)) return;
  displayedToastKeys.add(key);

  const toast = document.createElement("div");
  toast.className = "coach-toast";
  const label = document.createElement("span");
  label.textContent = eventLabel(title, body);
  const headline = document.createElement("strong");
  headline.textContent = title;
  const detail = document.createElement("p");
  detail.textContent = body;
  toast.appendChild(label);
  toast.appendChild(headline);
  toast.appendChild(detail);
  toastStack.prepend(toast);
  window.setTimeout(() => toast.classList.add("leaving"), 8500);
  window.setTimeout(() => toast.remove(), 9800);
}

function eventLabel(title, body) {
  const normalized = normalizeText(`${title} ${body}`);
  if (normalized.includes("presupuesto") || normalized.includes("precio")) return "Objecion";
  if (normalized.includes("competencia") || normalized.includes("alternativas")) return "Competencia";
  if (normalized.includes("dolor") || normalized.includes("pierden") || normalized.includes("impacto")) return "Dolor";
  if (normalized.includes("demo") || normalized.includes("propuesta") || normalized.includes("senal de compra")) return "Cierre";
  return "Coach AI";
}

function coachCardKey(text) {
  const normalized = normalizeText(text);
  const topics = [
    ["current_system", ["sistema usan", "herramienta usan", "salesforce", "crm usan", "dato no queda registrado"]],
    ["operations_scope", ["cuantas personas", "cuantos vendedores", "operaciones", "participan"]],
    ["decision_process", ["quien aprueba", "criterios de decision", "decision", "aprobacion"]],
    ["proposal", ["propuesta", "alcance", "necesidades", "oferta"]],
    ["demo", ["demo", "demostracion", "participantes", "objetivo de la reunion", "piloto", "prueba"]],
    ["budget", ["presupuesto", "costos", "precio", "pricing", "plan inicial", "planes"]],
    ["roi", ["roi", "impacto economico", "valor", "beneficios", "impacto", "urgencia"]],
    ["pain", ["dolor detectado", "falta de seguimiento", "pierden", "perdida", "perdemos", "sobrepasados", "manual", "centralizada"]],
    ["buying_signal", ["senal de compra", "compromiso concreto", "me interesa", "podemos avanzar"]],
    ["timeline", ["fecha", "plazo", "trimestre", "proximos meses", "next week"]],
    ["competition", ["competencia", "competidor", "proveedores", "alternativas"]],
    ["discovery", ["descubriendo necesidades", "profundiza", "dolor", "urgencia"]],
  ];
  const match = topics.find(([, keywords]) => keywords.some((keyword) => normalized.includes(keyword)));
  return match ? match[0] : normalized;
}

function coachCardStage(key, text) {
  const normalized = normalizeText(text);
  if (["demo", "proposal", "buying_signal"].includes(key)) return "closing";
  if (["budget", "roi"].includes(key) || normalized.includes("pricing")) return "pricing";
  if (key === "pain" || normalized.includes("dolor") || normalized.includes("impacto")) return "pain";
  if (["current_system", "operations_scope", "decision_process", "timeline", "competition", "discovery"].includes(key)) {
    return "discovery";
  }
  return "";
}

function coachStageRank(stage) {
  return {
    discovery: 1,
    pain: 2,
    pricing: 3,
    closing: 4,
  }[stage] || 0;
}

function isGenericCoachCard(text) {
  const normalized = normalizeText(text);
  return [
    "continua descubriendo necesidades del cliente",
    "seguir descubriendo necesidades",
    "analizando senales comerciales",
  ].some((phrase) => normalized.includes(phrase));
}

function normalizeText(text) {
  return String(text)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function appendPartial(text) {
  if (!text) return;
  if (!partialSegment) {
    partialSegment = document.createElement("p");
    partialSegment.className = "segment partial";
    const time = document.createElement("time");
    time.textContent = new Date().toLocaleTimeString();
    partialSegment.appendChild(time);
    partialSegment.append(document.createTextNode(""));
    transcript.appendChild(partialSegment);
  }
  partialSegment.lastChild.textContent += text;
  transcript.scrollTop = transcript.scrollHeight;
}

function closePartial() {
  if (partialSegment) {
    partialSegment.remove();
    partialSegment = null;
  }
}

function renderList(element, items) {
  element.innerHTML = "";
  const safeItems = Array.isArray(items) ? items : [];
  if (safeItems.length === 0) {
    const li = document.createElement("li");
    li.textContent = "--";
    element.appendChild(li);
    return;
  }
  safeItems.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    element.appendChild(li);
  });
}

function renderConfig(config) {
  if (!config) return;
  modelMetric.textContent = config.whisper_model || "--";
  if (config.audio_source) {
    audioSourceSelect.value = config.audio_source;
  }
  configList.innerHTML = "";
  [
    ["Proveedor", config.provider],
    ["Coach IA", `${config.llm_provider || "rules"} / ${config.llm_model || "--"}`],
    ["Fuente audio", audioSourceLabel(config.audio_source)],
    ["Idioma", config.language],
    ["Sample rate", `${config.sample_rate} Hz`],
    ["Segmento max", `${config.max_segment_seconds}s`],
    ["Overlap", `${config.overlap_seconds}s`],
    ["Min RMS", config.min_rms],
    ["VAD silencio", `${config.vad_silence_frames} frames`],
  ].forEach(([label, value]) => {
    const row = document.createElement("div");
    row.textContent = `${label}: ${value ?? "--"}`;
    configList.appendChild(row);
  });
}

function audioSourceLabel(source) {
  return {
    microphone: "Microfono",
    system: "Audio sistema",
    both: "Microfono + sistema",
  }[source] || "Microfono";
}

function renderInsight(data) {
  const insight = data.insight || {};
  const score = insight.opportunity_score ?? 0;
  latestInsight = insight;
  latestScore = score;
  scoreBadge.textContent = score;
  renderBuyReadiness(score, insight);
  stageValue.textContent = insight.sales_stage || "--";
  intentValue.textContent = insight.intent || "--";
  riskValue.textContent = insight.risk_level || "--";
  riskHint.textContent = riskHintText(insight.risk_level, insight);
  summaryValue.textContent = insight.summary || "Sin analisis todavia.";
  meetingSummaryValue.textContent = insight.summary || "Analisis en progreso.";
  nextStepValue.textContent = insight.next_step || "--";
  budgetValue.textContent = insight.budget_status || "--";
  timelineValue.textContent = insight.timeline || "--";
  decisionSignalValue.textContent = insight.buying_signal ? "Senal de compra" : "Sin compromiso aun";
  commercialStatusValue.textContent = commercialStatus(score, insight);
  activeObjectionsValue.textContent = activeObjectionsText(insight);
  aiConfidenceValue.textContent = aiConfidence(score, insight);
  momentumValue.textContent = momentumText(score, insight);
  renderStarProduct(insight);

  const coachItems = [
    ...(data.recommendation ? [data.recommendation] : []),
    ...(insight.coach_advice || []),
  ];
  renderList(coachList, coachItems);
  renderList(painList, insight.pain_points || []);
  renderList(goalsList, insight.business_goals || []);

  const advice = coachItems[0];
  if (advice) {
    liveAlert.textContent = advice;
    coachReason.textContent = coachReasonText(insight);
    appendCoachCard("Siguiente mejor accion", advice);
  } else if (insight.buying_signal) {
    liveAlert.textContent = "Senal de compra detectada. Busca un compromiso concreto.";
    coachReason.textContent = "El cliente mostro disposicion a avanzar.";
    appendCoachCard("Senal de compra", liveAlert.textContent);
  } else if ((insight.pain_points || []).length > 0) {
    liveAlert.textContent = "Dolor detectado. Profundiza impacto, urgencia y costo del problema.";
    coachReason.textContent = "El cliente expreso un problema que puede convertirse en valor comercial.";
    appendCoachCard("Dolor detectado", liveAlert.textContent);
  } else {
    liveAlert.textContent = "Analizando senales comerciales en tiempo real.";
    coachReason.textContent = "La IA esta esperando una senal accionable.";
  }
}

function renderCustomers(customers) {
  customerTable.innerHTML = "";
  const rows = (Array.isArray(customers) ? customers : []).filter(
    (customer) => normalizeText(customer.customer_name || "") !== "cliente sin nombre"
  );
  knownCustomers = rows;
  renderCustomerOptions(rows);
  updateContextSummary();
  if (rows.length === 0) {
    const row = document.createElement("tr");
    row.innerHTML = '<td colspan="8">Sin clientes guardados todavia.</td>';
    customerTable.appendChild(row);
    return;
  }

  rows.forEach((customer) => {
    const row = document.createElement("tr");
    row.className = "clickable-row";
    row.dataset.customerName = customer.customer_name || "";
    const riskClass = `risk-${customer.risk_level || "low"}`;
    row.innerHTML = `
      <td><strong>${escapeHtml(customer.customer_name)}</strong></td>
      <td>${customer.meeting_count ?? 0}</td>
      <td>${escapeHtml(customer.industry || "--")}</td>
      <td><span class="pill">${customer.opportunity_score ?? 0}</span></td>
      <td>${escapeHtml(customer.sales_stage || "--")}</td>
      <td><span class="pill ${riskClass}">${escapeHtml(customer.risk_level || "--")}</span></td>
      <td>${escapeHtml(customer.next_step || "--")}</td>
      <td>${escapeHtml(shorten(customer.summary || "--", 150))}</td>
    `;
    row.addEventListener("click", () => {
      selectExistingCustomer(customer.customer_name || "");
    });
    customerTable.appendChild(row);
  });
}

function renderCustomerOptions(customers) {
  const current = customerSelect.value;
  customerSelect.innerHTML = '<option value="">Nuevo cliente</option>';
  customers.forEach((customer) => {
    const option = document.createElement("option");
    option.value = customer.customer_name || "";
    const meetings = customer.meeting_count ?? 0;
    const suffix = meetings === 1 ? "1 reunion" : `${meetings} reuniones`;
    option.textContent = `${customer.customer_name || "Cliente"} - ${suffix}`;
    customerSelect.appendChild(option);
  });
  if ([...customerSelect.options].some((option) => option.value === current)) {
    customerSelect.value = current;
  }
}

function applyCustomerProfile(customer) {
  if (!customer) return;
  customerInputTouched = true;
  contextInputTouched = false;
  customerInput.value = customer.customer_name || "";
  sellerNameInput.value = customer.seller_name || "";
  industryInput.value = customer.industry || "";
  companySizeInput.value = customer.company_size || "";
  operationsInput.value = customer.operations_people || "";
  meetingDateInput.value = customer.meeting_date || "";
  customerSelect.value = customer.customer_name || "";
  setProfileSaved();
  updateContextSummary(customer);
}

async function selectExistingCustomer(customerName) {
  if (!customerName) return;
  const localCustomer = knownCustomers.find((customer) => customer.customer_name === customerName);
  if (localCustomer) {
    applyCustomerProfile(localCustomer);
  }
  const data = await post("/api/customer", { name: customerName });
  renderCustomers(data.customers || knownCustomers);
  if (data.context) {
    renderContext(data.context, true);
  }
  renderMeetings(data.meetings || [], data.name || customerName);
  customerSelect.value = data.name || customerName;
  exportTranscripts.href = `/api/export-transcripts?customer=${encodeURIComponent(data.name || customerName)}`;
  setProfileSaved();
}

function renderMeetings(meetings, customerName) {
  meetingTable.innerHTML = "";
  historyCustomerTitle.textContent = customerName || selectedCustomerName();
  const rows = Array.isArray(meetings) ? meetings : [];
  const suffix = rows.length === 1 ? "1 reunion" : `${rows.length} reuniones`;
  historyCountValue.textContent = suffix;
  if (rows.length === 0) {
    const row = document.createElement("tr");
    row.innerHTML = '<td colspan="6">Sin reuniones guardadas para este cliente.</td>';
    meetingTable.appendChild(row);
    return;
  }

  rows.forEach((meeting) => {
    const riskClass = `risk-${meeting.risk_level || "low"}`;
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(meeting.started_at || meeting.meeting_date || "--")}</td>
      <td><span class="pill">${meeting.opportunity_score ?? 0}</span></td>
      <td>${escapeHtml(meeting.sales_stage || "--")}</td>
      <td><span class="pill ${riskClass}">${escapeHtml(meeting.risk_level || "--")}</span></td>
      <td>${escapeHtml(meeting.next_step || "--")}</td>
      <td>${escapeHtml(shorten(meeting.summary || "--", 180))}</td>
    `;
    meetingTable.appendChild(row);
  });
  if (rows[0]?.id) {
    latestMeetingId = rows[0].id;
    updateMeetingJsonLink();
  }
}

async function loadCustomerHistory(customerName = selectedCustomerName()) {
  const url = `/api/customer-history?customer=${encodeURIComponent(customerName)}`;
  const data = await fetch(url).then((response) => response.json());
  renderMeetings(data.meetings, data.customer_name);
  exportTranscripts.href = `/api/export-transcripts?customer=${encodeURIComponent(customerName)}`;
  updateMeetingJsonLink();
}

function updateMeetingJsonLink() {
  if (!exportMeetingJson) return;
  const customer = encodeURIComponent(selectedCustomerName());
  const meetingParam = latestMeetingId ? `meeting_id=${encodeURIComponent(latestMeetingId)}` : `customer=${customer}`;
  exportMeetingJson.href = `/api/export-meeting-json?${meetingParam}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function shorten(value, limit) {
  if (value.length <= limit) return value;
  return `${value.slice(0, limit - 1)}...`;
}

function markLastSpeaker(speaker) {
  if (!lastSegmentElement || !speaker) return;
  const existing = lastSegmentElement.querySelector(".speaker");
  if (existing) return;
  const badge = document.createElement("span");
  badge.className = "speaker";
  badge.textContent = speaker;
  const time = lastSegmentElement.querySelector("time");
  if (time) {
    time.insertAdjacentElement("afterend", badge);
  }
}

function markProfileDirty() {
  customerInputTouched = true;
  updateSaveButtonState();
  updateContextSummary();
}

function currentContext() {
  return {
    name: customerInput.value,
    seller_name: sellerNameInput.value,
    industry: industryInput.value,
    company_size: companySizeInput.value,
    operations_people: operationsInput.value,
    meeting_date: meetingDateInput.value,
  };
}

function saveContextSoon() {
  contextInputTouched = true;
  updateSaveButtonState();
  updateContextSummary();
}

function renderContext(context, force = false) {
  if (!context || (contextInputTouched && !force)) return;
  sellerNameInput.value = context.seller_name || "";
  industryInput.value = context.industry || "";
  companySizeInput.value = context.company_size || "";
  operationsInput.value = context.operations_people || "";
  meetingDateInput.value = context.meeting_date || "";
  updateSaveButtonState();
  updateContextSummary();
}

function updateContextSummary(customer = null) {
  const selected = customer || knownCustomers.find((item) => item.customer_name === selectedCustomerName());
  const context = currentContext();
  contextCustomerValue.textContent = context.name || selected?.customer_name || "Nuevo cliente";
  contextSellerValue.textContent = context.seller_name || selected?.seller_name || "--";
  contextIndustryValue.textContent = context.industry || selected?.industry || "--";
  contextSizeValue.textContent = context.company_size || selected?.company_size || "--";
  contextOpsValue.textContent = context.operations_people || selected?.operations_people || "--";
  if (selected) {
    const meetings = selected.meeting_count ?? 0;
    historyCountValue.textContent = meetings === 1 ? "1 reunion" : `${meetings} reuniones`;
  }
}

function renderBuyReadiness(score, insight) {
  if (score >= 85 || insight.next_step === "proposal") {
    buyReadinessValue.textContent = "Muy cerca";
    buyReadinessHint.textContent = "Busca compromiso concreto: demo, propuesta o fecha de decision.";
    return;
  }
  if (score >= 70 || insight.next_step === "demo") {
    buyReadinessValue.textContent = "Alta";
    buyReadinessHint.textContent = "Valida criterios de exito y agenda el siguiente paso.";
    return;
  }
  if (score >= 45) {
    buyReadinessValue.textContent = "En evaluacion";
    buyReadinessHint.textContent = "Conecta dolor con impacto economico antes de hablar de precio.";
    return;
  }
  if (score > 0) {
    buyReadinessValue.textContent = "Temprana";
    buyReadinessHint.textContent = "Falta descubrir problema, urgencia y decisor.";
    return;
  }
  buyReadinessValue.textContent = "Sin lectura";
  buyReadinessHint.textContent = "Inicia la reunion para calcular intencion comercial.";
}

function activeObjectionsText(insight) {
  const objections = Array.isArray(insight.objections) ? insight.objections : [];
  if (objections.length > 0) {
    return objections.slice(0, 2).join(", ");
  }
  if (insight.budget_status === "limited") return "Presupuesto";
  if (insight.risk_level === "high") return "Riesgo alto";
  return "--";
}

function aiConfidence(score, insight) {
  const signals = [
    score > 0,
    Boolean(insight.summary),
    (insight.pain_points || []).length > 0,
    (insight.business_goals || []).length > 0,
    Boolean(insight.next_step && insight.next_step !== "--"),
    Boolean(insight.buying_signal),
  ].filter(Boolean).length;
  if (signals >= 5) return "Alta";
  if (signals >= 3) return "Media";
  if (signals >= 1) return "Inicial";
  return "--";
}

function momentumText(score, insight) {
  if (insight.buying_signal || insight.next_step === "proposal" || insight.next_step === "demo") {
    return "Va mejorando";
  }
  if (insight.risk_level === "high" || (insight.objections || []).length >= 2) {
    return "Perdiendo fuerza";
  }
  if (score >= 45) return "En evaluacion";
  if (score > 0) return "Estancado";
  return "Esperando";
}

function coachReasonText(insight) {
  if (insight.buying_signal) return "Hay senal de avance: busca compromiso concreto.";
  if ((insight.objections || []).includes("budget")) return "Aparecio presupuesto: protege valor antes de negociar.";
  if ((insight.objections || []).includes("competitor")) return "Aparecio competencia: diferencia criterios y valor.";
  if ((insight.pain_points || []).length > 0) return "Hay dolor explicito: cuantifica impacto y urgencia.";
  return "Recomendacion generada por etapa comercial y contexto del cliente.";
}

function riskHintText(risk, insight) {
  if (risk === "high") return "Hay objeciones fuertes. Protege valor antes de negociar.";
  if (risk === "medium") return "Requiere validar presupuesto, urgencia o decision.";
  if (risk === "low") return "Sin riesgo critico detectado por ahora.";
  if (insight.buying_signal) return "Cliente muestra senales positivas.";
  return "Sin historial activo";
}

function commercialStatus(score, insight) {
  if (insight.buying_signal) return "Compra plausible";
  if (score >= 70) return "Oportunidad caliente";
  if (score >= 45) return "Necesita madurar";
  if (score > 0) return "Discovery activo";
  return "Esperando";
}

function renderStarProduct(insight) {
  const text = normalizeText([
    ...(insight.pain_points || []),
    ...(insight.business_goals || []),
    insight.summary || "",
  ].join(" "));
  if (text.includes("seguimiento") || text.includes("pipeline") || text.includes("crm")) {
    starProductValue.textContent = "CRM + seguimiento";
    starProductHint.textContent = "Enfocar en visibilidad, trazabilidad y menos oportunidades perdidas.";
    return;
  }
  if (text.includes("vendedor") || text.includes("operaciones") || text.includes("sobrepasado")) {
    starProductValue.textContent = "Coach de productividad";
    starProductHint.textContent = "Enfocar en eficiencia del equipo y priorizacion comercial.";
    return;
  }
  if (text.includes("retencion") || text.includes("clientes")) {
    starProductValue.textContent = "Retencion comercial";
    starProductHint.textContent = "Enfocar en seguimiento, alertas y continuidad con clientes.";
    return;
  }
  starProductValue.textContent = "Sales Coach AI";
  starProductHint.textContent = "Recomendado segun dolores y contexto.";
}

customerSelect.addEventListener("change", () => {
  if (customerSelect.value) {
    selectExistingCustomer(customerSelect.value).catch((error) => {
      appendCoachCard("No se pudo cargar cliente", error.message, "system");
    });
    return;
  }
  customerInput.value = "";
  sellerNameInput.value = "";
  industryInput.value = "";
  companySizeInput.value = "";
  operationsInput.value = "";
  meetingDateInput.value = "";
  customerInputTouched = true;
  contextInputTouched = true;
  lastSavedProfileKey = "";
  updateSaveButtonState();
  updateContextSummary();
});
customerInput.addEventListener("input", () => {
  customerSelect.value = "";
  markProfileDirty();
});
sellerNameInput.addEventListener("input", saveContextSoon);
industryInput.addEventListener("input", saveContextSoon);
companySizeInput.addEventListener("input", saveContextSoon);
operationsInput.addEventListener("input", saveContextSoon);
meetingDateInput.addEventListener("input", saveContextSoon);
audioSourceSelect.addEventListener("change", async () => {
  try {
    await post("/api/audio-source", { source: audioSourceSelect.value });
    appendCoachCard("Fuente de audio", `Modo seleccionado: ${audioSourceLabel(audioSourceSelect.value)}.`, "system");
  } catch (error) {
    appendCoachCard("No se pudo cambiar audio", error.message, "system");
  }
});
saveProfileBtn.addEventListener("click", async () => {
  try {
    if (!hasValidCustomerName()) {
      requireCustomerBeforeStart();
      return;
    }
    saveProfileBtn.disabled = true;
    const data = await post("/api/save-profile", currentContext());
    renderCustomers(data.customers);
    customerSelect.value = selectedCustomerName();
    await loadCustomerHistory(selectedCustomerName());
    setProfileSaved();
    appendCoachCard("Cliente guardado", "La ficha del cliente quedo lista para esta reunion.", "system");
  } catch (error) {
    appendCoachCard("No se pudo guardar", error.message, "system");
  } finally {
    updateSaveButtonState();
  }
});
customerInput.addEventListener("focus", () => {
  if (customerInput.value === "Cliente sin nombre") {
    customerInput.value = "";
  }
});

startBtn.addEventListener("click", async () => {
  try {
    if (!hasValidCustomerName()) {
      requireCustomerBeforeStart();
      return;
    }
    statusBadge.textContent = "Iniciando";
    startBtn.disabled = true;
    transcript.innerHTML = "";
    coachFeed.innerHTML = "";
    if (toastStack) toastStack.innerHTML = "";
    displayedCoachKeys.clear();
    displayedCoachStages.clear();
    displayedToastKeys.clear();
    highestCoachStageRank = 0;
    latestMeetingId = null;
    meetingSummaryValue.textContent = "Reunion en curso. El resumen se actualizara con las senales detectadas.";
    await post("/api/audio-source", { source: audioSourceSelect.value });
    const data = await post("/api/save-profile", currentContext());
    renderCustomers(data.customers);
    customerSelect.value = selectedCustomerName();
    setProfileSaved();
    await post("/api/start");
  } catch (error) {
    appendSegment(`[Error] No se pudo iniciar: ${error.message}`);
    setRunning(false);
  }
});

stopBtn.addEventListener("click", async () => {
  try {
    stopBtn.disabled = true;
    await post("/api/stop");
  } catch (error) {
    appendSegment(`[Error] No se pudo detener: ${error.message}`);
  }
});

fetch("/api/status")
  .then((response) => response.json())
  .then((snapshot) => {
    setRunning(snapshot.running);
    renderConfig(snapshot.config);
    renderCustomers(snapshot.customers);
    renderMeetings(snapshot.meetings, snapshot.customer_name);
    renderContext(snapshot.customer_context);
    meetingIdBadge.textContent = snapshot.current_meeting_id
      ? `#${snapshot.current_meeting_id}`
      : "Nueva";
    if (snapshot.audio_source) {
      audioSourceSelect.value = snapshot.audio_source;
    }
    if (!customerInputTouched && document.activeElement !== customerInput) {
      customerInput.value = snapshot.customer_name === "Cliente sin nombre"
        ? ""
        : snapshot.customer_name || "";
    }
    customerSelect.value = customerInput.value;
    if (!customerInputTouched && !contextInputTouched) {
      setProfileSaved();
    } else {
      updateSaveButtonState();
    }
    exportTranscripts.href = `/api/export-transcripts?customer=${encodeURIComponent(selectedCustomerName())}`;
    updateMeetingJsonLink();
    queueMetric.textContent = `Cola ${snapshot.queue_size}`;
  });

const events = new EventSource("/events");
events.onmessage = (message) => {
  const event = JSON.parse(message.data);
  const payload = event.payload || {};

  if (event.type === "snapshot") {
    setRunning(payload.running);
    renderConfig(payload.config);
    renderCustomers(payload.customers);
    renderMeetings(payload.meetings, payload.customer_name);
    renderContext(payload.customer_context);
    meetingIdBadge.textContent = payload.current_meeting_id
      ? `#${payload.current_meeting_id}`
      : "Nueva";
    if (payload.audio_source) {
      audioSourceSelect.value = payload.audio_source;
    }
    if (!customerInputTouched && document.activeElement !== customerInput) {
      customerInput.value = payload.customer_name === "Cliente sin nombre"
        ? ""
        : payload.customer_name || "";
    }
    customerSelect.value = customerInput.value;
    if (!customerInputTouched && !contextInputTouched) {
      setProfileSaved();
    } else {
      updateSaveButtonState();
    }
    updateMeetingJsonLink();
    queueMetric.textContent = `Cola ${payload.queue_size}`;
  }

  if (event.type === "customer") {
    if (document.activeElement !== customerInput) {
      customerInput.value = payload.name === "Cliente sin nombre"
        ? ""
        : payload.name || "";
    }
  }

  if (event.type === "customer_context") {
    renderContext(payload);
  }

  if (event.type === "audio_source") {
    audioSourceSelect.value = payload.source || "microphone";
  }

  if (event.type === "status") {
    setRunning(payload.running);
    if (payload.meeting_id) {
      latestMeetingId = payload.meeting_id;
      meetingIdBadge.textContent = `#${payload.meeting_id}`;
      updateMeetingJsonLink();
    }
    if (payload.message) {
      appendSegment(`[Sistema] ${payload.message}`);
      appendCoachCard("Sistema", payload.message, "system");
    }
  }

  if (event.type === "queue") {
    queueMetric.textContent = `Cola ${payload.size}`;
    rmsMetric.textContent = payload.rms ?? "--";
  }

  if (event.type === "buffer") {
    bufferMetric.textContent = payload.size ?? 0;
  }

  if (event.type === "speaker_segment") {
    markLastSpeaker(payload.speaker);
  }

  if (event.type === "analysis_status") {
    liveAlert.textContent = payload.message || "Analizando conversacion";
  }

  if (event.type === "transcript_delta") {
    appendPartial(payload.text);
  }

  if (event.type === "transcript_segment") {
    closePartial();
    appendSegment(payload.text, payload);
    latencyMetric.textContent = payload.elapsed ? `${payload.elapsed}s` : "--";
    rmsMetric.textContent = payload.rms ?? "--";
    queueMetric.textContent = `Cola ${payload.queue_size ?? 0}`;
    if (payload.meeting_id) {
      latestMeetingId = payload.meeting_id;
      meetingIdBadge.textContent = `#${payload.meeting_id}`;
      updateMeetingJsonLink();
    }
  }

  if (event.type === "analysis") {
    renderInsight(payload);
    renderCustomers(payload.customers);
    renderMeetings(payload.meetings, selectedCustomerName());
    updateMeetingJsonLink();
  }

  if (event.type === "error") {
    appendSegment(`[Error] ${payload.message}`);
    appendCoachCard("Revisar configuracion", payload.message, "system");
    if (payload.message && payload.message.includes("Error opening InputStream")) {
      appendSegment(
        "[Sistema] No se pudo abrir la fuente de audio seleccionada. Prueba Microfono o revisa que exista un dispositivo de salida activo para Sistema."
      );
    }
    setRunning(false);
  }
};

if (syncCrmBtn) {
  syncCrmBtn.addEventListener("click", async () => {
    try {
      syncCrmBtn.disabled = true;
      const payload = {
        customer: selectedCustomerName(),
        meeting_id: latestMeetingId,
      };
      const data = await post("/api/sync-crm", payload);
      appendCoachCard(
        "CRM actualizado",
        data.message || "Insight agregado al conector CRM en modo append-only.",
        "system"
      );
    } catch (error) {
      appendCoachCard("CRM no actualizado", error.message, "system");
    } finally {
      syncCrmBtn.disabled = false;
    }
  });
}

