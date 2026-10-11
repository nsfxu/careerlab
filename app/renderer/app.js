// CareerLab renderer. No save-format knowledge here: everything comes from the engine.
const $ = (s) => document.querySelector(s);
const call = (m, p) => window.cl.call(m, p);

// Game-style Portuguese position labels and colours.
const POS_PT = { GK: "GO", CB: "ZC", LB: "LE", RB: "LD", DMF: "VOL", CMF: "MLG", LMF: "MLE",
  RMF: "MLD", AMF: "MAT", LWF: "PTE", RWF: "PTD", SS: "SA", CF: "CA" };
const POS_GROUP = { GK: "gk", CB: "def", LB: "def", RB: "def", DMF: "mid", CMF: "mid", LMF: "mid",
  RMF: "mid", AMF: "mid", LWF: "att", RWF: "att", SS: "att", CF: "att" };
const ABIL_PT = {
  offensive_awareness: "Talento ofensivo", ball_control: "Controle de bola", dribbling: "Drible",
  tight_possession: "Condução firme", low_pass: "Passe rasteiro", lofted_pass: "Passe alto",
  finishing: "Finalização", heading: "Cabeceio", place_kicking: "Chute colocado", curl: "Curva",
  speed: "Velocidade", acceleration: "Aceleração", kicking_power: "Força do chute", jump: "Impulsão",
  physical_contact: "Contato físico", balance: "Equilíbrio", stamina: "Resistência",
  defensive_awareness: "Talento defensivo", ball_winning: "Desarme", aggression: "Agressividade",
  gk_awareness: "Talento de GO", gk_catching: "Firmeza do GO", gk_clearing: "Afast. de bola do GO",
  gk_reflexes: "Reflexos do GO", gk_reach: "Alcance do GO",
};
const ABIL_ORDER = Object.keys(ABIL_PT);
const SKILL_NAMES = {
  scissors_feint: "Pedalada simples", flip_flap: "Elástico", marseille_turn: "Giro de Marselha",
  sombrero: "Chapéu", cut_behind_turn: "Corte por trás e giro", scotch_move: "Toque de letra",
  heading_skill: "Cabeçada", long_range_drive: "Chute de longe", knuckle_shot: "Folha seca",
  acrobatic_finishing: "Finalização acrobática", heel_trick: "Toque de calcanhar",
  first_time_shot: "Chute de primeira", one_touch_pass: "Passe de primeira", weighted_pass: "Passe na medida",
  pinpoint_crossing: "Cruzamento preciso", outside_curler: "Curva para fora", rabona: "De letra",
  low_lofted_pass: "Passe alto rasteiro", gk_low_punt: "Reposição baixa (GO)", long_throw: "Lateral longo",
  gk_long_throw: "Arremesso longo (GO)", gamesmanship: "Malícia", man_marking: "Marcação individual",
  track_back: "Volta para marcar", acrobatic_clear: "Afastamento acrobático", captaincy: "Liderança",
  super_sub: "Super substituto", fighting_spirit: "Espírito guerreiro", no_look_pass: "Passe sem olhar",
  penalty_specialist: "Especialista em pênaltis", gk_penalty_saver: "Pegador de pênaltis",
  chip_shot_control: "Cavadinha", step_on_skill_control: "Pisada na bola", dipping_shots: "Chute descendente",
  rising_shots: "Chute ascendente", gk_high_punt: "Reposição alta (GO)", interception: "Interceptação",
  double_touch: "Toque duplo", cross_over_turn: "Giro cruzado", long_range_shooting: "Precisão à distância",
  through_passing: "Passe em profundidade",
};

const state = { save: null, summary: null, clubs: [], block: null, squad: null, player: null, staged: [] };

function toast(msg, error = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast" + (error ? " error" : "");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.add("hidden"), error ? 7000 : 3500);
}
async function guarded(fn) {
  try { return await fn(); } catch (e) { toast(e.message || String(e), true); }
}
function badge(pos) {
  const b = document.createElement("span");
  b.className = "badge " + (POS_GROUP[pos] || "");
  b.textContent = POS_PT[pos] || pos || "?";
  return b;
}
function valClass(v) { return v >= 90 ? "v-hi" : v >= 80 ? "v-mid" : v >= 70 ? "v-lo" : "v-bad"; }
function el(tag, props = {}, ...kids) {
  const e = document.createElement(tag);
  Object.assign(e, props);
  for (const k of kids) e.append(k);
  return e;
}

// ------------------------------------------------------------------ saves

async function loadSaves() {
  const r = await call("list_saves");
  const sel = $("#save-picker");
  sel.innerHTML = "";
  for (const s of r.saves) {
    const d = new Date(s.modified * 1000).toLocaleString();
    sel.append(el("option", { value: s.path, textContent: `${s.slot}  ·  ${d}` }));
  }
  if (!r.saves.length) sel.append(el("option", { textContent: "No Become a Legend saves found" }));
  else await openSave(r.saves[0].path);
}

async function openSave(path) {
  await guarded(async () => {
    $("#squad-name").textContent = "Loading…";
    state.summary = await call("open_save", { path });
    state.save = path;
    state.staged = [];
    const me = state.summary.me;
    $("#career-info").textContent = me ? `${me.name}, ${me.age} · ${me.club || ""}` : "";
    state.clubs = await call("clubs");
    renderClubs();
    updateStaged();
    if (me && me.block != null) await openClub(me.block);
  });
}

// ------------------------------------------------------------------ clubs

function renderClubs() {
  const q = $("#club-filter").value.trim().toLowerCase();
  const ul = $("#club-list");
  ul.innerHTML = "";
  const myBlock = state.summary?.me?.block;
  for (const c of state.clubs) {
    if (q && !c.name.toLowerCase().includes(q) && !(c.manager || "").toLowerCase().includes(q)) continue;
    const li = el("li", { className: c.block === state.block ? "active" : "" },
      el("span", { textContent: c.name, className: c.block === myBlock ? "me" : "" }),
      el("span", { className: "size", textContent: c.size }));
    li.title = c.manager ? `Manager: ${c.manager}` : "";
    li.onclick = () => openClub(c.block);
    ul.append(li);
  }
}

async function openClub(block) {
  await guarded(async () => {
    state.block = block;
    state.squad = await call("squad", { block });
    renderClubs();
    renderSquad();
    $("#btn-manager").disabled = false;
    $("#btn-sync").disabled = !state.squad.teamId;
  });
}

function renderSquad() {
  const s = state.squad;
  $("#squad-name").textContent = s.name;
  $("#squad-manager").textContent = s.manager?.name ? `Manager: ${s.manager.name} · ${s.players.length} players` : `${s.players.length} players`;
  const body = $("#squad-body");
  body.innerHTML = "";
  for (const p of s.players) {
    const tr = el("tr", { className: (p.created ? "created " : "") + (state.player?.pid === p.pid ? "active" : "") });
    tr.append(el("td", { textContent: p.shirt ?? "" }), el("td", {}, badge(p.position)),
      el("td", { textContent: p.name }), el("td", { textContent: p.age ?? "" }),
      el("td", { textContent: p.speed ?? "" }));
    tr.onclick = () => openPlayer(p.pid);
    body.append(tr);
  }
}

// ------------------------------------------------------------------ player

async function openPlayer(pid) {
  await guarded(async () => {
    state.player = await call("player", { pid });
    renderSquad();
    renderPlayer();
  });
}

function skillOp(p, k, value, label) {
  return p.kind === "created"
    ? { op: "created", pid: p.pid, field: p.skillFields[k], value, label }
    : { op: "attr", pid: p.pid, field: k, value, label };
}

function stagedValue(pid, field) {
  for (let i = state.staged.length - 1; i >= 0; i--) {
    const o = state.staged[i];
    if ((o.op === "attr" || o.op === "created") && o.pid === pid && o.field === field) return o.value;
  }
  return undefined;
}

function renderPlayer() {
  const p = state.player;
  const box = $("#detail");
  box.className = "detail-card";
  box.innerHTML = "";
  box.append(el("h2", { textContent: p.name }));
  const where = p.blocks.map((b) => b.name).join(", ") || "no squad";
  box.append(el("div", { className: "detail-sub" }, badge(p.position), ` ${p.age ?? "?"} anos · ${where}`));

  const abilities = p.kind === "created" ? createdAbilities(p) : p.abilities;
  if (abilities) {
    box.append(el("div", { className: "section-title", textContent: "Habilidades" }));
    const grid = el("div", { className: "abil" });
    for (const k of ABIL_ORDER) {
      if (!(k in abilities)) continue;
      const pending = stagedValue(p.pid, p.kind === "created" ? createdField(k) : k);
      const v = pending ?? abilities[k];
      const inp = el("input", { type: "number", min: 40, max: 99, value: v, className: valClass(v) + (pending !== undefined ? " changed" : "") });
      inp.onchange = () => stageAbility(p, k, Number(inp.value), abilities[k]);
      grid.append(el("label", { textContent: ABIL_PT[k] }), inp);
    }
    box.append(grid);
  }
  if (p.skills) {
    box.append(el("div", { className: "section-title", textContent: "Habilidades do jogador" }));
    const chips = el("div", { className: "chips" });
    for (const [k, label] of Object.entries(SKILL_NAMES)) {
      const pending = stagedValue(p.pid, p.kind === "created" ? p.skillFields[k] : k);
      const on = pending !== undefined ? pending === 1 : p.skills.includes(k);
      if (p.kind === "created" && !p.skillFields[k]) continue;
      const c = el("span", { className: "chip" + (on ? " on" : ""), textContent: label });
      c.onclick = () => stage(skillOp(p, k, on ? 0 : 1, `${p.name}: ${label} ${on ? "off" : "on"}`), true);
      if (on || pending !== undefined) chips.append(c);
    }
    const add = el("span", { className: "chip", textContent: "+ add skill" });
    add.onclick = () => pickSkill(p);
    chips.append(add);
    box.append(chips);
  }
  if (p.kind !== "created" && p.blocks.length) {
    const actions = el("div", { className: "actions" });
    const mv = el("button", { className: "ghost", textContent: "Move to club…" });
    mv.onclick = () => pickClub(`Move ${p.name} to`, (b) => stage({ op: "move", pid: p.pid, from: state.block, to: b.block,
      label: `Move ${p.name}: ${state.squad.name} → ${b.name}` }));
    const rel = el("button", { className: "ghost", textContent: "Release" });
    rel.onclick = () => stage({ op: "release", pid: p.pid, block: state.block, label: `Release ${p.name} from ${state.squad.name}` });
    actions.append(mv, rel);
    box.append(actions);
  }
}

// The created character's fields use the Cheat Engine table's names.
const CREATED_MAP = { offensive_awareness: "offensive_awareness", ball_control: "ball_control", dribbling: "dribbling",
  tight_possession: "tight_possession", low_pass: "low_pass", lofted_pass: "lofted_pass", finishing: "finishing",
  heading: "heading", place_kicking: "place_kicking", curl: "curl", speed: "speed", acceleration: "acceleration",
  kicking_power: "kicking_power", jump: "jump", physical_contact: "physical_contact", balance: "balance",
  stamina: "stamina", defensive_awareness: "defensive_awareness", ball_winning: "ball_winning", aggression: "aggression",
  gk_awareness: "gk_awareness", gk_catching: "gk_catching", gk_clearing: "gk_clearing", gk_reflexes: "gk_reflexes",
  gk_reach: "gk_reach" };
function createdField(k) { return CREATED_MAP[k]; }
function createdAbilities(p) {
  const out = {};
  for (const k of ABIL_ORDER) if (p.fields[CREATED_MAP[k]] !== undefined) out[k] = p.fields[CREATED_MAP[k]];
  return out;
}

function stageAbility(p, k, value, original) {
  if (!(value >= 40 && value <= 99)) return toast("Abilities go from 40 to 99", true);
  if (value === original) return;
  const field = p.kind === "created" ? createdField(k) : k;
  stage({ op: p.kind === "created" ? "created" : "attr", pid: p.pid, field, value,
    label: `${p.name}: ${ABIL_PT[k]} ${original} → ${value}` }, true);
}

// ------------------------------------------------------------------ staging

async function stage(op, keepPlayer = false) {
  await guarded(async () => {
    const { label, ...clean } = op;
    state.staged = await call("stage", { op: clean });
    state.labels = state.labels || [];
    state.labels[state.staged.length - 1] = label;
    updateStaged();
    if (keepPlayer && state.player) renderPlayer();
    toast(label + " (staged)");
  });
}

function updateStaged() {
  $("#staged-count").textContent = state.staged.length;
  $("#btn-review").disabled = state.staged.length === 0;
}

async function openReview() {
  const ol = $("#staged-list");
  ol.innerHTML = "";
  state.staged.forEach((op, i) => {
    const undo = el("button", { className: "small ghost", textContent: "Undo" });
    undo.onclick = async () => {
      state.staged = await call("unstage", { index: i });
      state.labels.splice(i, 1);
      updateStaged();
      state.staged.length ? openReview() : $("#dlg-review").close();
      if (state.player) renderPlayer();
    };
    ol.append(el("li", {}, el("span", { textContent: state.labels?.[i] || JSON.stringify(op) }), undo));
  });
  const chk = $("#review-check");
  chk.className = "review-check muted";
  chk.textContent = "Checking the edits against the save…";
  if (!$("#dlg-review").open) $("#dlg-review").showModal();
  const r = await guarded(() => call("preview"));
  if (!r) return;
  if (r.newProblems.length) {
    chk.className = "review-check bad";
    chk.textContent = "These edits would break the save and will be refused: " + r.newProblems.join("; ");
    $("#btn-apply").disabled = true;
  } else {
    chk.className = "review-check good";
    chk.textContent = "Check passed: no new problems.";
    $("#btn-apply").disabled = false;
  }
}

async function applyEdits() {
  await guarded(async () => {
    const r = await call("apply");
    $("#dlg-review").close();
    state.staged = [];
    state.labels = [];
    updateStaged();
    toast(`Applied ${r.applied} edits${r.newPlayers ? ` (${r.newPlayers} players new to FL26)` : ""}. Backup: ${r.backup.split("\\").slice(-2).join("\\")}`);
    state.clubs = await call("clubs");
    renderClubs();
    if (state.block != null) await openClub(state.block);
    if (state.player) await openPlayer(state.player.pid);
  });
}

// ------------------------------------------------------------------ pickers

function openPicker(title, items, render, onPick, option) {
  $("#pick-title").textContent = title;
  const list = $("#pick-list");
  const filter = $("#pick-filter");
  filter.value = "";
  const opt = $("#pick-option");
  opt.classList.toggle("hidden", !option);
  if (option) { opt.querySelector("span").textContent = option; $("#pick-check").checked = true; }
  const draw = () => {
    const q = filter.value.trim().toLowerCase();
    list.innerHTML = "";
    for (const it of items) {
      const [main, side] = render(it);
      if (q && !(main + " " + side).toLowerCase().includes(q)) continue;
      const li = el("li", {}, el("span", { textContent: main }), el("span", { className: "muted", textContent: side }));
      li.onclick = () => { $("#dlg-pick").close(); onPick(it, $("#pick-check").checked); };
      list.append(li);
    }
  };
  filter.oninput = draw;
  draw();
  $("#dlg-pick").showModal();
  filter.focus();
}
function pickClub(title, onPick) {
  openPicker(title, state.clubs.filter((c) => c.block !== state.block), (c) => [c.name, `${c.size} players`], onPick);
}
function pickSkill(p) {
  const missing = Object.entries(SKILL_NAMES).filter(([k]) => !p.skills.includes(k)
    && (p.kind !== "created" || p.skillFields[k]));
  openPicker(`Add a skill to ${p.name}`, missing, ([, label]) => [label, ""],
    ([k, label]) => stage(skillOp(p, k, 1, `${p.name}: ${label} on`), true));
}
function pickManager() {
  const here = state.squad;
  openPicker(`New manager for ${here.name} (swap with another club)`, state.clubs.filter((c) => c.block !== state.block && c.manager),
    (c) => [c.manager, c.name],
    (c, withTactics) => withTactics
      ? stage({ op: "manager_swap", a: here.block, b: c.block, label: `Managers: ${c.manager} → ${here.name}, ${here.manager.name} → ${c.name} (with tactics)` })
      : guarded(async () => {
          const theirs = (await call("squad", { block: c.block })).manager;
          await stage({ op: "manager_set", block: here.block, coachId: theirs.id, name: theirs.name,
            label: `${here.name} manager: ${here.manager.name} → ${theirs.name} (keep ${here.name}'s tactics)` });
        }),
    "Bring the manager's tactics and formation (otherwise only the name changes)");
}

// ------------------------------------------------------------------ search

let searchTimer = null;
function onSearch() {
  clearTimeout(searchTimer);
  const q = $("#player-search").value;
  const box = $("#search-results");
  if (q.trim().length < 2) { box.classList.add("hidden"); return; }
  searchTimer = setTimeout(() => guarded(async () => {
    const rows = await call("search", { query: q });
    box.innerHTML = "";
    box.classList.remove("hidden");
    if (!rows.length) box.append(el("div", { textContent: "No players found" }));
    for (const r of rows) {
      const where = r.blocks.length ? r.blocks.map((b) => b.name).join(", ") : r.hasRecord ? "free / no squad" : "not in this career yet";
      const row = el("div", {}, el("span", { textContent: r.name }), el("span", { className: "where", textContent: where }));
      row.style.cursor = "pointer";
      if (!r.hasRecord) row.onclick = () => {
        box.classList.add("hidden");
        if (state.block == null) return;
        if (confirm(`${r.name} is not in this career yet. Create him at ${state.squad.name} with his efootballdb ratings?`))
          stage({ op: "new", pid: r.pid, block: state.block, label: `Create ${r.name} at ${state.squad.name}` });
      };
      if (r.hasRecord) row.onclick = async () => {
        box.classList.add("hidden");
        await openPlayer(r.pid);
        if (state.block != null && !r.blocks.some((b) => b.block === state.block))
          addOffer(r);
      };
      box.append(row);
    }
  }), 250);
}
function addOffer(r) {
  const actions = el("div", { className: "actions" });
  const btn = el("button", { className: "primary", textContent: `Add to ${state.squad.name}` });
  btn.onclick = () => r.blocks.length
    ? stage({ op: "move", pid: r.pid, from: r.blocks[0].block, to: state.block, label: `Move ${r.name}: ${r.blocks[0].name} → ${state.squad.name}` })
    : stage({ op: "add", pid: r.pid, block: state.block, label: `Add ${r.name} to ${state.squad.name}` });
  actions.append(btn);
  $("#detail").append(actions);
}

// ------------------------------------------------------------------ efootballdb sync

let syncPlan = null;
async function openSync(refresh = false) {
  const body = $("#sync-body");
  body.innerHTML = "<p class='muted'>Fetching the real squad…</p>";
  $("#sync-title").textContent = `Sync ${state.squad.name} with efootballdb`;
  if (!$("#dlg-sync").open) $("#dlg-sync").showModal();
  syncPlan = await guarded(() => call("sync_plan", { block: state.block, refresh }));
  if (!syncPlan) { body.innerHTML = ""; return; }
  body.innerHTML = "";
  const group = (title, note, items, render, checked = true) => {
    if (!items.length) return;
    const g = el("div", { className: "sync-group" });
    g.append(el("h3", {}, `${title} (${items.length}) `, el("span", { className: "muted", textContent: note })));
    for (const it of items) {
      const cb = el("input", { type: "checkbox", checked });
      it._cb = cb;
      const [main, side] = render(it);
      g.append(el("div", { className: "sync-row" }, cb, badge(it.position) || "", main, side));
    }
    body.append(g);
  };
  const tag = (t, cls) => el("span", { className: "tag " + cls, textContent: t });
  group("Move in", "currently at another club in your career", syncPlan.moveIn,
    (it) => [el("span", { textContent: it.name }), el("span", { className: "note", textContent: `from ${it.fromName}` })]);
  group("Add", "known to the career, without a club", syncPlan.add,
    (it) => [el("span", { textContent: it.name }), el("span", { className: "note", textContent: "free player" })]);
  group("Create", "new to this career", syncPlan.create,
    (it) => [el("span", { textContent: `${it.name}, ${it.age}` }),
      it.kind === "absent" ? tag("not in FL26: lookalike face", "absent") : tag("in FL26 database", "new")]);
  group("Release", "not in the real squad any more", syncPlan.release,
    (it) => [el("span", { textContent: it.name }), el("span", { className: "note", textContent: "becomes a free agent" })]);
  if (syncPlan.keep.length)
    body.append(el("p", { className: "muted", textContent: `${syncPlan.keep.length} players already match.` }));
  if (syncPlan.coach?.name && syncPlan.coach.name !== state.squad.manager?.name)
    body.append(el("p", { className: "muted", textContent: `Real coach: ${syncPlan.coach.name} (change it with "Change manager").` }));
}

async function stageSync() {
  const p = syncPlan;
  if (!p) return;
  const team = state.squad.name;
  const ops = [];
  for (const it of p.release) if (it._cb.checked) ops.push({ op: "release", pid: it.pid, block: p.block, label: `Release ${it.name} from ${team}` });
  for (const it of p.moveIn) if (it._cb.checked) ops.push({ op: "move", pid: it.careerPid, from: it.from, to: p.block, label: `Move ${it.name}: ${it.fromName} → ${team}` });
  for (const it of p.add) if (it._cb.checked) ops.push({ op: "add", pid: it.careerPid, block: p.block, label: `Add ${it.name} to ${team}` });
  for (const it of p.create) if (it._cb.checked) ops.push({ op: "new", pid: it.pid, block: p.block, shirt: it.shirt,
    label: `Create ${it.name} at ${team}` + (it.kind === "absent" ? " (new to FL26)" : "") });
  $("#dlg-sync").close();
  for (const op of ops) await stage(op);
  toast(`${ops.length} sync edits staged — review and apply when ready`);
}

// ------------------------------------------------------------------ backups / game state

async function openBackups() {
  const rows = await guarded(() => call("backups"));
  if (!rows) return;
  const ul = $("#backup-list");
  ul.innerHTML = "";
  if (!rows.length) ul.append(el("li", { textContent: "No backups yet" }));
  for (const b of rows) {
    const restore = el("button", { className: "small ghost", textContent: "Restore" });
    restore.onclick = async (ev) => {
      ev.stopPropagation();
      if (!confirm(`Restore ${b.name}? The current save is backed up first.`)) return;
      await guarded(async () => { await call("restore", { file: b.file }); $("#dlg-backups").close(); await openSave(state.save); toast("Backup restored"); });
    };
    const li = el("li", {}, el("span", { textContent: b.name }), restore);
    li.ondblclick = () => window.cl.reveal(b.file);
    ul.append(li);
  }
  $("#dlg-backups").showModal();
}

async function pollGame() {
  const r = await call("game_state").catch(() => null);
  const pill = $("#game-state");
  if (!r) return;
  pill.textContent = r.running ? "Game running — saving disabled" : "Game closed";
  pill.className = "pill " + (r.running ? "warn" : "ok");
  $("#btn-apply").title = r.running ? "Close the game first" : "";
}

// ------------------------------------------------------------------ wiring

$("#save-picker").onchange = (e) => openSave(e.target.value);
$("#club-filter").oninput = renderClubs;
$("#player-search").oninput = onSearch;
$("#btn-review").onclick = openReview;
$("#btn-close-review").onclick = () => $("#dlg-review").close();
$("#btn-apply").onclick = applyEdits;
$("#btn-close-pick").onclick = () => $("#dlg-pick").close();
$("#btn-backups").onclick = openBackups;
$("#btn-close-backups").onclick = () => $("#dlg-backups").close();
$("#btn-manager").onclick = pickManager;
$("#btn-sync").onclick = () => openSync(false);
$("#btn-sync-refresh").onclick = () => openSync(true);
$("#btn-close-sync").onclick = () => $("#dlg-sync").close();
$("#btn-sync-stage").onclick = stageSync;
loadSaves();
pollGame();
setInterval(pollGame, 4000);
