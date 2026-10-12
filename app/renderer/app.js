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
  const box = $("#toast");
  box.textContent = msg;
  box.className = "toast" + (error ? " error" : "");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => box.classList.add("hidden"), error ? 7000 : 3500);
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
  const r = await loadSaveOptions();
  if (r.saves.length) await openSave(r.saves[0].path);
}

async function loadSaveOptions() {
  const r = await call("list_saves");
  const sel = $("#save-picker");
  sel.innerHTML = "";
  for (const s of r.saves) {
    const d = new Date(s.modified * 1000).toLocaleString([], { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
    const n = /^BL0*(\d+)$/.exec(s.slot);
    sel.append(el("option", { value: s.path, textContent: n ? t("save.option", { n: Number(n[1]) + 1, d }) : s.slot, title: s.path }));
  }
  if (!r.saves.length) sel.append(el("option", { textContent: t("save.none") }));
  return r;
}

async function openSave(path) {
  await guarded(async () => {
    $("#squad-name").textContent = t("loading");
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
    li.title = c.manager ? t("clubs.manager", { name: c.manager }) : "";
    li.onclick = () => openClub(c.block);
    return li;
  };
  const shown = state.clubs.filter((c) => !q || c.name.toLowerCase().includes(q) || (c.manager || "").toLowerCase().includes(q));
  const mine = shown.find((c) => c.block === myBlock);
  if (mine && !q) {
    ul.append(el("li", { className: "group", textContent: t("clubs.yours") }), item(mine),
      el("li", { className: "group", textContent: t("clubs.all") }));
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
  meta.append(el("span", {}, icon("user"), t("squad.players", { n: s.players.length })));
  const body = $("#squad-body");
  body.innerHTML = "";
  for (const p of s.players) {
    const tr = el("tr", { className: (p.created ? "created " : "") + (state.player?.pid === p.pid ? "active" : "") });
    const name = el("span", { className: "pname", textContent: p.name });
    if (p.created) name.prepend(icon("star", "me-star"));
    if (p.captain) name.append(el("span", { className: "armband", textContent: "C", title: t("captain") }));
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
  const where = namedBlocks(p.blocks).map((b) => b.name).join(", ") || t("detail.noSquad");

  // header card
  const tags = el("div", { className: "p-tags" });
  if (p.kind === "created") tags.append(el("span", { className: "tag me" }, icon("star"), t("detail.yourPlayer")));
  if (inSquad?.captain) tags.append(el("span", { className: "tag cap", textContent: t("captain") }));
  box.append(el("div", { className: "p-head" },
    el("div", { className: "p-shirt", textContent: inSquad?.shirt ?? "–", title: t("detail.shirtNumber") }),
    el("div", {}, el("h2", { textContent: p.name }),
      el("div", { className: "p-sub" }, badge(p.position), t("detail.years", { n: p.age ?? "?" }), el("span", { textContent: "·" }), where),
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
    sec.append(el("div", { className: "section-title", textContent: t("detail.skills") }));
    const chips = el("div", { className: "chips" });
    for (const [k, label] of Object.entries(SKILL_NAMES)) {
      const pending = stagedValue(p.pid, p.kind === "created" ? p.skillFields[k] : k);
      const on = pending !== undefined ? pending === 1 : p.skills.includes(k);
      if (p.kind === "created" && !p.skillFields[k]) continue;
      const c = el("span", { className: "chip" + (on ? " on" : ""), textContent: label, title: on ? t("detail.chipRemove") : t("detail.chipAddBack") });
      c.onclick = () => stage(skillOp(p, k, on ? 0 : 1, t(on ? "lab.skillOff" : "lab.skillOn", { name: p.name, skill: label })), true);
      if (on || pending !== undefined) chips.append(c);
    }
    const add = el("span", { className: "chip add" }, icon("plus"), t("detail.addSkill"));
    add.onclick = () => pickSkill(p);
    chips.append(add);
    sec.append(chips);
    box.append(sec);
  }

  if (inSquad) {
    const sec = el("div", { className: "section" });
    sec.append(el("div", { className: "section-title", textContent: t("detail.club", { club: state.squad.name }) }));
    const row = el("div", { className: "field-row" });
    const shirt = el("input", { type: "number", min: 1, max: 99, value: inSquad.shirt ?? "", title: t("detail.shirtNumber") });
    shirt.onchange = () => {
      const n = Number(shirt.value);
      if (!(n >= 1 && n <= 99)) return toast(t("err.shirtRange"), true);
      const owner = state.squad.players.find((x) => x.shirt === n && x.pid !== p.pid);
      stage({ op: "shirt", pid: p.pid, block: state.block, shirt: n,
        label: t("lab.shirt", { name: p.name, from: inSquad.shirt, to: n }) + (owner ? t("lab.shirtFree", { owner: owner.name }) : "") }, true);
    };
    row.append(el("label", {}, icon("shirt"), t("detail.number"), shirt));
    if (!inSquad.captain) {
      const cap = el("button", { className: "ghost small", title: t("detail.captainTitle") },
        el("span", { className: "armband", textContent: "C" }), t("detail.makeCaptain"));
      cap.onclick = () => stage({ op: "captain", pid: p.pid, block: state.block, label: t("lab.captain", { club: state.squad.name, name: p.name }) }, true);
      row.append(cap);
    }
    sec.append(row);
    if (p.kind !== "created") {
      const actions = el("div", { className: "actions" });
      actions.style.marginTop = "12px";
      const mv = el("button", { className: "ghost" }, icon("move"), t("detail.move"));
      mv.onclick = () => pickClub(t("pick.moveTo", { name: p.name }), (b) => stage({ op: "move", pid: p.pid, from: state.block, to: b.block,
        label: t("lab.move", { name: p.name, from: state.squad.name, to: b.name }) }));
      const rel = el("button", { className: "ghost danger" }, icon("user-minus"), t("detail.release"));
      rel.onclick = () => stage({ op: "release", pid: p.pid, block: state.block, label: t("lab.release", { name: p.name, club: state.squad.name }) });
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
  if (!(value >= 40 && value <= 99)) return toast(t("err.abilityRange"), true);
  if (value === original) return;
  const field = p.kind === "created" ? createdField(k) : k;
  stage({ op: p.kind === "created" ? "created" : "attr", pid: p.pid, field, value,
    label: t("lab.ability", { name: p.name, ability: ABIL_PT[k], from: original, to: value }) }, true);
}

// ------------------------------------------------------------------ staging

async function stage(op, keepPlayer = false) {
  await guarded(async () => {
    state.staged = await call("stage", { op });
    updateStaged();
    if (keepPlayer && state.player) renderPlayer();
    if (!op.source) toast(t("staged", { label: op.label }));
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
    const undo = el("button", { className: "small ghost", title: t("review.undoTitle") }, icon("undo"), t("review.undo"));
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
  chk.textContent = t("review.checking");
  if (!$("#dlg-review").open) $("#dlg-review").showModal();
  const r = await guarded(() => call("preview"));
  if (!r) return;
  if (r.newProblems.length) {
    chk.className = "review-check bad";
    chk.replaceChildren(icon("alert"), t("review.refused") + r.newProblems.join("; "));
    $("#btn-apply").disabled = true;
  } else {
    chk.className = "review-check good";
    chk.replaceChildren(icon("check"), t("review.passed"));
    $("#btn-apply").disabled = false;
  }
}

async function undoAll() {
  if (!state.staged.length) return;
  if (!confirm(t("review.undoAllConfirm", { n: state.staged.length }))) return;
  await guarded(async () => {
    state.staged = await call("unstage_all");
    updateStaged();
    $("#dlg-review").close();
    if (state.player) renderPlayer();
    toast(t("review.undoAllDone"));
  });
}

async function applyEdits() {
  await guarded(async () => {
    const r = await call("apply");
    $("#dlg-review").close();
    state.staged = [];
    updateStaged();
    toast((r.applied === 1 ? t("review.applied1") : t("review.applied", { n: r.applied }))
      + (r.newPlayers ? t("review.newPlayers", { n: r.newPlayers }) : "") + t("review.inBackups"));
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
  openPicker(title, state.clubs.filter((c) => c.block !== state.block), (c) => [c.name, t("pick.players", { n: c.size })], onPick);
}
function pickSkill(p) {
  const missing = Object.entries(SKILL_NAMES).filter(([k]) => !p.skills.includes(k)
    && (p.kind !== "created" || p.skillFields[k]));
  openPicker(t("pick.addSkill", { name: p.name }), missing, ([, label]) => [label, ""],
    ([k, label]) => stage(skillOp(p, k, 1, t("lab.skillOn", { name: p.name, skill: label })), true));
}
function pickManager() {
  const here = state.squad;
  openPicker(t("pick.manager", { club: here.name }), state.clubs.filter((c) => c.block !== state.block && c.manager),
    (c) => [c.manager, c.name],
    (c, withTactics) => withTactics
      ? stage({ op: "manager_swap", a: here.block, b: c.block, label: t("lab.managerSwap", { a: c.manager, here: here.name, b: here.manager.name, there: c.name }) })
      : guarded(async () => {
          const theirs = (await call("squad", { block: c.block })).manager;
          await stage({ op: "manager_set", block: here.block, coachId: theirs.id, name: theirs.name,
            label: t("lab.managerSet", { club: here.name, from: here.manager.name, to: theirs.name }) });
        }),
    t("pick.managerOption"));
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
    if (!rows.length) box.append(el("div", { textContent: t("search.none") }));
    for (const r of rows) {
      const where = r.blocks.length ? (namedBlocks(r.blocks).map((b) => b.name).join(", ") || r.blocks[0].name) : r.hasRecord ? t("search.free") : t("search.notInCareer");
      const row = el("div", {}, el("span", { textContent: r.name }),
        el("span", { className: "where" }, icon(r.hasRecord ? (r.blocks.length ? "shield" : "user") : "user-plus"), where));
      if (!r.hasRecord) row.onclick = () => {
        box.classList.add("hidden");
        if (state.block == null) return;
        if (confirm(t("search.createConfirm", { name: r.name, club: state.squad.name })))
          stage({ op: "new", pid: r.pid, block: state.block, label: t("lab.create", { name: r.name, club: state.squad.name }) });
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
  const btn = el("button", { className: "primary" }, icon("user-plus"), t("search.addTo", { club: state.squad.name }));
  actions.className = "actions section";
  actions.style.marginTop = "14px";
  btn.onclick = () => r.blocks.length
    ? stage({ op: "move", pid: r.pid, from: r.blocks[0].block, to: state.block, label: t("lab.move", { name: r.name, from: r.blocks[0].name, to: state.squad.name }) })
    : stage({ op: "add", pid: r.pid, block: state.block, label: t("lab.add", { name: r.name, club: state.squad.name }) });
  actions.append(btn);
  $("#detail").append(actions);
}

// ------------------------------------------------------------------ efootballdb sync

let syncPlan = null;
async function openSync(refresh = false) {
  const body = $("#sync-body");
  body.replaceChildren(el("p", { className: "muted", textContent: t("sync.fetching") }));
  $("#sync-title").textContent = t("sync.title", { club: state.squad.name });
  if (!$("#dlg-sync").open) $("#dlg-sync").showModal();
  syncPlan = await guarded(() => call("sync_plan", { block: state.block, refresh }));
  if (!syncPlan) { body.innerHTML = ""; return; }
  body.innerHTML = "";
  const cc = syncPlan.crossCheck;
  if (cc) {
    let box;
    if (cc.error) box = el("div", { className: "cross muted" }, icon("alert"), t("cc.error", { source: cc.source, error: cc.error }));
    else if (cc.agree) box = el("div", { className: "cross good" }, icon("check"), t("cc.agree", { source: cc.source, n: cc.count }));
    else {
      const bits = [];
      if (cc.onlyPesmaster.length) bits.push(t("cc.alsoLists", { names: cc.onlyPesmaster.join(", ") }));
      if (cc.onlyEfdb.length) bits.push(t("cc.notList", { names: cc.onlyEfdb.join(", ") }));
      box = el("div", { className: "cross warn" }, icon("alert"), t("cc.differ", { source: cc.source, bits: bits.join("; ") }));
    }
    body.append(box);
  }
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
  const tag = (text, cls) => el("span", { className: "tag " + cls, textContent: text });
  group(t("sync.moveIn"), t("sync.moveInNote"), syncPlan.moveIn,
    (it) => [el("span", { textContent: it.name }), el("span", { className: "note", textContent: t("sync.from", { club: it.fromName }) })]);
  group(t("sync.add"), t("sync.addNote"), syncPlan.add,
    (it) => [el("span", { textContent: it.name }), el("span", { className: "note", textContent: t("sync.freePlayer") })]);
  group(t("sync.create"), t("sync.createNote"), syncPlan.create,
    (it) => [el("span", { textContent: `${it.name}, ${it.age}` }),
      it.kind === "absent" ? tag(t("sync.absentTag"), "absent") : tag(t("sync.dbTag"), "new")]);
  group(t("sync.release"), t("sync.releaseNote"), syncPlan.release,
    (it) => [el("span", { textContent: it.name }), el("span", { className: "note", textContent: t("sync.becomesFree") })]);
  group(t("sync.numbers"), t("sync.numbersNote"), syncPlan.renumber,
    (it) => [el("span", { textContent: it.name }), el("span", { className: "note", textContent: `${it.from ?? "–"} → ${it.to}` })]);
  syncPlan._numbersCb = el("input", { type: "checkbox", checked: true });
  body.append(el("label", { className: "pick-option" }, syncPlan._numbersCb,
    t("sync.numbersAll")));
  if (syncPlan.captain) {
    syncPlan._captainCb = el("input", { type: "checkbox", checked: true });
    body.append(el("label", { className: "pick-option" }, syncPlan._captainCb, t("sync.captainCb", { name: syncPlan.captain.name })));
  }
  body.append(el("p", { className: "muted", textContent: t("sync.takers") }));
  if (syncPlan.keep.length)
    body.append(el("p", { className: "muted", textContent: t("sync.alreadyMatch", { n: syncPlan.keep.length }) }));
  if (syncPlan.coach?.name && syncPlan.coach.name !== state.squad.manager?.name)
    body.append(el("p", { className: "muted", textContent: t("sync.realCoach", { name: syncPlan.coach.name }) }));
}

async function stageSync() {
  const p = syncPlan;
  if (!p) return;
  const team = state.squad.name;
  const ops = [];
  for (const it of p.release) if (it._cb.checked) ops.push({ op: "release", pid: it.pid, block: p.block, label: t("lab.release", { name: it.name, club: team }) });
  for (const it of p.moveIn) if (it._cb.checked) ops.push({ op: "move", pid: it.careerPid, from: it.from, to: p.block, label: t("lab.move", { name: it.name, from: it.fromName, to: team }) });
  for (const it of p.add) if (it._cb.checked) ops.push({ op: "add", pid: it.careerPid, block: p.block, label: t("lab.add", { name: it.name, club: team }) });
  for (const it of p.create) if (it._cb.checked) ops.push({ op: "new", pid: it.pid, block: p.block, shirt: it.shirt,
    label: t("lab.create", { name: it.name, club: team }) + (it.kind === "absent" ? t("lab.newToFl26") : "") });
  if (p._numbersCb?.checked && Object.keys(p.numbers).length)
    ops.push({ op: "renumber", block: p.block, numbers: p.numbers, label: t("lab.numbers", { club: team }) });
  if (p._captainCb?.checked && p.captain)
    ops.push({ op: "captain", block: p.block, pid: p.captain.pid, label: t("lab.captain", { club: team, name: p.captain.name }) });
  $("#dlg-sync").close();
  for (const op of ops) await stage({ ...op, source: t("lab.source", { club: team }) });
  toast(t("sync.staged", { n: ops.length }));
}

// ------------------------------------------------------------------ league sync

const KINDS = ["release", "move", "add", "create", "numbers", "captain"];
let leaguePlan = null;
const leagueKinds = Object.fromEntries(KINDS.map((k) => [k, true]));

async function openLeagues() {
  const pick = $("#league-picker");
  $("#league-body").replaceChildren(el("p", { className: "muted", textContent: t("league.reading") }));
  if (!$("#dlg-league").open) $("#dlg-league").showModal();
  const leagues = await guarded(() => call("leagues"));
  if (!leagues) return;
  pick.innerHTML = "";
  for (const lg of leagues)
    pick.append(el("option", { value: lg.id, textContent: t("league.option", { name: lg.name, c: lg.clubs, t: lg.total }) + (lg.mine ? t("league.yours") : "") }));
  const kinds = $("#league-kinds");
  kinds.innerHTML = "";
  for (const k of KINDS) {
    const cb = el("input", { type: "checkbox", checked: leagueKinds[k] });
    cb.onchange = () => { leagueKinds[k] = cb.checked; renderLeague(); };
    kinds.append(el("label", { className: "k-" + k }, cb, t("kind." + k)));
  }
  if (leagues.length) loadLeague(false);
  else $("#league-body").replaceChildren(el("p", { className: "muted", textContent: t("league.none") }));
}

async function loadLeague(refresh) {
  const id = Number($("#league-picker").value);
  $("#league-body").replaceChildren(el("p", { className: "muted", textContent: t(refresh ? "league.fetchingAgain" : "league.fetching") }));
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
    for (const [k, key] of [["move", "league.in"], ["add", "league.free"], ["create", "league.new"], ["release", "league.out"]])
      if (n(k)) counts.append(el("span", { className: "k-" + k, textContent: `${t(key)} ${n(k)}` }));
    if (!ops.length) counts.append(el("span", { className: "tag ok" }, icon("check"), t("league.upToDate")));
    body.append(el("details", { className: "league-club" + (cl._on ? "" : " off") },
      el("summary", {}, cb,
        el("span", {}, el("b", { textContent: cl.name }), el("span", { className: "muted", textContent: "  " + t("league.match", { n: cl.keep }) })),
        counts),
      el("div", { className: "ops" }, ...ops.map((o) => el("div", { className: "k-" + o.kind, textContent: o.label })),
        ...(cl.kept?.length ? [el("div", { className: "muted", textContent: t("league.kept", { n: leaguePlan.minSquad, names: cl.kept.join(", ") }) })] : []))));
  }
  if (leaguePlan.madeUp?.length)
    body.append(el("p", { className: "muted", textContent: t("league.madeUp", { clubs: leaguePlan.madeUp.join(", ") }) }));
  if (leaguePlan.skipped?.length)
    body.append(el("p", { className: "muted", textContent: t("league.skipped") + leaguePlan.skipped.join("; ") }));
  body.append(el("p", { className: "muted", textContent: t("league.footer") }));
  const total = leagueOps().length;
  $("#league-total").textContent = total ? t("league.total", { n: total }) : t("league.allMatch");
  $("#btn-league-stage").disabled = total === 0;
}

async function stageLeague() {
  const ops = leagueOps();
  if (!ops.length) return;
  await guarded(async () => {
    const source = t("lab.source", { club: leaguePlan.league });
    const r = await call("stage_many", { ops: ops.map((o) => ({ ...o, source })) });
    state.staged = r.staged;
    updateStaged();
    $("#dlg-league").close();
    toast(t("league.staged", { n: ops.length }));
  });
}

// ------------------------------------------------------------------ first-run setup

async function refreshSetup() {
  const st = await guarded(() => call("setup_status"));
  if (!st) return null;
  const step = (id, ok) => { $(id).className = "setup-step " + (ok ? "ok" : "bad"); };
  $("#setup-game").textContent = st.gameDir || t("setup.gameNotFound");
  step("#step-game", !!st.gameDir);
  let db;
  if (!st.gameDir) db = t("setup.dbNeedsGame");
  else if (st.dumpOk) db = t("setup.dbFound");
  else if (!st.siderInstalled) db = t("setup.dbNoSider");
  else if (st.moduleInstalled) db = t("setup.dbInstalled");
  else db = t("setup.dbMissing");
  $("#setup-db").textContent = db;
  step("#step-db", st.dumpOk);
  $("#btn-setup-module").hidden = st.dumpOk || !st.siderInstalled || st.moduleInstalled;
  $("#setup-saves").textContent = st.saveDir + (st.saveDirOk ? "" : t("setup.notFound"));
  step("#step-saves", st.saveDirOk);
  $("#btn-setup-done").disabled = !(st.gameDir && st.dumpOk && st.saveDirOk);
  return st;
}

function markFlags() {
  for (const b of document.querySelectorAll(".flag")) b.classList.toggle("on", b.dataset.lang === LANG);
}

async function switchLanguage(lang) {
  if (lang === LANG) return;
  setLang(lang);
  markFlags();
  await call("set_language", { lang }).catch(() => null);
  // redraw whatever is on screen in the new language
  renderClubs();
  if (state.squad) renderSquad();
  if (state.player) renderPlayer();
  else $("#detail").replaceChildren(icon("user", "big"), el("span", { textContent: t("detail.empty") }));
  if (!state.squad) $("#squad-name").textContent = t("squad.open");
  if (state.save) {
    const sel = $("#save-picker"), cur = sel.value;
    await loadSaveOptions();
    sel.value = cur;
  }
  pollGame();
  refreshSetup();
}

async function openSetup() {
  window.cl.version().then((v) => { $("#setup-version").textContent = `CareerLab ${v}`; });
  markFlags();
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
  if (!rows.length) ul.append(el("li", { className: "muted", textContent: t("bk.none") }));
  for (const b of rows) {
    // 20261011-193531-careerlab-307-edits -> "11/10/2026 19:35"
    const m = b.name.match(/^(\d{4})(\d\d)(\d\d)-(\d\d)(\d\d)\d\d-(.*)$/);
    const when = m ? `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}` : b.name;
    const rest = m ? m[6] : b.name;
    let title = b.title;
    if (!title) {                                       // made before descriptions existed
      const n = rest.match(/careerlab-(\d+)-edits/);
      title = b.kind === "restore" ? t("bk.beforeRestore") : n ? t("bk.nEdits", { n: n[1] }) : rest.replace(/-/g, " ");
    }
    const lead = b.kind === "apply" ? t("bk.before") : "";
    const restore = el("button", { className: "small ghost" }, icon("undo"), t("bk.restore"));
    restore.onclick = async (ev) => {
      ev.preventDefault(); ev.stopPropagation();
      if (!confirm(t("bk.confirm", { when }) + (b.kind === "apply" ? t("bk.undoes", { title }) : "") + t("bk.backedUp"))) return;
      await guarded(async () => { await call("restore", { file: b.file }); $("#dlg-backups").close(); await openSave(state.save); toast(t("bk.restored")); });
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
      if (b.edits.length > 300) list.append(el("li", { className: "muted", textContent: t("bk.more", { n: b.edits.length - 300 }) }));
      if (b.clubs?.length) det.append(el("div", { className: "muted bk-clubs", textContent: t("bk.clubs", { list: b.clubs.join(", ") }) }));
      det.append(list);
    } else head.classList.add("plain");
    head.ondblclick = () => window.cl.reveal(b.file);
    const li = el("li", { title: t("bk.itemTitle") }, det);
    ul.append(li);
  }
  $("#dlg-backups").showModal();
}

async function pollGame() {
  const r = await call("game_state").catch(() => null);
  const pill = $("#game-state");
  if (!r) return;
  pill.textContent = r.running ? t("game.running") : t("game.closed");
  pill.className = "pill " + (r.running ? "warn" : "ok");
  $("#btn-apply").title = r.running ? t("game.closeFirst") : "";
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
$("#btn-setup-game").onclick = () => chooseFolder("set_game_dir", t("setup.pickGame"));
$("#btn-setup-saves").onclick = () => chooseFolder("set_save_dir", t("setup.pickSaves"));
$("#btn-setup-module").onclick = () => guarded(async () => { await call("install_dump_module"); await refreshSetup(); toast(t("setup.readerInstalled")); });
$("#btn-setup-check").onclick = refreshSetup;
$("#btn-setup-done").onclick = () => { $("#dlg-setup").close(); loadSaves(); };
$("#dlg-setup").addEventListener("cancel", (e) => { if ($("#btn-setup-done").disabled) e.preventDefault(); });
for (const b of document.querySelectorAll(".flag")) b.onclick = () => switchLanguage(b.dataset.lang);
applyStatic();
call("set_language", { lang: LANG }).catch(() => null);
startup();
pollGame();
setInterval(pollGame, 4000);
