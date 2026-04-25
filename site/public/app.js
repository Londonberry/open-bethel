/* =========================================================================
   open-bethel — site controller
   Router + view renderers + utilities. No framework; no build step.
   ========================================================================= */

// -----------------------------------------------------------------------------
// State
// -----------------------------------------------------------------------------
const state = {
  data: null,
  teamBySlug: new Map(),
  pairMap: new Map(), // "a|b" (sorted) → hops
  sort: { col: "bethel", dir: "desc" },
  filters: { search: "", classFilter: "", minGames: 0, normalize: true, includeOOS: false },
  compare: { a: null, b: null, focusInput: null },
  maxBethel: 0,
};

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------
const app = document.getElementById("app");

/** Title-case a slug for display, with a few hand-tuned exceptions. */
function displayName(slug) {
  if (!slug) return "";
  const special = {
    "pk-yonge-blue-wave": "P.K. Yonge Blue Wave",
    "st-johns-country-day-spartans": "St. Johns Country Day Spartans",
    "st-john-paul-ii-academy-eagles": "St. John Paul II Academy Eagles",
    "st-joseph-academy-fighting-flashes": "St. Joseph Academy Fighting Flashes",
    "st-augustine-yellow-jackets": "St. Augustine Yellow Jackets",
    "st-petersburg-catholic-barons": "St. Petersburg Catholic Barons",
    "st-andrews-scots": "St. Andrew's Scots",
    "st-francis-catholic-academy-wolves": "St. Francis Catholic Academy Wolves",
    "saint-francis-catholic-academy-wolves": "St. Francis Catholic Academy Wolves",
    "img-academy-none": "IMG Academy",
    "nsu-university-school-sharks": "NSU University School Sharks",
  };
  if (special[slug]) return special[slug];
  return slug
    .split("-")
    .map((w) => {
      if (w.length <= 1) return w.toUpperCase();
      if (w === "ii" || w === "iii") return w.toUpperCase();
      return w[0].toUpperCase() + w.slice(1);
    })
    .join(" ");
}

/** Returns the strength value to display for a team row, respecting the
 *  normalize toggle. Raw Bethel is preserved for win-probability math; this
 *  helper is for display only. */
function displayStrength(rankRow) {
  if (!rankRow) return null;
  return state.filters.normalize ? rankRow.bethel_norm : rankRow.bethel;
}

function fmtNum(n, decimals = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return Number(n).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtInt(n) {
  if (n === null || n === undefined) return "—";
  return Number(n).toLocaleString("en-US");
}

function fmtDate(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.toLocaleDateString("en-US", {
    timeZone: "UTC",
    month: "short",
    day: "numeric",
  });
}

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k === "text") node.textContent = v;
    else if (k === "dataset") Object.assign(node.dataset, v);
    else if (k === "style" && typeof v === "object") Object.assign(node.style, v);
    else if (k.startsWith("on") && typeof v === "function")
      node.addEventListener(k.slice(2).toLowerCase(), v);
    else if (v === true) node.setAttribute(k, "");
    else if (v !== false && v !== null && v !== undefined) node.setAttribute(k, v);
  }
  const arr = Array.isArray(children) ? children : [children];
  for (const c of arr) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return node;
}

function clearApp() {
  app.innerHTML = "";
}

function mountTemplate(id) {
  const tpl = document.getElementById(id);
  const frag = tpl.content.cloneNode(true);
  clearApp();
  app.append(frag);
}

function markActiveNav() {
  const hash = location.hash.replace(/^#/, "") || "/";
  document.querySelectorAll(".primary-nav a[data-route-match]").forEach((a) => {
    const rx = new RegExp(a.dataset.routeMatch);
    if (rx.test(hash)) a.classList.add("is-current");
    else a.classList.remove("is-current");
  });
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: "instant" });
  app.focus({ preventScroll: true });
}

// -----------------------------------------------------------------------------
// Boot
// -----------------------------------------------------------------------------
async function boot() {
  try {
    const res = await fetch("data.json");
    if (!res.ok) throw new Error(`Failed to fetch data.json (${res.status})`);
    state.data = await res.json();
    state.teamBySlug = new Map(state.data.rankings.map((r) => [r.team, r]));
    for (const p of state.data.connectivity_pairs) {
      const key = [p.a, p.b].sort().join("|");
      state.pairMap.set(key, p.hops);
    }
    state.maxBethel = Math.max(...state.data.rankings.map((r) => r.bethel));
    state.maxBethelNorm = Math.max(...state.data.rankings.map((r) => r.bethel_norm ?? 0));
    renderMasthead();
    window.addEventListener("hashchange", route);
    route();
  } catch (err) {
    console.error(err);
    app.innerHTML = `<div class="app-loading" role="alert">Couldn't load rankings data. ${err.message}</div>`;
  }
}

function renderMasthead() {
  const m = state.data.meta;
  const dt = new Date(m.generated_at);
  const edition = dt.toISOString().slice(0, 10);
  const meta = document.getElementById("masthead-meta");
  meta.innerHTML = `
    <span>Volume <strong>I</strong></span>
    <span class="sep">·</span>
    <span>Edition ${edition}</span>
    <span class="sep">·</span>
    <span>${fmtInt(m.teams_count)} teams</span>
    <span class="sep">·</span>
    <span>${fmtInt(m.games_count)} games</span>
    <span class="sep">·</span>
    <span>Converged in ${m.convergence_iterations} iterations</span>
  `;
}

// -----------------------------------------------------------------------------
// Router
// -----------------------------------------------------------------------------
function route() {
  const hash = location.hash.replace(/^#/, "") || "/";
  const parts = hash.split("/").filter(Boolean);
  markActiveNav();
  scrollToTop();

  if (window.goatcounter && window.goatcounter.count) {
    window.goatcounter.count({
      path: location.pathname + location.search + location.hash,
    });
  }

  if (parts.length === 0) return renderIndex();
  if (parts[0] === "team" && parts[1]) return renderTeam(decodeURIComponent(parts[1]));
  if (parts[0] === "compare") {
    return renderCompare(
      parts[1] ? decodeURIComponent(parts[1]) : null,
      parts[2] ? decodeURIComponent(parts[2]) : null,
    );
  }
  if (parts[0] === "about") return renderAbout();
  if (parts[0] === "method") return renderMethod();
  renderIndex();
}

// -----------------------------------------------------------------------------
// Index view
// -----------------------------------------------------------------------------
function renderIndex() {
  mountTemplate("tpl-index");

  const tbody = document.getElementById("rankings-tbody");
  const search = document.getElementById("f-search");
  const classSelect = document.getElementById("f-class");
  const normToggle = document.getElementById("f-norm");
  const oosToggle = document.getElementById("f-oos");
  const minGames = document.getElementById("f-min");
  const minGamesVal = document.getElementById("f-min-val");
  const bethelLabel = document.getElementById("th-bethel-label");
  const countEl = document.getElementById("rankings-count");
  const table = document.getElementById("rankings-table");

  search.value = state.filters.search;
  classSelect.value = state.filters.classFilter;
  normToggle.checked = state.filters.normalize;
  oosToggle.checked = state.filters.includeOOS;
  bethelLabel.textContent = state.filters.normalize ? "Bethel·norm" : "Bethel";
  minGames.value = String(state.filters.minGames);
  minGamesVal.textContent = String(state.filters.minGames);

  function paint() {
    const rows = filteredSorted();
    tbody.innerHTML = "";
    if (rows.length === 0) {
      const tr = el("tr");
      tr.append(el("td", { class: "rankings-empty", colspan: 7, text: "No teams match these filters." }));
      tbody.append(tr);
    } else {
      const frag = document.createDocumentFragment();
      rows.forEach((r, i) => frag.append(renderRankingRow(r, i + 1)));
      tbody.append(frag);
    }
    countEl.textContent = `${fmtInt(rows.length)} teams`;
    updateSortIndicator();
  }

  function filteredSorted() {
    let rows = state.data.rankings.filter((r) => {
      if (!state.filters.includeOOS && !r.class) return false;
      if (state.filters.classFilter && r.class !== state.filters.classFilter) return false;
      if (r.games < state.filters.minGames) return false;
      if (state.filters.search) {
        const q = state.filters.search.toLowerCase();
        if (!r.team.toLowerCase().includes(q) && !displayName(r.team).toLowerCase().includes(q)) return false;
      }
      return true;
    });
    const { col, dir } = state.sort;
    const mult = dir === "asc" ? 1 : -1;
    rows = [...rows].sort((a, b) => {
      if (col === "team") {
        return displayName(a.team).localeCompare(displayName(b.team)) * mult;
      }
      return (a[col] - b[col]) * mult;
    });
    return rows;
  }

  function renderRankingRow(r, displayRank) {
    const tr = el("tr", {
      dataset: { team: r.team },
      onClick: () => {
        location.hash = `#/team/${encodeURIComponent(r.team)}`;
      },
    });

    // Rank cell — display position within current filter (1..N), not the
    // global graph-wide rank. Highlight top-1/top-10 by display position.
    const rankCell = el("td", {
      class: `col-rank ${displayRank === 1 ? "top-1" : displayRank <= 10 ? "top-10" : ""}`,
      text: String(displayRank),
    });

    // Team cell
    const teamCell = el("td", { class: "col-team" });
    const teamDisp = el("span", { class: "team-display", text: displayName(r.team) });
    teamCell.append(teamDisp);
    if (r.class) teamCell.append(el("span", { class: `team-badge class-${r.class}`, text: r.class }));

    // Record
    const recCell = el("td", { class: "col-record", text: `${r.wins}–${r.losses}` });

    // Bethel with bar viz — value/scale switch with the normalize toggle
    const bethelCell = el("td", { class: "col-bethel" });
    const useNorm = state.filters.normalize;
    const value = useNorm ? r.bethel_norm : r.bethel;
    const max = useNorm ? state.maxBethelNorm : state.maxBethel;
    bethelCell.append(document.createTextNode(fmtNum(value, 2)));
    const bar = el("span", { class: "strength-bar" });
    const pct = Math.max(2, Math.min(100, (value / max) * 100));
    bar.style.width = `${pct}%`;
    bethelCell.append(bar);

    tr.append(
      rankCell,
      teamCell,
      recCell,
      bethelCell,
      el("td", { class: "col-rpi", text: r.rpi.toFixed(3) }),
      el("td", { class: "col-wp", text: r.wp.toFixed(3) }),
      el("td", { class: "col-owp", text: r.owp.toFixed(3) }),
    );
    return tr;
  }

  function updateSortIndicator() {
    table.querySelectorAll("thead th").forEach((th) => {
      th.classList.remove("is-active", "is-asc");
      if (th.dataset.sort === state.sort.col) {
        th.classList.add("is-active");
        if (state.sort.dir === "asc") th.classList.add("is-asc");
      }
    });
  }

  // Events
  let searchTimer;
  search.addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      paint();
    }, 100);
  });
  classSelect.addEventListener("change", (e) => {
    state.filters.classFilter = e.target.value;
    paint();
  });
  normToggle.addEventListener("change", (e) => {
    state.filters.normalize = e.target.checked;
    bethelLabel.textContent = state.filters.normalize ? "Bethel·norm" : "Bethel";
    paint();
  });
  oosToggle.addEventListener("change", (e) => {
    state.filters.includeOOS = e.target.checked;
    paint();
  });
  minGames.addEventListener("input", (e) => {
    state.filters.minGames = Number(e.target.value);
    minGamesVal.textContent = e.target.value;
    paint();
  });

  table.querySelectorAll("thead th").forEach((th) => {
    th.addEventListener("click", () => {
      const col = th.dataset.sort;
      if (!col) return;
      if (state.sort.col === col) {
        state.sort.dir = state.sort.dir === "desc" ? "asc" : "desc";
      } else {
        state.sort.col = col;
        state.sort.dir = col === "team" ? "asc" : "desc";
      }
      paint();
    });
  });

  paint();
}

// -----------------------------------------------------------------------------
// Team view
// -----------------------------------------------------------------------------
function renderTeam(slug) {
  mountTemplate("tpl-team");

  const team = state.teamBySlug.get(slug);
  if (!team) {
    app.innerHTML = `
      <p class="kicker"><a href="#/">Rankings</a> / Not found</p>
      <h1 class="headline">Team not found</h1>
      <p class="deck">No team in this graph matches the slug <span class="mono">${escapeHtml(slug)}</span>.</p>
    `;
    return;
  }

  const games = state.data.team_games[slug] || [];
  const contribs = state.data.contributions[slug] || null;
  const contribsByIdx = contribs
    ? new Map(contribs.map((c) => [`${c.winner}|${c.loser}|${c.game_index}`, c.delta]))
    : null;

  // FL-only ranks: position among in-state teams (those with a class).
  // Falls back to overall rank for OOS teams.
  const flTeams = state.data.rankings.filter((t) => t.class);
  const flCount = flTeams.length;
  const totalCount = state.data.rankings.length;

  const rpiRankedAll = [...state.data.rankings].sort((a, b) => b.rpi - a.rpi);
  const rpiRankedFL = rpiRankedAll.filter((t) => t.class);
  const rpiRank = team.class
    ? rpiRankedFL.findIndex((t) => t.team === slug) + 1
    : rpiRankedAll.findIndex((t) => t.team === slug) + 1;

  const bethelRank = team.rank_fl ?? team.rank;
  const rankDenominator = team.class ? flCount : totalCount;
  const rankSuffix = team.class ? "FL teams" : "of all teams";

  // Header
  document.getElementById("t-name").textContent = displayName(slug);
  document.getElementById("t-breadcrumb").innerHTML = `<a href="#/">Rankings</a><span aria-hidden="true"> / </span>${escapeHtml(displayName(slug))}`;
  document.getElementById("t-record").innerHTML = `${team.wins}–${team.losses}<span class="sub">·${team.games}g</span>`;
  document.getElementById("t-bethel-rank").innerHTML = `#${bethelRank}<span class="sub">of ${fmtInt(rankDenominator)} ${rankSuffix}</span>`;
  document.getElementById("t-bethel-val").textContent = fmtNum(displayStrength(team), 2);
  document.getElementById("t-rpi-rank").innerHTML = `#${rpiRank}<span class="sub">of ${fmtInt(rankDenominator)} ${rankSuffix}</span>`;
  document.getElementById("t-wp").textContent = team.wp.toFixed(3);
  document.getElementById("t-owp").textContent = team.owp.toFixed(3);

  // Season strip
  const strip = document.getElementById("t-strip");
  strip.innerHTML = "";
  games.forEach((g, i) => {
    const contribDelta = contribs
      ? findContributionDelta(contribs, slug, g, i, games)
      : null;
    const pip = el("span", {
      class: `pip ${g.result === "W" ? "w" : "l"}`,
      dataset: { gameType: g.game_type },
      title: `${fmtDate(g.date)} ${g.result} ${g.team_score}-${g.opp_score} ${g.home ? "vs" : "@"} ${displayName(g.opponent)}${contribDelta != null ? ` (Δ ${contribDelta >= 0 ? "+" : ""}${contribDelta.toFixed(3)})` : ""}`,
    });
    strip.append(pip);
  });

  // Intro line
  const intro = buildIntroLine(team, rpiRank, games, contribs);
  document.getElementById("t-intro").textContent = intro;

  // Best / worst
  const bestWinsEl = document.getElementById("t-best-wins");
  const worstLossesEl = document.getElementById("t-worst-losses");
  if (!contribs) {
    const msg = el("li", {
      class: "extreme-empty",
      text: "Per-game contributions have not yet been computed for this team.",
    });
    bestWinsEl.append(msg);
    const msg2 = el("li", {
      class: "extreme-empty",
      text: "Per-game contributions have not yet been computed for this team.",
    });
    worstLossesEl.append(msg2);
  } else {
    const wins = contribs
      .filter((c) => c.winner === slug)
      .slice()
      .sort((a, b) => b.delta - a.delta)
      .slice(0, 5);
    const losses = contribs
      .filter((c) => c.loser === slug)
      .slice()
      .sort((a, b) => a.delta - b.delta)
      .slice(0, 5);
    wins.forEach((c) => bestWinsEl.append(renderExtremeItem(c, slug, "pos")));
    losses.forEach((c) => worstLossesEl.append(renderExtremeItem(c, slug, "neg")));
    if (wins.length === 0) bestWinsEl.append(el("li", { class: "extreme-empty", text: "No wins recorded." }));
    if (losses.length === 0) worstLossesEl.append(el("li", { class: "extreme-empty", text: "No losses recorded." }));
  }

  // Schedule body
  const tbody = document.getElementById("t-schedule-body");
  const scheduleNote = document.getElementById("t-schedule-note");
  const absoluteMaxDelta = contribs
    ? Math.max(...contribs.map((c) => Math.abs(c.delta)))
    : 0;

  games.forEach((g, i) => {
    const tr = renderScheduleRow(g, i, slug, games, contribs, contribsByIdx, absoluteMaxDelta);
    tbody.append(tr);
  });

  if (!contribs) {
    scheduleNote.textContent =
      "Per-game contributions are precomputed for a curated subset of teams (FHSAA Class 2A and the top ~20 by strength). This team is not currently in that subset — the rankings are correct, but the per-game impact numbers haven't been computed yet.";
  } else {
    scheduleNote.textContent =
      "Impact is the change in this team's Bethel strength from including each game, computed by leaving one game out at a time and re-solving the ranking. A win against a strong opponent contributes more than a win against a weak one.";
  }
}

function renderExtremeItem(c, slug, kind) {
  const opp = c.winner === slug ? c.loser : c.winner;
  const oppTeam = state.teamBySlug.get(opp);
  const li = el("li");
  const left = el("a", { class: "extreme-opp", href: `#/team/${encodeURIComponent(opp)}` });
  left.append(document.createTextNode(displayName(opp)));
  if (oppTeam) {
    const small = el("small", {
      text: `#${oppTeam.rank_fl ?? oppTeam.rank} · Bethel ${fmtNum(displayStrength(oppTeam), 2)}`,
    });
    left.append(small);
  }
  const right = el("span", {
    class: `extreme-delta ${kind}`,
    text: `${c.delta >= 0 ? "+" : ""}${c.delta.toFixed(3)}`,
  });
  li.append(left, right);
  return li;
}

function renderScheduleRow(g, gameIndex, slug, games, contribs, contribsByIdx, absoluteMaxDelta) {
  const delta = contribs
    ? findContributionDelta(contribs, slug, g, gameIndex, games)
    : null;

  const tr = el("tr", {
    class: `game-${g.result === "W" ? "w" : "l"} ${g.game_type !== "regular" ? "game-tournament" : ""}`,
  });

  tr.append(el("td", { class: "col-sched-date", text: fmtDate(g.date) }));
  tr.append(el("td", { class: "col-sched-loc", text: g.home ? "vs" : "@" }));

  const oppTd = el("td", { class: "col-sched-opp" });
  const oppLink = el("a", {
    href: `#/team/${encodeURIComponent(g.opponent)}`,
    text: displayName(g.opponent),
  });
  oppTd.append(oppLink);
  if (g.game_type !== "regular") {
    const tag = el("span", {
      class: "team-badge",
      text: g.game_type === "district-tournament" ? "DIST" : "REG",
    });
    tag.style.background = "var(--accent-wash)";
    oppTd.append(tag);
  }
  tr.append(oppTd);

  const oppTeam = state.teamBySlug.get(g.opponent);
  tr.append(
    el("td", {
      class: "col-sched-opp-str",
      text: oppTeam ? fmtNum(displayStrength(oppTeam), 2) : "—",
    }),
  );

  const resTd = el("td", { class: "col-sched-res" });
  resTd.innerHTML = `<span class="outcome ${g.result === "W" ? "w" : "l"}">${g.result}</span> ${g.team_score}–${g.opp_score}`;
  tr.append(resTd);

  // Delta cell
  const dtTd = el("td", { class: "col-sched-delta" });
  if (delta == null) {
    const nc = el("div", { class: "delta-cell nc" });
    nc.append(el("span", { class: "delta-num", text: "n/c" }));
    dtTd.append(nc);
  } else {
    const cls = delta >= 0 ? "pos" : "neg";
    const cell = el("div", { class: `delta-cell ${cls}` });
    const numText = `${delta >= 0 ? "+" : ""}${delta.toFixed(3)}`;
    cell.append(el("span", { class: `delta-num ${cls}`, text: numText }));
    const bar = el("span", { class: "delta-bar" });
    const pct = absoluteMaxDelta > 0 ? (Math.abs(delta) / absoluteMaxDelta) * 50 : 0;
    bar.style.setProperty("--bar-w", `${pct.toFixed(1)}%`);
    cell.append(bar);
    dtTd.append(cell);
  }
  tr.append(dtTd);

  return tr;
}

function findContributionDelta(contribs, slug, game, gameIdx, games) {
  // Contributions are keyed by (winner, loser, game_index). The game_index is
  // the global game index in the original game list used by the engine, not
  // the per-team index here, so we have to find by (winner, loser) pair +
  // date-occurrence since some teams played twice.
  const winner = game.result === "W" ? slug : game.opponent;
  const loser = game.result === "W" ? game.opponent : slug;
  // Count how many prior games also had the same winner/loser pair.
  let occurrence = 0;
  for (let i = 0; i < gameIdx; i++) {
    const prev = games[i];
    const pw = prev.result === "W" ? slug : prev.opponent;
    const pl = prev.result === "W" ? prev.opponent : slug;
    if (pw === winner && pl === loser) occurrence++;
  }
  // Now find the nth matching contribution.
  const matches = contribs.filter((c) => c.winner === winner && c.loser === loser);
  if (matches.length === 0) return null;
  return matches[Math.min(occurrence, matches.length - 1)].delta;
}

function buildIntroLine(team, rpiRank, games, contribs) {
  const wins = games.filter((g) => g.result === "W").length;
  const losses = games.filter((g) => g.result === "L").length;
  const tournGames = games.filter((g) => g.game_type !== "regular").length;
  const flCount = state.data.rankings.filter((t) => t.class).length;
  const denom = team.class ? flCount : state.data.rankings.length;
  const suffix = team.class ? "FL teams" : "teams";
  const bethelRank = team.rank_fl ?? team.rank;
  const parts = [];
  parts.push(`Ranked #${bethelRank} of ${fmtInt(denom)} ${suffix} by Bethel; #${rpiRank} by RPI.`);
  parts.push(`${wins}-${losses} across ${games.length} games${tournGames > 0 ? `, ${tournGames} in postseason play` : ""}.`);
  if (contribs && contribs.length > 0) {
    const net = contribs.reduce((a, c) => a + c.delta, 0);
    parts.push(`Net per-game contribution: ${net >= 0 ? "+" : ""}${net.toFixed(2)}.`);
  }
  return parts.join(" ");
}

// -----------------------------------------------------------------------------
// Compare view
// -----------------------------------------------------------------------------
function renderCompare(slugA, slugB) {
  mountTemplate("tpl-compare");

  if (slugA) state.compare.a = slugA;
  if (slugB) state.compare.b = slugB;

  const pickA = document.getElementById("pick-a");
  const pickB = document.getElementById("pick-b");
  const resA = document.getElementById("pick-a-results");
  const resB = document.getElementById("pick-b-results");
  const body = document.getElementById("compare-body");

  if (state.compare.a) pickA.value = displayName(state.compare.a);
  if (state.compare.b) pickB.value = displayName(state.compare.b);

  const wire = (input, resultsEl, side) => {
    let activeIdx = -1;
    let results = [];

    const close = () => {
      resultsEl.classList.remove("is-open");
      resultsEl.innerHTML = "";
      activeIdx = -1;
    };

    const pickCurrent = () => {
      if (activeIdx >= 0 && activeIdx < results.length) {
        const r = results[activeIdx];
        input.value = displayName(r.team);
        state.compare[side] = r.team;
        close();
        updateCompareUrl();
        drawCompareBody();
      }
    };

    const show = (q) => {
      if (!q || q.length < 1) {
        close();
        return;
      }
      const lower = q.toLowerCase();
      results = state.data.rankings
        .filter(
          (r) =>
            r.team.toLowerCase().includes(lower) ||
            displayName(r.team).toLowerCase().includes(lower),
        )
        .slice(0, 10);
      if (results.length === 0) {
        close();
        return;
      }
      resultsEl.innerHTML = "";
      results.forEach((r, i) => {
        const resEl = el("div", {
          class: `result ${i === 0 ? "is-active" : ""}`,
          role: "option",
          dataset: { team: r.team, idx: String(i) },
          onMouseenter: () => {
            activeIdx = i;
            resultsEl.querySelectorAll(".result").forEach((rr, j) =>
              rr.classList.toggle("is-active", j === i),
            );
          },
          onMousedown: (e) => {
            e.preventDefault();
            activeIdx = i;
            pickCurrent();
          },
        });
        resEl.append(
          el("span", { class: "result-name", text: displayName(r.team) }),
          el("span", { class: "result-meta", text: `#${r.rank_fl ?? r.rank} · ${r.wins}-${r.losses}` }),
        );
        resultsEl.append(resEl);
      });
      activeIdx = 0;
      resultsEl.classList.add("is-open");
    };

    input.addEventListener("input", (e) => show(e.target.value.trim()));
    input.addEventListener("focus", () => {
      if (input.value.trim()) show(input.value.trim());
    });
    input.addEventListener("blur", () => {
      setTimeout(close, 150);
    });
    input.addEventListener("keydown", (e) => {
      if (!resultsEl.classList.contains("is-open")) {
        if (e.key === "ArrowDown") show(input.value.trim());
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        activeIdx = Math.min(results.length - 1, activeIdx + 1);
        resultsEl.querySelectorAll(".result").forEach((rr, j) =>
          rr.classList.toggle("is-active", j === activeIdx),
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeIdx = Math.max(0, activeIdx - 1);
        resultsEl.querySelectorAll(".result").forEach((rr, j) =>
          rr.classList.toggle("is-active", j === activeIdx),
        );
      } else if (e.key === "Enter") {
        e.preventDefault();
        pickCurrent();
      } else if (e.key === "Escape") {
        close();
      }
    });
  };

  wire(pickA, resA, "a");
  wire(pickB, resB, "b");

  drawCompareBody();
}

function updateCompareUrl() {
  const { a, b } = state.compare;
  let hash = "#/compare";
  if (a) hash += `/${encodeURIComponent(a)}`;
  if (a && b) hash += `/${encodeURIComponent(b)}`;
  history.replaceState(null, "", hash);
  markActiveNav();
}

function drawCompareBody() {
  const body = document.getElementById("compare-body");
  body.innerHTML = "";
  const { a, b } = state.compare;
  if (!a || !b) {
    body.append(
      el("div", {
        class: "compare-empty",
        text: a || b ? "Pick a second team to see the comparison." : "Pick two teams to begin.",
      }),
    );
    return;
  }
  if (a === b) {
    body.append(el("div", { class: "compare-empty", text: "You've selected the same team twice." }));
    return;
  }

  const tA = state.teamBySlug.get(a);
  const tB = state.teamBySlug.get(b);
  if (!tA || !tB) {
    body.append(el("div", { class: "compare-empty", text: "One of those teams isn't in the dataset." }));
    return;
  }

  // Bethel win probability
  const pA = tA.bethel / (tA.bethel + tB.bethel);
  const pB = 1 - pA;

  const grid = el("div", { class: "compare-grid" });

  // Summary
  const summary = el("div", { class: "compare-summary" });
  summary.append(renderCompareTeamBlock(tA, "Team A"));
  const probBlock = el("div", { class: "compare-prob" });
  probBlock.append(el("p", { class: "compare-prob-label", text: "Bethel-implied win probability" }));
  const bar = el("div", { class: "prob-bar", role: "img", "aria-label": `${Math.round(pA * 100)}% A vs ${Math.round(pB * 100)}% B` });
  const barA = el("div", { class: "prob-a", text: `${Math.round(pA * 100)}%` });
  barA.style.flex = `${pA}`;
  const barB = el("div", { class: "prob-b", text: `${Math.round(pB * 100)}%` });
  barB.style.flex = `${pB}`;
  bar.append(barA, barB);
  probBlock.append(bar);
  probBlock.append(el("p", { class: "compare-prob-note", text: "Neutral site. No home-field adjustment." }));
  summary.append(probBlock);
  summary.append(renderCompareTeamBlock(tB, "Team B"));
  grid.append(summary);

  // Connection path
  const directGames = findHeadToHead(a, b);
  grid.append(renderConnectionSection(a, b, directGames));

  // Head-to-head
  if (directGames.length > 0) grid.append(renderHeadToHeadSection(a, b, directGames));

  // Shared opponents
  grid.append(renderSharedOpponentsSection(a, b));

  body.append(grid);
}

function renderCompareTeamBlock(team, label) {
  const block = el("div", { class: "compare-team" });
  block.append(
    el("p", { class: "cteam-label", text: label }),
    el("h2", { class: "cteam-name" }, [
      el("a", {
        href: `#/team/${encodeURIComponent(team.team)}`,
        text: displayName(team.team),
        style: { color: "inherit", textDecoration: "none" },
      }),
    ]),
    el("p", { class: "cteam-meta", text: `#${team.rank_fl ?? team.rank} · ${team.wins}–${team.losses} · Win% ${team.wp.toFixed(3)}` }),
    el("p", { class: "cteam-strength", text: fmtNum(displayStrength(team), 3) }),
  );
  return block;
}

function renderConnectionSection(a, b, direct) {
  const section = el("section", { class: "compare-section" });
  section.append(el("h3", { text: "Graph connection" }));

  const hops = getHops(a, b, direct);

  if (direct.length > 0) {
    const path = el("div", { class: "connection-path direct" });
    path.append(
      el("span", { class: "node", text: displayName(a) }),
      el("span", { class: "edge", text: `played ${direct.length} time${direct.length > 1 ? "s" : ""} →` }),
      el("span", { class: "node", text: displayName(b) }),
    );
    section.append(path);
    section.append(
      el("p", {
        class: "schedule-note",
        text: "Direct games exist. The comparison is grounded in head-to-head results, not graph inference.",
      }),
    );
  } else if (hops === null) {
    const path = el("div", { class: "connection-path disconnected" });
    path.append(el("span", { text: "No chain of opponents connects these two teams in the graph — the comparison is not defined by the data." }));
    section.append(path);
  } else {
    const path = el("div", { class: "connection-path" });
    path.append(el("span", { class: "node", text: displayName(a) }));
    for (let i = 0; i < hops + 1; i++) {
      path.append(el("span", { class: "edge", text: "→ common opponent →" }));
      if (i < hops) path.append(el("span", { class: "node", text: "⋯" }));
    }
    path.append(el("span", { class: "node", text: displayName(b) }));
    section.append(path);
    section.append(
      el("p", {
        class: "schedule-note",
        text: `The two teams never played directly. Their comparison is grounded indirectly, through ${hops === 0 ? "a common opponent" : `a chain of ${hops + 1} shared opponents`}.`,
      }),
    );
  }
  return section;
}

function findHeadToHead(a, b) {
  const gamesA = state.data.team_games[a] || [];
  return gamesA
    .filter((g) => g.opponent === b)
    .map((g) => ({ ...g, from: a }));
}

function getHops(a, b, directGames) {
  if (directGames.length > 0) return 0;
  const key = [a, b].sort().join("|");
  if (state.pairMap.has(key)) return state.pairMap.get(key);
  // Compute client-side BFS
  const adj = new Map();
  for (const [team, games] of Object.entries(state.data.team_games)) {
    const set = new Set();
    for (const g of games) set.add(g.opponent);
    adj.set(team, set);
  }
  if (!adj.has(a) || !adj.has(b)) return null;
  if (adj.get(a).has(b)) return 0;
  const visited = new Set([a]);
  let frontier = [[a, 0]];
  while (frontier.length) {
    const [node, depth] = frontier.shift();
    for (const nxt of adj.get(node) || []) {
      if (nxt === b) return depth;
      if (!visited.has(nxt)) {
        visited.add(nxt);
        frontier.push([nxt, depth + 1]);
      }
    }
  }
  return null;
}

function renderHeadToHeadSection(a, b, games) {
  const section = el("section", { class: "compare-section" });
  section.append(el("h3", { text: "Head-to-head games" }));
  const list = el("ul", { class: "head-to-head-list" });
  const aWins = games.filter((g) => g.result === "W").length;
  const bWins = games.filter((g) => g.result === "L").length;
  let summary = "";
  if (aWins > 0 && bWins === 0) summary = `${displayName(a)} ${aWins}–0`;
  else if (bWins > 0 && aWins === 0) summary = `${displayName(b)} ${bWins}–0`;
  else summary = `Split ${aWins}-${bWins}`;
  section.append(
    el("p", {
      class: "compare-prob-note",
      style: { marginBottom: "var(--space-2)" },
      text: summary + ` across ${games.length} game${games.length > 1 ? "s" : ""}.`,
    }),
  );
  for (const g of games) {
    const winner = g.result === "W" ? a : b;
    const li = el("li");
    li.append(
      el("span", { class: "date", text: fmtDate(g.date) }),
      el("span", { text: `${displayName(a)} ${g.team_score} · ${g.opp_score} ${displayName(b)}` }),
      el("span", {
        class: `result-chip ${winner === a ? "a" : "b"}`,
        text: `${displayName(winner).split(" ")[0]} won`,
      }),
    );
    list.append(li);
  }
  section.append(list);
  return section;
}

function renderSharedOpponentsSection(a, b) {
  const section = el("section", { class: "compare-section" });
  section.append(el("h3", { text: "Common opponents" }));

  const gamesA = state.data.team_games[a] || [];
  const gamesB = state.data.team_games[b] || [];
  const oppsA = new Map(); // slug → { wins, losses }
  const oppsB = new Map();
  for (const g of gamesA) {
    if (g.opponent === b) continue;
    const rec = oppsA.get(g.opponent) || { w: 0, l: 0 };
    if (g.result === "W") rec.w++;
    else rec.l++;
    oppsA.set(g.opponent, rec);
  }
  for (const g of gamesB) {
    if (g.opponent === a) continue;
    const rec = oppsB.get(g.opponent) || { w: 0, l: 0 };
    if (g.result === "W") rec.w++;
    else rec.l++;
    oppsB.set(g.opponent, rec);
  }

  const shared = [...oppsA.keys()].filter((k) => oppsB.has(k));
  shared.sort((x, y) => {
    const bx = state.teamBySlug.get(x)?.bethel ?? 0;
    const by = state.teamBySlug.get(y)?.bethel ?? 0;
    return by - bx;
  });

  if (shared.length === 0) {
    section.append(
      el("p", { class: "compare-prob-note", text: "No common opponents appear in the dataset." }),
    );
    return section;
  }

  const list = el("ul", { class: "shared-opponents" });
  for (const opp of shared) {
    const oppTeam = state.teamBySlug.get(opp);
    const rA = oppsA.get(opp);
    const rB = oppsB.get(opp);
    let chipClass = "split";
    if (rA.w > 0 && rA.l === 0 && rB.l > 0 && rB.w === 0) chipClass = "a";
    else if (rB.w > 0 && rB.l === 0 && rA.l > 0 && rA.w === 0) chipClass = "b";

    const chipText = `${rA.w}-${rA.l} / ${rB.w}-${rB.l}`;
    const li = el("li");
    li.append(
      el("span", {
        class: "label",
        text: oppTeam ? `Bethel ${fmtNum(oppTeam.bethel, 2)}` : "",
      }),
      el("a", {
        href: `#/team/${encodeURIComponent(opp)}`,
        style: { color: "var(--ink)" },
        text: displayName(opp),
      }),
      el("span", { class: `result-chip ${chipClass}`, text: chipText }),
    );
    list.append(li);
  }
  section.append(list);
  section.append(
    el("p", {
      class: "compare-prob-note",
      style: { marginTop: "var(--space-3)" },
      text: `Format: ${displayName(a).split(" ")[0]}'s record vs each opponent, then ${displayName(b).split(" ")[0]}'s record.`,
    }),
  );
  return section;
}

// -----------------------------------------------------------------------------
// About / Method
// -----------------------------------------------------------------------------
function renderAbout() {
  mountTemplate("tpl-about");
  const countsEl = document.getElementById("about-counts");
  const m = state.data.meta;
  const dt = new Date(m.generated_at);
  const dateFmt = dt.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  countsEl.textContent = `This edition covers ${fmtInt(m.games_count)} games across ${fmtInt(m.teams_count)} Florida high school baseball teams from the 2026 season. Per-game contribution numbers are computed for ${m.contributions_computed_for.length} teams — FHSAA Class 2A plus the top of the state rankings. Ranking strengths converged in ${m.convergence_iterations} iterations. Generated ${dateFmt}.`;
}

function renderMethod() {
  mountTemplate("tpl-method");
}

// -----------------------------------------------------------------------------
// HTML-escape
// -----------------------------------------------------------------------------
function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// -----------------------------------------------------------------------------
// Go
// -----------------------------------------------------------------------------
boot();
