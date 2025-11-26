const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json({ limit: '2mb' }));

const STATE_FILE = path.join(__dirname, 'workspace_state.json');

function readState() {
  if (!fs.existsSync(STATE_FILE)) {
    return { beats: [] };
  }
  const raw = fs.readFileSync(STATE_FILE, 'utf8');
  return JSON.parse(raw || '{"beats": []}');
}

function writeState(state) {
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

app.get('/api/state', (req, res) => {
  const state = readState();
  res.json(state);
});

app.post('/api/state', (req, res) => {
  const { beats } = req.body;
  if (!beats || !Array.isArray(beats)) {
    return res.status(400).json({ error: 'State must include beats array' });
  }
  writeState({ beats });
  res.json({ success: true });
});

app.use(express.static(path.join(__dirname, 'public')));

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Beat polish UI running on port ${port}`);
});
