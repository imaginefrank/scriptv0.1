const beatsContainer = document.getElementById('beats-container');
const generateJobButton = document.getElementById('generate-job');

async function fetchState() {
  const response = await fetch('/api/state');
  return response.json();
}

async function refresh() {
  const state = await fetchState();
  renderBeats(state.beats || []);
}

function createVariantElement(beatId, variant) {
  const wrapper = document.createElement('div');
  wrapper.className = 'variant';
  wrapper.innerHTML = `
    <div><strong>${variant.type}</strong></div>
    <div class="meta">${variant.system_prompt}</div>
    <div>${variant.text}</div>
    <footer>
      <button data-beat="${beatId}" data-variant="${variant.id}">Select</button>
      <span class="badge">${variant.id}</span>
    </footer>
  `;
  const button = wrapper.querySelector('button');
  button.addEventListener('click', () => selectVariant(beatId, variant.id));
  return wrapper;
}

function renderBeats(beats) {
  beatsContainer.innerHTML = '';
  beats.forEach((beat) => {
    const beatEl = document.createElement('article');
    beatEl.className = 'beat';
    const statusBadges = [];
    if (beat.manual_override) {
      statusBadges.push('<span class="badge status-manual">Manual Override</span>');
    }
    if (beat.operator_choice) {
      statusBadges.push(`<span class="badge">Chosen via: ${beat.operator_choice}</span>`);
    }

    beatEl.innerHTML = `
      <header>
        <div>
          <h3>${beat.title}</h3>
          <div class="meta">
            Persona: <strong>${beat.persona}</strong> · Tool: <strong>${beat.tool_usage || 'n/a'}</strong> · Context: ${beat.context || 'None'}
          </div>
        </div>
        <div>${statusBadges.join(' ')}</div>
      </header>
      <div class="meta">Beat text: ${beat.text}</div>
      <div class="variants" id="variants-${beat.id}"></div>
      <div class="meta">Final text: ${beat.final_text || 'Pending'}</div>
      <button class="secondary" data-reject="${beat.id}">Reject All</button>
      <div class="manual-entry" id="manual-${beat.id}">
        <label>Operator text</label>
        <textarea></textarea>
        <div style="margin-top:6px; display:flex; gap:8px;">
          <button data-save-manual="${beat.id}">Save Manual</button>
          <button class="secondary" data-cancel-manual="${beat.id}">Cancel</button>
        </div>
      </div>
    `;

    const variantsEl = beatEl.querySelector(`#variants-${beat.id}`);
    beat.variants?.forEach((variant) => variantsEl.appendChild(createVariantElement(beat.id, variant)));

    const rejectBtn = beatEl.querySelector(`[data-reject="${beat.id}"]`);
    const manualWrapper = beatEl.querySelector(`#manual-${beat.id}`);
    rejectBtn.addEventListener('click', () => {
      manualWrapper.style.display = 'block';
    });

    const saveManual = beatEl.querySelector(`[data-save-manual="${beat.id}"]`);
    const cancelManual = beatEl.querySelector(`[data-cancel-manual="${beat.id}"]`);
    const textarea = manualWrapper.querySelector('textarea');

    saveManual.addEventListener('click', () => {
      rejectAll(beat.id, textarea.value);
      manualWrapper.style.display = 'none';
      textarea.value = '';
    });
    cancelManual.addEventListener('click', () => {
      manualWrapper.style.display = 'none';
      textarea.value = '';
    });

    beatsContainer.appendChild(beatEl);
  });
}

async function selectVariant(beatId, variantId) {
  await fetch(`/api/beats/${beatId}/select`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ variant_id: variantId }),
  });
  refresh();
}

async function rejectAll(beatId, operatorText) {
  await fetch(`/api/beats/${beatId}/reject_all`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operator_text: operatorText }),
  });
  refresh();
}

async function generateJob() {
  const beats = [
    { id: 'beat_1', title: 'Opening', text: 'Introduce the mission and protagonist', persona: 'Safe', tool: 'Search' },
    { id: 'beat_2', title: 'Conflict', text: 'Reveal antagonist plan', persona: 'Anchor', tool: 'Planner' },
    { id: 'beat_3', title: 'Resolution', text: 'Show how the day is saved', persona: 'Wildcard', tool: 'Notebook' },
  ];

  await fetch('/api/job', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ beats }),
  });
  refresh();
}

generateJobButton.addEventListener('click', generateJob);
refresh();
