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
// Unidentified internal squads (representative teams etc.) are named "Squad <n>": not worth showing.
const namedBlocks = (blocks) => blocks.filter((b) => !/^Squad \d+$/.test(b.name));
const SVGNS = "http://www.w3.org/2000/svg";
function icon(name, cls = "") {
  const svg = document.createElementNS(SVGNS, "svg");
  svg.setAttribute("class", "i " + cls);
  const use = document.createElementNS(SVGNS, "use");
  use.setAttribute("href", "#i-" + name);
  svg.append(use);
  return svg;
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
    const d = new Date(s.modified * 1000).toLocaleString([], { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
    const n = /^BL0*(\d+)$/.exec(s.slot);
    sel.append(el("option", { value: s.path, textContent: `${n ? "Slot " + (Number(n[1]) + 1) : s.slot}  ·  saved ${d}`, title: s.path }));
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
    const info = $("#career-info");
    info.innerHTML = "";
    if (me) info.append(icon("user"), el("b", { textContent: me.name }), `${me.age} · ${me.club || ""}`);
    state.clubs = await call("clubs");
    renderClubs();
    updateStaged();
    $("#btn-league").disabled = false;
    if (me && me.block != null) await openClub(me.block);
  });
}

// ------------------------------------------------------------------ clubs

function renderClubs() {
  const q = $("#club-filter").value.trim().toLowerCase();
  const ul = $("#club-list");
  ul.innerHTML = "";
  const myBlock = state.summary?.me?.block;
  $("#club-count").textContent = state.clubs.length ? state.clubs.length : "";
  const item = (c) => {
    const li = el("li", { className: c.block === state.block ? "active" : "" },
      el("span", { textContent: c.name, className: "name" + (c.block === myBlock ? " me" : "") }),
      el("span", { className: "size", textContent: c.size }));
    if (c.block === myBlock) li.prepend(icon("star", "me-star"));
    li.title = c.manager ? `Manager: ${c.manager}` : "";
    li.onclick = () => openClub(c.block);
    return li;
  };
  const shown = state.clubs.filter((c) => !q || c.name.toLowerCase().includes(q) || (c.manager || "").toLowerCase().includes(q));
  const mine = shown.find((c) => c.block === myBlock);
  if (mine && !q) {
    ul.append(el("li", { className: "group", textContent: "Your club" }), item(mine),
      el("li", { className: "group", textContent: "All clubs" }));
  }
  for (const c of shown) if (q || c.block !== myBlock) ul.append(item(c));
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
  const meta = $("#squad-manager");
  meta.innerHTML = "";
  if (s.manager?.name) meta.append(el("span", {}, icon("whistle"), s.manager.name));
  meta.append(el("span", {}, icon("user"), `${s.players.length} players`));
  const body = $("#squad-body");
  body.innerHTML = "";
  for (const p of s.players) {
    const tr = el("tr", { className: (p.created ? "created " : "") + (state.player?.pid === p.pid ? "active" : "") });
    const name = el("span", { className: "pname", textContent: p.name });
    if (p.created) name.prepend(icon("star", "me-star"));
    if (p.captain) name.append(el("span", { className: "armband", textContent: "C", title: "Captain" }));
    tr.append(el("td", { className: "c-num", textContent: p.shirt ?? "" }), el("td", {}, badge(p.position)),
      el("td", {}, name), el("td", { className: "c-num", textContent: p.age ?? "" }),
      el("td", { className: "c-num", textContent: p.speed ?? "" }));
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

const ABIL_GROUPS = [
  ["Ataque", ["offensive_awareness", "ball_control", "dribbling", "tight_possession", "low_pass", "lofted_pass",
    "finishing", "heading", "place_kicking", "curl"]],
  ["Físico", ["speed", "acceleration", "kicking_power", "jump", "physical_contact", "balance", "stamina"]],
  ["Defesa", ["defensive_awareness", "ball_winning", "aggression"]],
  ["Goleiro", ["gk_awareness", "gk_catching", "gk_clearing", "gk_reflexes", "gk_reach"]],
];

function abilityGrid(p, abilities, keys) {
  const grid = el("div", { className: "abil" });
  for (const k of keys) {
    if (!(k in abilities)) continue;
    const pending = stagedValue(p.pid, p.kind === "created" ? createdField(k) : k);
    const v = pending ?? abilities[k];
    const bar = el("div", { className: "bar " + valClass(v) }, el("i"));
    bar.firstChild.style.width = `${Math.max(4, ((v - 40) / 59) * 100)}%`;
    const inp = el("input", { type: "number", min: 40, max: 99, value: v, className: valClass(v) + (pending !== undefined ? " changed" : "") });
    inp.onchange = () => stageAbility(p, k, Number(inp.value), abilities[k]);
    grid.append(el("label", { textContent: ABIL_PT[k], title: ABIL_PT[k] }), bar, inp);
  }
  return grid;
}

function renderPlayer() {
  const p = state.player;
  const box = $("#detail");
  box.className = "detail-card";
  box.innerHTML = "";
  const inSquad = state.squad?.players.find((x) => x.pid === p.pid);
  const where = namedBlocks(p.blocks).map((b) => b.name).join(", ") || "no squad";

  // header card
  const tags = el("div", { className: "p-tags" });
  if (p.kind === "created") tags.append(el("span", { className: "tag me" }, icon("star"), "Your player"));
  if (inSquad?.captain) tags.append(el("span", { className: "tag cap", textContent: "Captain" }));
  box.append(el("div", { className: "p-head" },
    el("div", { className: "p-shirt", textContent: inSquad?.shirt ?? "–", title: "Shirt number" }),
    el("div", {}, el("h2", { textContent: p.name }),
      el("div", { className: "p-sub" }, badge(p.position), `${p.age ?? "?"} anos`, el("span", { textContent: "·" }), where),
      tags.childNodes.length ? tags : "")));

  // abilities, grouped like the game; goalkeeping folded away for outfield players
  const abilities = p.kind === "created" ? createdAbilities(p) : p.abilities;
  if (abilities) {
    const sec = el("div", { className: "section" });
    const isGk = p.position === "GK";
    for (const [title, keys] of ABIL_GROUPS) {
      const vals = keys.filter((k) => k in abilities).map((k) => stagedValue(p.pid, p.kind === "created" ? createdField(k) : k) ?? abilities[k]);
      if (!vals.length) continue;
      const avg = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
      const head = el("div", { className: "section-title" }, title, el("span", { className: "avg " + valClass(avg), textContent: avg }));
      if (title === "Goleiro" && !isGk) {
        head.prepend(icon("chevron"));
        sec.append(el("details", { className: "abil-group" }, el("summary", {}, head), abilityGrid(p, abilities, keys)));
      } else sec.append(head, abilityGrid(p, abilities, keys));
    }
    box.append(sec);
  }

  if (p.skills) {
    const sec = el("div", { className: "section" });
    sec.append(el("div", { className: "section-title", textContent: "Habilidades do jogador" }));
    const chips = el("div", { className: "chips" });
    for (const [k, label] of Object.entries(SKILL_NAMES)) {
      const pending = stagedValue(p.pid, p.kind === "created" ? p.skillFields[k] : k);
      const on = pending !== undefined ? pending === 1 : p.skills.includes(k);
      if (p.kind === "created" && !p.skillFields[k]) continue;
      const c = el("span", { className: "chip" + (on ? " on" : ""), textContent: label, title: on ? "Click to remove" : "Click to add back" });
      c.onclick = () => stage(skillOp(p, k, on ? 0 : 1, `${p.name}: ${label} ${on ? "off" : "on"}`), true);
      if (on || pending !== undefined) chips.append(c);
    }
    const add = el("span", { className: "chip add" }, icon("plus"), "Add skill");
    add.onclick = () => pickSkill(p);
    chips.append(add);
    sec.append(chips);
    box.append(sec);
  }

  if (inSquad) {
    const sec = el("div", { className: "section" });
    sec.append(el("div", { className: "section-title", textContent: `Clube · ${state.squad.name}` }));
    const row = el("div", { className: "field-row" });
    const shirt = el("input", { type: "number", min: 1, max: 99, value: inSquad.shirt ?? "", title: "Shirt number" });
    shirt.onchange = () => {
      const n = Number(shirt.value);
      if (!(n >= 1 && n <= 99)) return toast("Shirt numbers go from 1 to 99", true);
      const owner = state.squad.players.find((x) => x.shirt === n && x.pid !== p.pid);
      stage({ op: "shirt", pid: p.pid, block: state.block, shirt: n,
        label: `${p.name}: shirt ${inSquad.shirt} → ${n}` + (owner ? ` (${owner.name} gets a free number)` : "") }, true);
    };
    row.append(el("label", {}, icon("shirt"), "Número", shirt));
    if (!inSquad.captain) {
      const cap = el("button", { className: "ghost small", title: "Wears the armband when he is in the starting XI" },
        el("span", { className: "armband", textContent: "C" }), "Make captain");
      cap.onclick = () => stage({ op: "captain", pid: p.pid, block: state.block, label: `${state.squad.name} captain: ${p.name}` }, true);
      row.append(cap);
    }
    sec.append(row);
    if (p.kind !== "created") {
      const actions = el("div", { className: "actions" });
      actions.style.marginTop = "12px";
      const mv = el("button", { className: "ghost" }, icon("move"), "Move to club…");
      mv.onclick = () => pickClub(`Move ${p.name} to`, (b) => stage({ op: "move", pid: p.pid, from: state.block, to: b.block,
        label: `Move ${p.name}: ${state.squad.name} → ${b.name}` }));
      const rel = el("button", { className: "ghost danger" }, icon("user-minus"), "Release");
      rel.onclick = () => stage({ op: "release", pid: p.pid, block: state.block, label: `Release ${p.name} from ${state.squad.name}` });
      actions.append(mv, rel);
      sec.append(actions);
    }
    box.append(sec);
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
    state.staged = await call("stage", { op });
    updateStaged();
    if (keepPlayer && state.player) renderPlayer();
    if (!op.source) toast(op.label + " (staged)");
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
    const undo = el("button", { className: "small ghost", title: "Remove this edit" }, icon("undo"), "Undo");
    undo.onclick = async () => {
      state.staged = await call("unstage", { index: i });
      updateStaged();
      state.staged.length ? openReview() : $("#dlg-review").close();
      if (state.player) renderPlayer();
    };
    ol.append(el("li", {}, el("div", {}, el("span", { textContent: op.label || op.op }), undo)));
  });
  const chk = $("#review-check");
  chk.className = "review-check muted";
  chk.textContent = "Checking the edits against the save…";
  if (!$("#dlg-review").open) $("#dlg-review").showModal();
  const r = await guarded(() => call("preview"));
  if (!r) return;
  if (r.newProblems.length) {
    chk.className = "review-check bad";
    chk.replaceChildren(icon("alert"), "These edits would break the save and will be refused: " + r.newProblems.join("; "));
    $("#btn-apply").disabled = true;
  } else {
    chk.className = "review-check good";
    chk.replaceChildren(icon("check"), "Check passed: no new problems.");
    $("#btn-apply").disabled = false;
  }
}

async function undoAll() {
  if (!state.staged.length) return;
  if (!confirm(`Remove all ${state.staged.length} staged edits? Nothing has been written yet, so the save is not touched.`)) return;
  await guarded(async () => {
    state.staged = await call("unstage_all");
    updateStaged();
    $("#dlg-review").close();
    if (state.player) renderPlayer();
    toast("All staged edits removed");
  });
}

async function applyEdits() {
  await guarded(async () => {
    const r = await call("apply");
    $("#dlg-review").close();
    state.staged = [];
    updateStaged();
    toast(`Applied ${r.applied} edit${r.applied === 1 ? "" : "s"}${r.newPlayers ? ` (${r.newPlayers} players new to FL26)` : ""}. The career as it was is in Backups.`);
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
      const where = r.blocks.length ? (namedBlocks(r.blocks).map((b) => b.name).join(", ") || r.blocks[0].name) : r.hasRecord ? "free / no squad" : "not in this career yet";
      const row = el("div", {}, el("span", { textContent: r.name }),
        el("span", { className: "where" }, icon(r.hasRecord ? (r.blocks.length ? "shield" : "user") : "user-plus"), where));
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
  const btn = el("button", { className: "primary" }, icon("user-plus"), `Add to ${state.squad.name}`);
  actions.className = "actions section";
  actions.style.marginTop = "14px";
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
  group("Shirt numbers", "players already here who change number", syncPlan.renumber,
    (it) => [el("span", { textContent: it.name }), el("span", { className: "note", textContent: `${it.from ?? "–"} → ${it.to}` })]);
  syncPlan._numbersCb = el("input", { type: "checkbox", checked: true });
  body.append(el("label", { className: "pick-option" }, syncPlan._numbersCb,
    " Give every player his real shirt number (new arrivals included)"));
  if (syncPlan.captain) {
    syncPlan._captainCb = el("input", { type: "checkbox", checked: true });
    body.append(el("label", { className: "pick-option" }, syncPlan._captainCb, ` Make ${syncPlan.captain.name} captain (real captain; wears the armband when he starts)`));
  }
  body.append(el("p", { className: "muted", textContent: "Set-piece takers are chosen by the AI manager in Become a Legend, so they are not synced." }));
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
  if (p._numbersCb?.checked && Object.keys(p.numbers).length)
    ops.push({ op: "renumber", block: p.block, numbers: p.numbers, label: `${team}: real shirt numbers` });
  if (p._captainCb?.checked && p.captain)
    ops.push({ op: "captain", block: p.block, pid: p.captain.pid, label: `${team} captain: ${p.captain.name}` });
  $("#dlg-sync").close();
  for (const op of ops) await stage({ ...op, source: `${team} sync` });
  toast(`${ops.length} sync edits staged — review and apply when ready`);
}

// ------------------------------------------------------------------ league sync

const KINDS = { release: "Releases", move: "Moves", add: "Free players", create: "New players",
  numbers: "Shirt numbers", captain: "Captains" };
let leaguePlan = null;
const leagueKinds = Object.fromEntries(Object.keys(KINDS).map((k) => [k, true]));

async function openLeagues() {
  const pick = $("#league-picker");
  $("#league-body").innerHTML = "<p class='muted'>Reading efootballdb's league list…</p>";
  if (!$("#dlg-league").open) $("#dlg-league").showModal();
  const leagues = await guarded(() => call("leagues"));
  if (!leagues) return;
  pick.innerHTML = "";
  for (const lg of leagues)
    pick.append(el("option", { value: lg.id, textContent: `${lg.name} (${lg.clubs}/${lg.total} clubs)${lg.mine ? " — your league" : ""}` }));
  const kinds = $("#league-kinds");
  kinds.innerHTML = "";
  for (const [k, label] of Object.entries(KINDS)) {
    const cb = el("input", { type: "checkbox", checked: leagueKinds[k] });
    cb.onchange = () => { leagueKinds[k] = cb.checked; renderLeague(); };
    kinds.append(el("label", { className: "k-" + k }, cb, label));
  }
  if (leagues.length) loadLeague(false);
  else $("#league-body").innerHTML = "<p class='muted'>No efootballdb league matches this career's clubs.</p>";
}

async function loadLeague(refresh) {
  const id = Number($("#league-picker").value);
  $("#league-body").innerHTML = `<p class='muted'>Fetching every squad${refresh ? " again" : ""} (one request per club, cached for a day)…</p>`;
  leaguePlan = await guarded(() => call("league_plan", { comp_id: id, refresh }));
  if (!leaguePlan) { $("#league-body").innerHTML = ""; return; }
  for (const cl of leaguePlan.clubs) cl._on = true;
  renderLeague();
}

function leagueOps() {
  const ops = [];
  for (const cl of leaguePlan?.clubs || [])
    if (cl._on) for (const op of cl.ops) if (leagueKinds[op.kind]) ops.push(op);
  return ops;
}

function renderLeague() {
  const body = $("#league-body");
  if (!leaguePlan) return;
  body.innerHTML = "";
  for (const cl of leaguePlan.clubs) {
    const cb = el("input", { type: "checkbox", checked: cl._on });
    cb.onclick = (ev) => ev.stopPropagation();
    cb.onchange = () => { cl._on = cb.checked; renderLeague(); };
    const ops = cl.ops.filter((o) => leagueKinds[o.kind]);
    const n = (k) => ops.filter((o) => o.kind === k).length;
    const counts = el("span", { className: "counts" });
    for (const [k, t] of [["move", "→ in"], ["add", "+ free"], ["create", "+ new"], ["release", "− out"]])
      if (n(k)) counts.append(el("span", { className: "k-" + k, textContent: `${t} ${n(k)}` }));
    if (!ops.length) counts.append(el("span", { className: "tag ok" }, icon("check"), "Up to date"));
    body.append(el("details", { className: "league-club" + (cl._on ? "" : " off") },
      el("summary", {}, cb,
        el("span", {}, el("b", { textContent: cl.name }), el("span", { className: "muted", textContent: `  ${cl.keep} already match` })),
        counts),
      el("div", { className: "ops" }, ...ops.map((o) => el("div", { className: "k-" + o.kind, textContent: o.label })),
        ...(cl.kept?.length ? [el("div", { className: "muted", textContent: `Kept so the squad stays at ${leaguePlan.minSquad}+: ${cl.kept.join(", ")}` })] : []))));
  }
  if (leaguePlan.madeUp?.length)
    body.append(el("p", { className: "muted", textContent: `Left as they are: ${leaguePlan.madeUp.join(", ")}. eFootball has no player licence there (invented names), so FL26's own squad is kept.` }));
  if (leaguePlan.skipped?.length)
    body.append(el("p", { className: "muted", textContent: "Skipped: " + leaguePlan.skipped.join("; ") }));
  body.append(el("p", { className: "muted", textContent: "Players FL26 lacks borrow a little-known player's ID and the face of a player of the same nationality. Coaches and set-piece takers are not synced." }));
  const total = leagueOps().length;
  $("#league-total").textContent = total ? `${total} edits selected` : "Every club already matches efootballdb";
  $("#btn-league-stage").disabled = total === 0;
}

async function stageLeague() {
  const ops = leagueOps();
  if (!ops.length) return;
  await guarded(async () => {
    const source = `${leaguePlan.league} sync`;
    const r = await call("stage_many", { ops: ops.map((o) => ({ ...o, source })) });
    state.staged = r.staged;
    updateStaged();
    $("#dlg-league").close();
    toast(`${ops.length} league edits staged — review and apply when ready`);
  });
}

// ------------------------------------------------------------------ first-run setup

async function refreshSetup() {
  const st = await guarded(() => call("setup_status"));
  if (!st) return null;
  const step = (id, ok) => { $(id).className = "setup-step " + (ok ? "ok" : "bad"); };
  $("#setup-game").textContent = st.gameDir || "Not found: choose the folder that has FL_2026.exe";
  step("#step-game", !!st.gameDir);
  let db;
  if (!st.gameDir) db = "Needs the game folder first.";
  else if (st.dumpOk) db = "Found (written by the game through Sider).";
  else if (!st.siderInstalled) db = "Sider is not installed in this game folder, so the database cannot be read.";
  else if (st.moduleInstalled) db = "Reader installed. Start FL2026 once, wait for the main menu, close it, then press Check again.";
  else db = "Not found yet. Install the reader (a read-only Sider module), then start the game once.";
  $("#setup-db").textContent = db;
  step("#step-db", st.dumpOk);
  $("#btn-setup-module").hidden = st.dumpOk || !st.siderInstalled || st.moduleInstalled;
  $("#setup-saves").textContent = st.saveDir + (st.saveDirOk ? "" : " (not found)");
  step("#step-saves", st.saveDirOk);
  $("#btn-setup-done").disabled = !(st.gameDir && st.dumpOk && st.saveDirOk);
  return st;
}

async function openSetup() {
  window.cl.version().then((v) => { $("#setup-version").textContent = `CareerLab ${v}`; });
  await refreshSetup();
  if (!$("#dlg-setup").open) $("#dlg-setup").showModal();
}

async function chooseFolder(method, title) {
  const dir = await window.cl.pickFolder(title);
  if (!dir) return;
  await guarded(async () => { await call(method, { path: dir }); });
  await refreshSetup();
}

async function startup() {
  const st = await refreshSetup();
  if (st && st.gameDir && st.dumpOk && st.saveDirOk) return loadSaves();
  openSetup();
}

// ------------------------------------------------------------------ backups / game state

async function openBackups() {
  const rows = await guarded(() => call("backups"));
  if (!rows) return;
  const ul = $("#backup-list");
  ul.innerHTML = "";
  if (!rows.length) ul.append(el("li", { className: "muted", textContent: "No backups yet" }));
  for (const b of rows) {
    // 20261011-193531-careerlab-307-edits -> "11/10/2026 19:35"
    const m = b.name.match(/^(\d{4})(\d\d)(\d\d)-(\d\d)(\d\d)\d\d-(.*)$/);
    const when = m ? `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}` : b.name;
    const rest = m ? m[6] : b.name;
    let title = b.title;
    if (!title) {                                       // made before descriptions existed
      const n = rest.match(/careerlab-(\d+)-edits/);
      title = b.kind === "restore" ? "Before a restore" : n ? `${n[1]} edits` : rest.replace(/-/g, " ");
    }
    const lead = b.kind === "apply" ? "Before: " : "";
    const restore = el("button", { className: "small ghost" }, icon("undo"), "Restore");
    restore.onclick = async (ev) => {
      ev.preventDefault(); ev.stopPropagation();
      if (!confirm(`Restore the save as it was on ${when}?${b.kind === "apply" ? `\nThis undoes: ${title}.` : ""}\nThe current save is backed up first.`)) return;
      await guarded(async () => { await call("restore", { file: b.file }); $("#dlg-backups").close(); await openSave(state.save); toast("Backup restored"); });
    };
    const head = el("summary", { className: "bk-head" },
      icon(b.kind === "restore" ? "undo" : b.kind === "apply" ? "history" : "save"),
      el("div", { className: "bk-text" },
        el("div", {}, el("b", { textContent: lead + title })),
        el("div", { className: "muted bk-sub", textContent: [when, b.summary].filter(Boolean).join("  ·  ") })),
      restore);
    const det = el("details", { className: "bk" }, head);
    if (b.edits?.length) {
      const list = el("ol", { className: "bk-edits" });
      for (const e of b.edits.slice(0, 300)) list.append(el("li", { textContent: e }));
      if (b.edits.length > 300) list.append(el("li", { className: "muted", textContent: `…and ${b.edits.length - 300} more` }));
      if (b.clubs?.length) det.append(el("div", { className: "muted bk-clubs", textContent: `Clubs: ${b.clubs.join(", ")}` }));
      det.append(list);
    } else head.classList.add("plain");
    head.ondblclick = () => window.cl.reveal(b.file);
    const li = el("li", { title: "Click to see the edits · double-click to show the file" }, det);
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
$("#btn-undo-all").onclick = undoAll;
$("#btn-close-pick").onclick = () => $("#dlg-pick").close();
$("#btn-backups").onclick = openBackups;
$("#btn-close-backups").onclick = () => $("#dlg-backups").close();
$("#btn-manager").onclick = pickManager;
$("#btn-sync").onclick = () => openSync(false);
$("#btn-sync-refresh").onclick = () => openSync(true);
$("#btn-close-sync").onclick = () => $("#dlg-sync").close();
$("#btn-sync-stage").onclick = stageSync;
$("#btn-league").onclick = openLeagues;
$("#league-picker").onchange = () => loadLeague(false);
$("#btn-league-refresh").onclick = () => loadLeague(true);
$("#btn-close-league").onclick = () => $("#dlg-league").close();
$("#btn-league-stage").onclick = stageLeague;
$("#btn-setup").onclick = openSetup;
$("#btn-setup-game").onclick = () => chooseFolder("set_game_dir", "Football Life 2026 folder (with FL_2026.exe)");
$("#btn-setup-saves").onclick = () => chooseFolder("set_save_dir", "Become a Legend saves folder");
$("#btn-setup-module").onclick = () => guarded(async () => { await call("install_dump_module"); await refreshSetup(); toast("Database reader installed: start the game once"); });
$("#btn-setup-check").onclick = refreshSetup;
$("#btn-setup-done").onclick = () => { $("#dlg-setup").close(); loadSaves(); };
$("#dlg-setup").addEventListener("cancel", (e) => { if ($("#btn-setup-done").disabled) e.preventDefault(); });
startup();
pollGame();
setInterval(pollGame, 4000);
