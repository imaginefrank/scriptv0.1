const phases = [
  { id: 'filters', label: 'Filters', hint: 'Select at least one filter to proceed.' },
  { id: 'toolkit', label: 'Toolkit', hint: 'Pick a single toolkit before continuing.' },
  { id: 'variants', label: 'Variant approval', hint: 'Approve a variant for this execution.' },
  { id: 'rollback', label: 'Rollback', hint: 'Confirm the checkpoint before continuing.' },
];

const tokenPricing = {
  input: 0.0015 / 1000,
  output: 0.002 / 1000,
};

const state = {
  phaseIndex: 0,
  decisions: {
    filters: new Set(),
    toolkit: '',
    variant: '',
    rollback: false,
  },
  tokens: [],
  queue: [],
  conversation: [
    { speaker: 'Operator', text: 'Kick off transcript validation with safety filters.', tag: 'plan' },
    { speaker: 'Assistant', text: 'Filters ready. Awaiting toolkit selection.', tag: 'status' },
  ],
};

const elements = {};

function el(id) {
  return document.getElementById(id);
}

function renderBadges() {
  const container = el('phase-badges');
  container.innerHTML = '';
  phases.forEach((phase, index) => {
    const badge = document.createElement('div');
    badge.className = `badge ${index === state.phaseIndex ? 'active' : ''}`;
    badge.textContent = phase.label;
    container.appendChild(badge);
  });
}

function updatePhaseInfo() {
  const phase = phases[state.phaseIndex];
  el('current-phase').textContent = phase.label;
  el('phase-hint').textContent = phase.hint;
  renderBadges();
  enforceDecision();
}

function enforceDecision() {
  const nextBtn = el('next-phase');
  const { decisions, phaseIndex } = state;
  let allowed = false;

  switch (phases[phaseIndex].id) {
    case 'filters':
      allowed = decisions.filters.size > 0;
      break;
    case 'toolkit':
      allowed = Boolean(decisions.toolkit);
      break;
    case 'variants':
      allowed = Boolean(decisions.variant);
      break;
    case 'rollback':
      allowed = decisions.rollback;
      break;
    default:
      allowed = true;
  }

  nextBtn.disabled = !allowed;
}

function changePhase(delta) {
  const nextIndex = Math.min(phases.length - 1, Math.max(0, state.phaseIndex + delta));
  state.phaseIndex = nextIndex;
  updatePhaseInfo();
}

function handleFilterChange(event) {
  const { value, checked } = event.target;
  if (checked) {
    state.decisions.filters.add(value);
  } else {
    state.decisions.filters.delete(value);
  }
  enforceDecision();
}

function handleToolkitChange(event) {
  state.decisions.toolkit = event.target.value;
  enforceDecision();
}

function approveVariant() {
  const selected = el('variant-select').value;
  if (!selected) return;
  state.decisions.variant = selected;
  enforceDecision();
  alert(`Variant ${selected} approved.`);
}

function toggleRollback(event) {
  state.decisions.rollback = event.target.checked;
  enforceDecision();
}

function renderConversation() {
  const body = el('conversation-body');
  body.innerHTML = '';
  const template = document.getElementById('conversation-line');
  state.conversation.forEach((line, index) => {
    const clone = template.content.cloneNode(true);
    clone.querySelector('.speaker').textContent = line.speaker;
    clone.querySelector('.text').textContent = line.text;
    clone.querySelector('.meta').textContent = `${line.tag} · Line ${index + 1}`;
    body.appendChild(clone);
  });
}

function renderTags() {
  const tags = new Set(state.conversation.map((line) => line.tag));
  const transcriptTagContainer = el('transcript-tags');
  const sidebarTagContainer = el('sidebar-tags');
  transcriptTagContainer.innerHTML = '';
  sidebarTagContainer.innerHTML = '';

  tags.forEach((tag) => {
    const node = document.createElement('span');
    node.className = 'tag';
    node.textContent = tag;
    transcriptTagContainer.appendChild(node.cloneNode(true));
    sidebarTagContainer.appendChild(node.cloneNode(true));
  });
}

function renderSummary() {
  const summary =
    'Operator is configuring filters, selecting toolkit, and gating progression with explicit approvals.';
  el('sidebar-summary').textContent = summary;
}

function renderSentiment() {
  const sentiment = {
    label: 'Confident',
    color: 'linear-gradient(90deg, #22c55e, #a3e635)',
    description: 'Operator is decisive with checkpoints.',
  };
  const container = el('sidebar-sentiment');
  container.innerHTML = '';
  const dot = document.createElement('div');
  dot.className = 'dot';
  dot.style.background = sentiment.color;
  const label = document.createElement('div');
  label.className = 'label';
  label.textContent = `${sentiment.label} — ${sentiment.description}`;
  container.append(dot, label);
}

function addConversationLine(speaker, text, tag = 'note') {
  state.conversation.push({ speaker, text, tag });
  renderConversation();
  renderTags();
}

function calculateCost(inputTokens, outputTokens) {
  const inputCost = inputTokens * tokenPricing.input;
  const outputCost = outputTokens * tokenPricing.output;
  return {
    inputCost,
    outputCost,
    total: inputCost + outputCost,
  };
}

function renderTokens() {
  const list = el('token-list');
  const totals = el('token-totals');
  list.innerHTML = '';

  let totalInput = 0;
  let totalOutput = 0;
  let totalCost = 0;

  state.tokens.forEach((entry, index) => {
    const { inputTokens, outputTokens, cost } = entry;
    totalInput += inputTokens;
    totalOutput += outputTokens;
    totalCost += cost.total;

    const item = document.createElement('li');
    item.className = 'token-entry';
    item.textContent = `Call ${index + 1}: in ${inputTokens} • out ${outputTokens} • $${cost.total.toFixed(4)}`;
    list.appendChild(item);
  });

  totals.innerHTML = `
    <div>Total input tokens: <strong>${totalInput}</strong></div>
    <div>Total output tokens: <strong>${totalOutput}</strong></div>
    <div>Estimated cost: <strong>$${totalCost.toFixed(4)}</strong></div>
  `;
}

function simulateApiCall() {
  const prompt = el('prompt-input').value.trim();
  const inputTokens = prompt.length || Math.floor(Math.random() * 120) + 20;
  const outputTokens = Math.floor(Math.random() * 120) + 30;
  const cost = calculateCost(inputTokens, outputTokens);

  state.tokens.push({ inputTokens, outputTokens, cost });
  renderTokens();

  addConversationLine('Assistant', `Processed call with ${inputTokens} in / ${outputTokens} out tokens.`, 'metrics');
}

function updateSplitMode() {
  const clipDisplay = el('clip-display');
  clipDisplay.classList.toggle('split-mode');
}

async function togglePiP() {
  const video = el('clip-video');
  if (!document.pictureInPictureElement) {
    try {
      await video.requestPictureInPicture();
    } catch (err) {
      console.warn('PiP not available', err);
    }
  } else {
    await document.exitPictureInPicture();
  }
}

function addQueueItem(label) {
  const task = { id: crypto.randomUUID(), label, status: 'waiting' };
  state.queue.push(task);
  renderQueue();

  // Simulate non-blocking execution
  setTimeout(() => updateQueueStatus(task.id, 'running'), 300);
  setTimeout(() => updateQueueStatus(task.id, 'done'), 2600);
}

function updateQueueStatus(id, status) {
  const task = state.queue.find((item) => item.id === id);
  if (!task) return;
  task.status = status;
  renderQueue();
}

function renderQueue() {
  const list = el('queue-list');
  list.innerHTML = '';
  const loading = el('global-loading');

  const running = state.queue.some((task) => task.status === 'running' || task.status === 'waiting');
  loading.classList.toggle('active', running);

  state.queue.forEach((task) => {
    const item = document.createElement('li');
    item.className = 'queue-item';
    item.innerHTML = `
      <span>${task.label}</span>
      <span class="status-pill ${task.status}">${task.status}</span>
    `;
    list.appendChild(item);
  });
}

function bindEvents() {
  document.querySelectorAll('#filter-options input').forEach((input) => input.addEventListener('change', handleFilterChange));
  document.querySelectorAll('#toolkit-options input').forEach((input) => input.addEventListener('change', handleToolkitChange));
  el('approve-variant').addEventListener('click', approveVariant);
  el('variant-select').addEventListener('change', enforceDecision);
  el('rollback-check').addEventListener('change', toggleRollback);
  el('next-phase').addEventListener('click', () => changePhase(1));
  el('prev-phase').addEventListener('click', () => changePhase(-1));
  el('simulate-call').addEventListener('click', simulateApiCall);
  el('pip-btn').addEventListener('click', togglePiP);
  el('split-btn').addEventListener('click', updateSplitMode);
  el('start-task').addEventListener('click', () => addQueueItem('Queued run ' + (state.queue.length + 1)));
}

function init() {
  bindEvents();
  updatePhaseInfo();
  renderConversation();
  renderTags();
  renderSummary();
  renderSentiment();
  renderTokens();
  renderQueue();
}

init();
