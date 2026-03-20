// ====================================================================
// AI DISPATCHER — FULL INTERACTIVE MPC SIMULATOR ENGINE
// Ports the Python optimizer to JavaScript for in-browser computation
// ====================================================================

// Chart instances (global for destruction/recreation)
let charts = {};

function getVal(id) {
  const el = document.getElementById(id);
  return el ? parseFloat(el.value) : 0;
}

function getParams() {
  return {
    deficit: getVal('p_deficit'),
    beta: getVal('p_beta'),
    duration: getVal('p_duration'),
    reoptInterval: getVal('p_reopt') / 60, // convert min to hours

    dguFuel: getVal('p_dgu_fuel'),
    co2Rate: getVal('p_co2_rate'),
    esgPenalty: getVal('p_esg_penalty'),
    dguRampMin: getVal('p_dgu_ramp'),
    dguMinLoad: getVal('p_dgu_min'),

    hvacMax: getVal('p_hvac_max'),
    hvacCost: getVal('p_hvac_cost'),
    pumpMax: getVal('p_pump_max'),
    pumpCost: getVal('p_pump_cost'),
    millMax: getVal('p_mill_max'),
    millCost: getVal('p_mill_cost'),

    tSetpoint: getVal('p_t_setpoint'),
    tAmbient: getVal('p_t_ambient'),
    tau: getVal('p_tau') / 60, // min to hours
    tWarn: getVal('p_t_warn'),
    tCritical: getVal('p_t_critical'),
    warnPenalty: getVal('p_warn_penalty'),
    severePenalty: getVal('p_severe_penalty'),

    pumpBuffer: getVal('p_pump_buffer'),
    pumpEscalation: getVal('p_pump_escalation'),
    millScrap: getVal('p_mill_scrap'),
  };
}

// Update display labels for all sliders
function updateLabel(id) {
  const el = document.getElementById(id);
  const label = document.getElementById(id + '_val');
  if (el && label) label.textContent = el.value;
}

function initLabels() {
  document.querySelectorAll('.sim-slider').forEach(s => {
    s.addEventListener('input', () => { updateLabel(s.id); runSimulation(); });
  });
  document.querySelectorAll('.sim-input').forEach(s => {
    s.addEventListener('input', () => { runSimulation(); });
  });
}

// ==== TEMPERATURE MODEL ====
function computeTemperature(tRoom, xHvac, hvacMax, tAmb, tSet, tau, dt) {
  if (xHvac <= 0) {
    // HVAC fully running — recover toward setpoint
    let t = tAmb + (tRoom - tAmb) * Math.exp(-dt / (tau * 0.3));
    return Math.max(tSet, Math.min(t, tAmb > tSet ? t : tSet));
  }
  const frac = Math.min(xHvac / hvacMax, 1);
  const tauEff = tau / Math.max(frac, 0.01);
  const tEq = tSet + (tAmb - tSet) * frac;
  return tEq + (tRoom - tEq) * Math.exp(-dt / tauEff);
}

function getHvacPenalty(tRoom, P) {
  const isHot = P.tAmbient > P.tSetpoint;
  const dev = isHot ? tRoom - P.tSetpoint : P.tSetpoint - tRoom;
  const warnDelta = Math.abs(P.tWarn - P.tSetpoint);
  const critDelta = Math.abs(P.tCritical - P.tSetpoint);
  if (dev <= warnDelta) return 0;
  if (dev <= critDelta) return P.warnPenalty * (dev - warnDelta) / (critDelta - warnDelta);
  return P.warnPenalty + P.severePenalty;
}

function getPumpEscalation(cumPumpHrs, P) {
  const bufferHrs = P.pumpBuffer / 60;
  if (cumPumpHrs < bufferHrs) return -Math.min(2000, P.pumpCost * 0.4);
  if (cumPumpHrs < 1) return 0;
  if (cumPumpHrs < 2) return P.pumpEscalation * (cumPumpHrs - 1);
  return P.pumpEscalation + 7000;
}

// ==== SINGLE-PERIOD OPTIMIZER ====
function optimizePeriod(P, tRoom, cumPumpHrs, dt) {
  const step = 5;
  const carbonPerMW = P.co2Rate * P.esgPenalty;
  let best = null, bestCost = Infinity;

  for (let dgu = 0; dgu <= P.deficit + 10; dgu += step) {
    for (let hvac = 0; hvac <= Math.min(P.hvacMax, P.deficit + 10 - dgu); hvac += step) {
      for (let pump = 0; pump <= Math.min(P.pumpMax, P.deficit + 10 - dgu - hvac); pump += step) {
        let millNeed = Math.max(0, P.deficit - dgu - hvac - pump);
        let mill = Math.ceil(millNeed / step) * step;
        if (mill > P.millMax) continue;
        if (dgu + hvac + pump + mill < P.deficit - 0.1) continue;

        // Simulate temperature
        let tNew = computeTemperature(tRoom, hvac, P.hvacMax, P.tAmbient, P.tSetpoint, P.tau, dt);
        let tAvg = (tRoom + tNew) / 2;
        let penalty = getHvacPenalty(tAvg, P);
        let pumpEsc = pump > 0 ? getPumpEscalation(cumPumpHrs, P) : 0;
        const hvacFrac = P.hvacMax > 0 ? hvac / P.hvacMax : 0;
        const pumpFrac = P.pumpMax > 0 ? pump / P.pumpMax : 0;
        const millFrac = P.millMax > 0 ? mill / P.millMax : 0;

        let rate = P.dguFuel * dgu
          + P.beta * carbonPerMW * dgu
          + (P.hvacCost + penalty) * hvacFrac
          + (P.pumpCost + pumpEsc) * pumpFrac
          + P.millCost * millFrac;

        let cost = rate * dt;
        if (cost < bestCost) {
          bestCost = cost;
          best = { dgu, hvac, pump, mill, cost, rate, tNew, penalty, pumpEsc };
        }
      }
    }
  }
  return best;
}

// ==== FULL MPC SIMULATION ====
function runMPC(P) {
  const rampHrs = P.dguRampMin / 60;
  const carbonPerMW = P.co2Rate * P.esgPenalty;
  const dt = P.reoptInterval;

  // Phase 1: DGU ramp
  const dguAvg = P.deficit / 2; // average during ramp (0 to ~deficit)
  const p1Cost = (P.dguFuel * dguAvg + P.beta * carbonPerMW * dguAvg
    + P.hvacCost + P.pumpCost + P.millCost) * rampHrs;
  const p1CO2 = P.co2Rate * dguAvg * rampHrs;

  let tRoom = P.tSetpoint;
  tRoom = computeTemperature(tRoom, P.hvacMax, P.hvacMax, P.tAmbient, P.tSetpoint, P.tau, rampHrs);

  let totalCost = p1Cost, totalCO2 = p1CO2;
  let cumPump = rampHrs, cumHvac = rampHrs, cumMill = rampHrs, cumDgu = rampHrs;
  let elapsed = rampHrs;

  const timeline = [{
    time: 0, dgu: 'Ramp', hvac: P.hvacMax, pump: P.pumpMax, mill: P.millMax,
    tRoom: tRoom, cost: p1Cost, cumCost: totalCost, co2: totalCO2,
    penalty: 0, pumpEsc: 0, label: 'Phase 1: All Shed'
  }];

  // Phase 2+: MPC loop
  const periods = Math.floor((P.duration - rampHrs) / dt);
  for (let i = 0; i < periods; i++) {
    const result = optimizePeriod(P, tRoom, cumPump, dt);
    if (!result) break;

    tRoom = result.tNew;
    elapsed += dt;
    totalCost += result.cost;
    totalCO2 += P.co2Rate * result.dgu * dt;
    cumDgu += dt;
    if (result.hvac > 0) cumHvac += dt;
    if (result.pump > 0) cumPump += dt;
    if (result.mill > 0) cumMill += dt;

    timeline.push({
      time: elapsed - dt, dgu: result.dgu, hvac: result.hvac,
      pump: result.pump, mill: result.mill, tRoom: tRoom,
      cost: result.cost, cumCost: totalCost, co2: totalCO2,
      penalty: result.penalty, pumpEsc: result.pumpEsc,
      label: result.penalty > 0 ? 'Temp Warning' : (result.pumpEsc > 0 ? 'Pump Stressed' : 'Normal')
    });
  }

  return { timeline, totalCost, totalCO2, peakTemp: Math.max(...timeline.map(t => t.tRoom)),
    cumDgu, cumHvac, cumPump, cumMill, p1Cost };
}

// ==== BETA SWEEP (for Pareto + β sensitivity) ====
function betaSweep(P) {
  const betas = [];
  const results = [];
  for (let b = 0.2; b <= 5.0; b += 0.2) {
    const pp = { ...P, beta: b, duration: Math.min(P.duration, 1) }; // 1hr snapshot for Pareto
    const carbonPerMW = pp.co2Rate * pp.esgPenalty;
    // Quick single-period optimization
    const step = 5;
    let best = null, bestCost = Infinity;
    for (let dgu = 0; dgu <= pp.deficit + 10; dgu += step) {
      for (let hvac = 0; hvac <= Math.min(pp.hvacMax, pp.deficit + 10 - dgu); hvac += step) {
        for (let pump = 0; pump <= Math.min(pp.pumpMax, pp.deficit + 10 - dgu - hvac); pump += step) {
          let mill = Math.ceil(Math.max(0, pp.deficit - dgu - hvac - pump) / step) * step;
          if (mill > pp.millMax || dgu + hvac + pump + mill < pp.deficit - 0.1) continue;
          const hvacFrac = pp.hvacMax > 0 ? hvac / pp.hvacMax : 0;
          const pumpFrac = pp.pumpMax > 0 ? pump / pp.pumpMax : 0;
          const millFrac = pp.millMax > 0 ? mill / pp.millMax : 0;
          let rate = pp.dguFuel * dgu + b * carbonPerMW * dgu
            + pp.hvacCost * hvacFrac + pp.pumpCost * pumpFrac + pp.millCost * millFrac;
          let co2 = pp.co2Rate * dgu;
          if (rate < bestCost) { bestCost = rate; best = { dgu, hvac, pump, mill, rate, co2, beta: b }; }
        }
      }
    }
    if (best) { betas.push(b); results.push(best); }
  }
  return { betas, results };
}

// ==== RENDER ALL CHARTS ====
function renderCharts(mpc, sweep, P) {
  const cc = (id) => document.getElementById(id)?.getContext('2d');

  // Destroy existing charts
  Object.values(charts).forEach(c => c?.destroy?.());
  charts = {};

  // 1. DISPATCH TIMELINE (stacked area)
  const timeLabels = mpc.timeline.map(t => typeof t.dgu === 'string' ? '0:00-0:05' : `${Math.floor(t.time)}:${String(Math.round((t.time % 1) * 60)).padStart(2, '0')}`);
  const ctx1 = cc('chart_dispatch');
  if (ctx1) {
    charts.dispatch = new Chart(ctx1, {
      type: 'bar', data: {
        labels: timeLabels,
        datasets: [
          { label: 'DGU (MW)', data: mpc.timeline.map(t => typeof t.dgu === 'string' ? P.deficit / 2 : t.dgu), backgroundColor: '#ef4444', stack: 'a' },
          { label: 'HVAC Shed', data: mpc.timeline.map(t => t.hvac), backgroundColor: '#06b6d4', stack: 'a' },
          { label: 'Pump Shed', data: mpc.timeline.map(t => t.pump), backgroundColor: '#f59e0b', stack: 'a' },
          { label: 'Mill Shed', data: mpc.timeline.map(t => t.mill), backgroundColor: '#8b5cf6', stack: 'a' },
        ]
      },
      options: { responsive: true, plugins: { title: { display: true, text: 'Power Dispatch Over Time (MW)', color: '#e2e8f0' }, legend: { labels: { color: '#94a3b8' } } },
        scales: { x: { ticks: { color: '#94a3b8', maxRotation: 45 }, grid: { color: '#1a2332' } }, y: { ticks: { color: '#94a3b8' }, grid: { color: '#1a2332' }, title: { display: true, text: 'MW', color: '#94a3b8' } } } }
    });
  }

  // 2. TEMPERATURE DRIFT
  const ctx2 = cc('chart_temp');
  if (ctx2) {
    charts.temp = new Chart(ctx2, {
      type: 'line', data: {
        labels: timeLabels,
        datasets: [
          { label: 'Room Temp (°C)', data: mpc.timeline.map(t => t.tRoom.toFixed(1)), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.1)', fill: true, tension: 0.3 },
          { label: 'Warning', data: mpc.timeline.map(() => P.tAmbient > P.tSetpoint ? P.tWarn : P.tSetpoint - (P.tWarn - P.tSetpoint)), borderColor: '#f59e0b', borderDash: [5, 5], pointRadius: 0 },
          { label: 'Critical', data: mpc.timeline.map(() => P.tAmbient > P.tSetpoint ? P.tCritical : P.tSetpoint - (P.tCritical - P.tSetpoint)), borderColor: '#ef4444', borderDash: [5, 5], pointRadius: 0 },
        ]
      },
      options: { responsive: true, plugins: { title: { display: true, text: 'Temperature Drift & Penalty Zones', color: '#e2e8f0' }, legend: { labels: { color: '#94a3b8' } } },
        scales: { x: { ticks: { color: '#94a3b8', maxRotation: 45 }, grid: { color: '#1a2332' } }, y: { ticks: { color: '#94a3b8' }, grid: { color: '#1a2332' }, title: { display: true, text: '°C', color: '#94a3b8' } } } }
    });
  }

  // 3. COST WATERFALL (per period)
  const ctx3 = cc('chart_waterfall');
  if (ctx3) {
    const carbonPerMW = P.co2Rate * P.esgPenalty;
    const wfData = mpc.timeline.map(t => {
      const d = typeof t.dgu === 'string' ? P.deficit / 2 : t.dgu;
      const dt2 = t.time === 0 ? P.dguRampMin / 60 : P.reoptInterval;
      return {
        fuel: P.dguFuel * d * dt2,
        co2: P.beta * carbonPerMW * d * dt2,
        hvac: P.hvacCost * (t.hvac / Math.max(P.hvacMax, 1)) * dt2,
        pump: P.pumpCost * (t.pump / Math.max(P.pumpMax, 1)) * dt2,
        mill: P.millCost * (t.mill / Math.max(P.millMax, 1)) * dt2,
      };
    });
    charts.waterfall = new Chart(ctx3, {
      type: 'bar', data: {
        labels: timeLabels,
        datasets: [
          { label: 'DGU Fuel', data: wfData.map(w => w.fuel.toFixed(0)), backgroundColor: '#ef4444', stack: 'a' },
          { label: 'CO₂ Penalty', data: wfData.map(w => w.co2.toFixed(0)), backgroundColor: '#f97316', stack: 'a' },
          { label: 'HVAC', data: wfData.map(w => w.hvac.toFixed(0)), backgroundColor: '#06b6d4', stack: 'a' },
          { label: 'Pump', data: wfData.map(w => w.pump.toFixed(0)), backgroundColor: '#f59e0b', stack: 'a' },
          { label: 'Mill', data: wfData.map(w => w.mill.toFixed(0)), backgroundColor: '#8b5cf6', stack: 'a' },
        ]
      },
      options: { responsive: true, plugins: { title: { display: true, text: 'Cost Breakdown Per Period ($)', color: '#e2e8f0' }, legend: { labels: { color: '#94a3b8' } } },
        scales: { x: { ticks: { color: '#94a3b8', maxRotation: 45 }, grid: { color: '#1a2332' } }, y: { ticks: { color: '#94a3b8' }, grid: { color: '#1a2332' }, title: { display: true, text: '$', color: '#94a3b8' } } } }
    });
  }

  // 4. CUMULATIVE COST + CO₂ (dual axis)
  const ctx4 = cc('chart_cumulative');
  if (ctx4) {
    charts.cumulative = new Chart(ctx4, {
      type: 'line', data: {
        labels: timeLabels,
        datasets: [
          { label: 'Cumulative Cost ($)', data: mpc.timeline.map(t => t.cumCost.toFixed(0)), borderColor: '#06b6d4', yAxisID: 'y', tension: 0.3 },
          { label: 'Cumulative CO₂ (t)', data: mpc.timeline.map(t => t.co2.toFixed(1)), borderColor: '#10b981', yAxisID: 'y1', tension: 0.3 },
        ]
      },
      options: { responsive: true, plugins: { title: { display: true, text: 'Cumulative Cost & CO₂ Over Time', color: '#e2e8f0' }, legend: { labels: { color: '#94a3b8' } } },
        scales: {
          x: { ticks: { color: '#94a3b8', maxRotation: 45 }, grid: { color: '#1a2332' } },
          y: { type: 'linear', position: 'left', ticks: { color: '#06b6d4' }, grid: { color: '#1a2332' }, title: { display: true, text: '$', color: '#06b6d4' } },
          y1: { type: 'linear', position: 'right', ticks: { color: '#10b981' }, grid: { display: false }, title: { display: true, text: 'tonnes', color: '#10b981' } }
        } }
    });
  }

  // 5. PARETO FRONTIER (from β sweep)
  const ctx5 = cc('chart_pareto');
  if (ctx5) {
    const paretoData = sweep.results.map(r => ({ x: r.rate, y: r.co2 }));
    charts.pareto = new Chart(ctx5, {
      type: 'scatter', data: {
        datasets: [{
          label: 'Pareto Points (β sweep)',
          data: paretoData,
          backgroundColor: sweep.betas.map(b => b <= P.beta + 0.1 && b >= P.beta - 0.1 ? '#ef4444' : '#06b6d4'),
          pointRadius: sweep.betas.map(b => b <= P.beta + 0.1 && b >= P.beta - 0.1 ? 10 : 5),
        }]
      },
      options: { responsive: true, plugins: { title: { display: true, text: 'Pareto Frontier: Cost Rate vs CO₂/hr', color: '#e2e8f0' }, legend: { labels: { color: '#94a3b8' } },
        tooltip: { callbacks: { label: (ctx) => { const i = ctx.dataIndex; const r = sweep.results[i]; return `β=${r.beta.toFixed(1)} | DGU=${r.dgu} | $${r.rate.toFixed(0)}/hr | ${r.co2.toFixed(1)}t/hr`; } } }
      },
        scales: { x: { ticks: { color: '#94a3b8' }, grid: { color: '#1a2332' }, title: { display: true, text: 'Cost ($/hr)', color: '#94a3b8' } },
          y: { ticks: { color: '#94a3b8' }, grid: { color: '#1a2332' }, title: { display: true, text: 'CO₂ (t/hr)', color: '#94a3b8' } } } }
    });
  }

  // 6. β SENSITIVITY (3 lines: cost, DGU, CO₂)
  const ctx6 = cc('chart_beta');
  if (ctx6) {
    charts.beta = new Chart(ctx6, {
      type: 'line', data: {
        labels: sweep.betas.map(b => b.toFixed(1)),
        datasets: [
          { label: 'Cost Rate ($/hr)', data: sweep.results.map(r => r.rate.toFixed(0)), borderColor: '#06b6d4', yAxisID: 'y', tension: 0.3 },
          { label: 'DGU (MW)', data: sweep.results.map(r => r.dgu), borderColor: '#ef4444', yAxisID: 'y1', tension: 0.3 },
          { label: 'CO₂ (t/hr)', data: sweep.results.map(r => r.co2.toFixed(1)), borderColor: '#10b981', yAxisID: 'y1', tension: 0.3 },
        ]
      },
      options: { responsive: true, plugins: { title: { display: true, text: 'β Sensitivity: How ESG Weight Changes Everything', color: '#e2e8f0' }, legend: { labels: { color: '#94a3b8' } } },
        scales: {
          x: { ticks: { color: '#94a3b8' }, grid: { color: '#1a2332' }, title: { display: true, text: 'β', color: '#94a3b8' } },
          y: { type: 'linear', position: 'left', ticks: { color: '#06b6d4' }, grid: { color: '#1a2332' }, title: { display: true, text: '$/hr', color: '#06b6d4' } },
          y1: { type: 'linear', position: 'right', ticks: { color: '#ef4444' }, grid: { display: false }, title: { display: true, text: 'MW or t/hr', color: '#ef4444' } }
        } }
    });
  }

  // 7. DGU RAMP PROFILE
  const ctx7 = cc('chart_ramp');
  if (ctx7) {
    const rampPts = 20;
    const rampLabels = [], rampDGU = [], rampShed = [];
    for (let i = 0; i <= rampPts; i++) {
      const t = (i / rampPts) * P.dguRampMin;
      rampLabels.push(t.toFixed(1) + ' min');
      const dguPow = (i / rampPts) * (mpc.timeline.length > 1 ? (typeof mpc.timeline[1].dgu === 'number' ? mpc.timeline[1].dgu : P.deficit) : P.deficit);
      rampDGU.push(dguPow.toFixed(0));
      rampShed.push((P.deficit - dguPow).toFixed(0));
    }
    charts.ramp = new Chart(ctx7, {
      type: 'line', data: {
        labels: rampLabels,
        datasets: [
          { label: 'DGU Power (MW)', data: rampDGU, borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.2)', fill: true, tension: 0.1 },
          { label: 'Total Shed (MW)', data: rampShed, borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.2)', fill: true, tension: 0.1 },
        ]
      },
      options: { responsive: true, plugins: { title: { display: true, text: 'DGU Ramp-Up Profile (Phase 1)', color: '#e2e8f0' }, legend: { labels: { color: '#94a3b8' } } },
        scales: { x: { ticks: { color: '#94a3b8' }, grid: { color: '#1a2332' } }, y: { ticks: { color: '#94a3b8' }, grid: { color: '#1a2332' }, title: { display: true, text: 'MW', color: '#94a3b8' } } } }
    });
  }

  // 8. HEATMAP (DGU level x β -> cost) as bubble chart
  const ctx8 = cc('chart_heatmap');
  if (ctx8) {
    const carbonPerMW = P.co2Rate * P.esgPenalty;
    const heatData = [];
    for (let b = 0.5; b <= 4; b += 0.5) {
      for (let dgu = 0; dgu <= P.deficit; dgu += 10) {
        const shed = P.deficit - dgu;
        const hvac = Math.min(P.hvacMax, shed);
        const pump = Math.min(P.pumpMax, shed - hvac);
        const mill = Math.min(P.millMax, shed - hvac - pump);
        if (hvac + pump + mill + dgu < P.deficit - 1) continue;
        const hvacFrac = P.hvacMax > 0 ? hvac / P.hvacMax : 0;
        const pumpFrac = P.pumpMax > 0 ? pump / P.pumpMax : 0;
        const millFrac = P.millMax > 0 ? mill / P.millMax : 0;
        const rate = P.dguFuel * dgu + b * carbonPerMW * dgu + P.hvacCost * hvacFrac + P.pumpCost * pumpFrac + P.millCost * millFrac;
        heatData.push({ x: b, y: dgu, r: Math.max(3, Math.min(15, rate / 2000)), rate });
      }
    }
    charts.heatmap = new Chart(ctx8, {
      type: 'bubble', data: {
        datasets: [{
          label: 'Cost Rate (bubble size)',
          data: heatData,
          backgroundColor: heatData.map(d => {
            const norm = (d.rate - 10000) / 25000;
            const r = Math.round(50 + norm * 200);
            const g = Math.round(200 - norm * 150);
            return `rgba(${r},${g},80,0.6)`;
          }),
        }]
      },
      options: { responsive: true, plugins: { title: { display: true, text: 'Cost Heatmap: DGU Level × β', color: '#e2e8f0' }, legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => `β=${ctx.raw.x} DGU=${ctx.raw.y}MW $${ctx.raw.rate.toFixed(0)}/hr` } }
      },
        scales: { x: { ticks: { color: '#94a3b8' }, grid: { color: '#1a2332' }, title: { display: true, text: 'β', color: '#94a3b8' } },
          y: { ticks: { color: '#94a3b8' }, grid: { color: '#1a2332' }, title: { display: true, text: 'DGU (MW)', color: '#94a3b8' } } } }
    });
  }
}

// ==== RENDER TIMELINE TABLE ====
function renderTable(mpc, P) {
  const tbody = document.getElementById('sim_table_body');
  if (!tbody) return;
  tbody.innerHTML = '';
  mpc.timeline.forEach((t, i) => {
    const tr = document.createElement('tr');
    const hrs = Math.floor(t.time); const mins = Math.round((t.time % 1) * 60);
    const timeStr = typeof t.dgu === 'string' ? '00:00→00:05' : `${String(hrs).padStart(2,'0')}:${String(mins).padStart(2,'0')}`;
    const dguStr = typeof t.dgu === 'string' ? 'Ramp' : t.dgu;
    const cls = t.penalty > P.warnPenalty ? 'row-danger' : t.penalty > 0 ? 'row-warn' : (t.pumpEsc > 0 ? 'row-warn' : '');
    tr.className = cls;
    tr.innerHTML = `<td>${timeStr}</td><td>${dguStr}</td><td>${t.hvac}</td><td>${t.pump}</td><td>${t.mill}</td>
      <td>${t.tRoom.toFixed(1)}°C</td><td>$${t.penalty.toFixed(0)}</td><td>$${t.pumpEsc.toFixed(0)}</td>
      <td>$${t.cost.toFixed(0)}</td><td>$${t.cumCost.toFixed(0)}</td><td>${t.co2.toFixed(1)}</td><td>${t.label}</td>`;
    tbody.appendChild(tr);
  });
}

// ==== UPDATE SUMMARY CARDS ====
function renderSummary(mpc, P) {
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('sum_cost', '$' + mpc.totalCost.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ','));
  set('sum_co2', mpc.totalCO2.toFixed(1) + ' t');
  set('sum_avg', '$' + (mpc.totalCost / P.duration).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + '/hr');
  set('sum_peak', mpc.peakTemp.toFixed(1) + '°C');
  set('sum_shifts', mpc.timeline.filter((t,i) => i > 1 && typeof t.dgu === 'number' && typeof mpc.timeline[i-1].dgu === 'number' && t.dgu !== mpc.timeline[i-1].dgu).length.toString());
  set('sum_dgu_hrs', mpc.cumDgu.toFixed(1) + ' hrs');
}

// ==== MAIN ENTRY ====
let debounceTimer;
function runSimulation() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    const P = getParams();
    const mpc = runMPC(P);
    const sweep = betaSweep(P);
    renderSummary(mpc, P);
    renderCharts(mpc, sweep, P);
    renderTable(mpc, P);
  }, 150);
}

document.addEventListener('DOMContentLoaded', () => {
  Chart.defaults.color = '#94a3b8';
  Chart.defaults.borderColor = '#2a3a52';
  Chart.defaults.backgroundColor = 'rgba(6,182,212,0.5)';
  initLabels();
  runSimulation();
});
