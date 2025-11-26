const beatListEl = document.getElementById('beat-list');
const beatDetailEl = document.getElementById('beat-detail');
const beatTemplate = document.getElementById('beat-template');

let workspaceState = { beats: [] };
let activeBeatId = null;

async function loadState() {
  const res = await fetch('/api/state');
  workspaceState = await res.json();
  if (workspaceState.beats.length > 0) {
    activeBeatId = workspaceState.beats[0].id;
  }
  renderBeatList();
  renderActiveBeat();
}

async function saveState() {
  await fetch('/api/state', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ beats: workspaceState.beats })
  });
}

function renderBeatList() {
  beatListEl.innerHTML = '<h3>Beats</h3>';
  workspaceState.beats.forEach((beat) => {
    const link = document.createElement('a');
    link.textContent = beat.title;
    link.href = '#';
    link.className = `beat-nav-item ${beat.id === activeBeatId ? 'active' : ''}`;
    link.addEventListener('click', (e) => {
      e.preventDefault();
      activeBeatId = beat.id;
      renderBeatList();
      renderActiveBeat();
    });
    beatListEl.appendChild(link);
  });
}

function buildPrompt(beat, donorOption, instruction) {
  const donorText = donorOption ? `${donorOption.name}: ${donorOption.text}` : 'Use baseline tone only.';
  const selectedVersion = beat.versions.find((v) => v.id === beat.selectedVersionId);
  return [
    'You are polishing a beat while preserving meaning and structure.',
    `Current selected draft: ${selectedVersion ? selectedVersion.text : beat.baseline}`,
    `Baseline reference: ${beat.baseline}`,
    `Style donor: ${donorText}`,
    `Operator instruction: ${instruction || 'None provided'}`,
    'Return a polished draft that keeps the narrative order but adapts tone/style from the donor and instruction.'
  ].join('\n');
}

function createPolishedDraft(beat, donorOption, instruction) {
  const prompt = buildPrompt(beat, donorOption, instruction);
  const donorLabel = donorOption ? donorOption.name : 'baseline';
  const timestamp = new Date().toISOString();
  const text = `Polished draft using ${donorLabel} with instruction "${instruction || 'None'}".\n\n${beat.baseline}\n\nStyle cues: ${donorOption ? donorOption.text : 'Baseline tone'}\nInstruction applied: ${instruction || 'None provided'}`;
  return {
    id: crypto.randomUUID(),
    text,
    sourceOption: donorLabel,
    instruction: instruction || 'None provided',
    timestamp,
    prompt
  };
}

function renderVersionList(beat, container) {
  container.innerHTML = '';
  beat.versions
    .slice()
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .forEach((version) => {
      const card = document.createElement('div');
      card.className = 'version-card';

      const meta = document.createElement('div');
      meta.className = 'version-meta';
      meta.innerHTML = `
        <span class="badge">${version.sourceOption}</span>
        <span>${new Date(version.timestamp).toLocaleString()}</span>
        <span>Instruction: ${version.instruction}</span>
      `;
      card.appendChild(meta);

      const text = document.createElement('div');
      text.className = 'version-text';
      text.textContent = version.text;
      card.appendChild(text);

      const prompt = document.createElement('details');
      const summary = document.createElement('summary');
      summary.textContent = 'View prompt';
      prompt.appendChild(summary);
      const promptBody = document.createElement('pre');
      promptBody.className = 'prompt-text';
      promptBody.textContent = version.prompt;
      prompt.appendChild(promptBody);
      card.appendChild(prompt);

      const actions = document.createElement('div');
      actions.className = 'version-actions';

      if (beat.selectedVersionId === version.id) {
        const selected = document.createElement('span');
        selected.className = 'badge';
        selected.textContent = 'Selected';
        actions.appendChild(selected);
      } else {
        const selectBtn = document.createElement('button');
        selectBtn.className = 'secondary-btn';
        selectBtn.textContent = 'Select';
        selectBtn.addEventListener('click', async () => {
          beat.selectedVersionId = version.id;
          await saveState();
          renderActiveBeat();
        });
        actions.appendChild(selectBtn);
      }

      const rollbackBtn = document.createElement('button');
      rollbackBtn.className = 'secondary-btn';
      rollbackBtn.textContent = 'Rollback here';
      rollbackBtn.addEventListener('click', async () => {
        beat.selectedVersionId = version.id;
        await saveState();
        renderActiveBeat();
      });
      actions.appendChild(rollbackBtn);

      card.appendChild(actions);
      container.appendChild(card);
    });
}

function renderActiveBeat() {
  const beat = workspaceState.beats.find((b) => b.id === activeBeatId);
  if (!beat) {
    beatDetailEl.innerHTML = '<p>No beat selected.</p>';
    return;
  }

  const node = beatTemplate.content.cloneNode(true);
  node.querySelector('.beat-title').textContent = beat.title;
  node.querySelector('.beat-baseline').textContent = `Baseline: ${beat.baseline}`;

  const optionsContainer = node.querySelector('.rejected-options');

  const baselineOption = document.createElement('label');
  baselineOption.className = 'option-card';
  baselineOption.innerHTML = `
    <input type="radio" name="style-donor" value="baseline" checked> Use baseline tone only
  `;
  optionsContainer.appendChild(baselineOption);

  beat.rejectedOptions.forEach((opt) => {
    const label = document.createElement('label');
    label.className = 'option-card';
    label.innerHTML = `
      <input type="radio" name="style-donor" value="${opt.id}"> <strong>${opt.name}</strong><br>${opt.text}
    `;
    optionsContainer.appendChild(label);
  });

  const instructionInput = node.querySelector('.instruction-input');
  const promptText = node.querySelector('.prompt-text');
  const polishBtn = node.querySelector('.polish-btn');
  const versionContainer = node.querySelector('.version-list');

  const getSelectedDonor = () => {
    const checked = optionsContainer.querySelector('input[name="style-donor"]:checked');
    if (!checked || checked.value === 'baseline') return null;
    return beat.rejectedOptions.find((opt) => opt.id === checked.value) || null;
  };

  const updatePromptPreview = () => {
    promptText.textContent = buildPrompt(beat, getSelectedDonor(), instructionInput.value.trim());
  };

  optionsContainer.addEventListener('change', updatePromptPreview);
  instructionInput.addEventListener('input', updatePromptPreview);

  polishBtn.addEventListener('click', async () => {
    const donorOption = getSelectedDonor();
    const instruction = instructionInput.value.trim();
    const version = createPolishedDraft(beat, donorOption, instruction);
    beat.versions.push(version);
    beat.selectedVersionId = version.id;
    await saveState();
    renderActiveBeat();
  });

  updatePromptPreview();
  renderVersionList(beat, versionContainer);

  beatDetailEl.innerHTML = '';
  beatDetailEl.appendChild(node);
}

loadState();
