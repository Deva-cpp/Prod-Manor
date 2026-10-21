// Prod Manor reel engine — renders an episode (JSON beats) as a pure function of time.
// window.PMR.load(episode) then window.PMR.seek(t) draws the frame at t seconds.
// Uses the original cast library (pm-characters.js → window.PM) so every reel is on-model.
(function () {
  const W = 1080, H = 1920, FLOOR = 1370, S = 1.85;
  const INK = '#1A1C3A', MOON = '#C9D3F4', CREAM = '#E7EBF8';
  const FD = "'Griffy', cursive", FM = "'JetBrains Mono', monospace", FS = "'DM Sans', sans-serif";
  const COLORS = { junior: '#F38A2D', null: '#E6ECFA', caller: '#F0465A', twins: '#97E52E', leak: '#EE56B8', ollie: '#E8BC3E' };
  const NAMES = { junior: 'Junior', null: 'The Null', caller: 'The Caller', twins: 'Fork & Join', leak: 'The Leak', ollie: 'Ollie One-Off' };
  const LENS = { x: 282.3, y: 243.9 }; // Junior's flashlight lens in character units

  // ---------- math ----------
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const mix = (a, b, p) => a + (b - a) * p;
  const ease = {
    out: (t) => 1 - Math.pow(1 - t, 3),
    inout: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    back: (t) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
  };
  const prog = (t, a, b, e) => (e || ease.out)(clamp((t - a) / Math.max(1e-6, b - a), 0, 1));
  const q = (v, s) => Math.round(v / s) * s;
  const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const hash = (n) => { const x = Math.sin(n * 127.1) * 43758.5453; return x - Math.floor(x); };

  // ---------- character cache ----------
  const cache = new Map();
  let uidN = 0;
  function charSVG(who, opts, scale) {
    const key = who + '|' + JSON.stringify(opts) + '|' + scale.toFixed(3);
    let s = cache.get(key);
    if (!s) {
      s = window.PM.svg(who, opts, 'c' + (uidN++).toString(36) + '_', scale);
      cache.set(key, s);
      if (cache.size > 600) cache.delete(cache.keys().next().value);
    }
    return s;
  }
  function geom(who, scale) {
    const d = window.PM.dims(who), k = S * scale;
    return { d, k, w: d.w * k, h: d.h * k, footY: (d.floor - d.y0) * k, cxOff: (d.cx - d.x0) * k, headOff: (d.top - d.y0) * k };
  }

  // ---------- backgrounds (ported from the cast reveal hallway, re-composed for 9:16) ----------
  function bgHallway() {
    let s = `<rect width="${W}" height="${H}" fill="#2A2E62"/>`;
    for (let x = 0; x < W; x += 72) s += `<rect x="${x}" y="0" width="36" height="${FLOOR - 190}" fill="#2E3268"/>`;
    const win = (x, y, moon) => {
      let g = `<path d="M${x},${y + 224} L${x},${y} A90,90 0 0 1 ${x + 180},${y} L${x + 180},${y + 224} Z" fill="#3A3F80" stroke="${INK}" stroke-width="8"/>` +
        `<path d="M${x + 16},${y + 212} L${x + 16},${y + 2} A74,74 0 0 1 ${x + 164},${y + 2} L${x + 164},${y + 212} Z" fill="#1B2559" stroke="${INK}" stroke-width="4"/>`;
      if (moon) g += `<circle cx="${x + 112}" cy="${y + 16}" r="70" fill="#9FB4FF" opacity="0.12"/><circle cx="${x + 112}" cy="${y + 16}" r="38" fill="${CREAM}" stroke="${INK}" stroke-width="4"/><circle cx="${x + 100}" cy="${y + 6}" r="8" fill="#CBD3EE"/><circle cx="${x + 124}" cy="${y + 30}" r="5" fill="#CBD3EE"/>`;
      g += `<line x1="${x + 90}" x2="${x + 90}" y1="${y - 70}" y2="${y + 212}" stroke="#3A3F80" stroke-width="10"/><line x1="${x + 16}" x2="${x + 164}" y1="${y + 104}" y2="${y + 104}" stroke="#3A3F80" stroke-width="10"/>` +
        `<rect x="${x - 14}" y="${y + 220}" width="208" height="18" rx="3" fill="#3A3F80" stroke="${INK}" stroke-width="5"/>`;
      return g;
    };
    s += win(120, 640, false) + win(780, 640, true);
    s += `<rect x="0" y="${FLOOR - 190}" width="${W}" height="180" fill="#22265A"/>`;
    for (let i = 0; i < 5; i++) s += `<rect x="${30 + i * 210}" y="${FLOOR - 162}" width="180" height="124" rx="4" fill="none" stroke="#2C3168" stroke-width="4"/>`;
    s += `<rect x="-10" y="${FLOOR - 200}" width="${W + 20}" height="16" fill="#343A78" stroke="${INK}" stroke-width="4"/>`;
    s += `<rect x="-10" y="${FLOOR - 24}" width="${W + 20}" height="26" fill="#1B1E48" stroke="${INK}" stroke-width="4"/>`;
    s += floorBoards();
    s += `<g style="mix-blend-mode:screen"><polygon points="142,870 280,870 470,${FLOOR + 220} 260,${FLOOR + 220}" fill="#C3D0FF" opacity="0.07"/><polygon points="802,870 940,870 1100,${FLOOR + 220} 900,${FLOOR + 220}" fill="#C3D0FF" opacity="0.1"/></g>`;
    return s;
  }
  function floorBoards() {
    let s = `<rect x="0" y="${FLOOR + 2}" width="${W}" height="${H - FLOOR}" fill="#181B44"/>`;
    [FLOOR + 40, FLOOR + 96, FLOOR + 164, FLOOR + 246, FLOOR + 344, FLOOR + 460].forEach((y, i) => {
      s += `<line x1="0" x2="${W}" y1="${y}" y2="${y}" stroke="#12143A" stroke-width="3"/>`;
      for (let j = 0; j < 4; j++) { const x = (j * 330 + i * 150) % W; s += `<line x1="${x}" x2="${x}" y1="${y}" y2="${y - (i ? 50 + i * 8 : 38)}" stroke="#12143A" stroke-width="3"/>`; }
    });
    return s;
  }
  function bgBedroom(t) {
    let s = `<rect width="${W}" height="${H}" fill="#23275A"/>`;
    for (let y = 0; y < FLOOR - 24; y += 64) s += `<line x1="0" x2="${W}" y1="${y}" y2="${y}" stroke="#262B60" stroke-width="2"/>`;
    // window with moon
    s += `<rect x="640" y="520" width="320" height="300" rx="8" fill="#1B2559" stroke="${INK}" stroke-width="8"/><line x1="800" x2="800" y1="520" y2="820" stroke="#3A3F80" stroke-width="10"/><line x1="640" x2="960" y1="670" y2="670" stroke="#3A3F80" stroke-width="10"/>` +
      `<circle cx="880" cy="590" r="34" fill="${CREAM}" stroke="${INK}" stroke-width="4"/>`;
    // desk + glowing monitor
    s += `<rect x="70" y="${FLOOR - 260}" width="420" height="22" rx="4" fill="#3A3F80" stroke="${INK}" stroke-width="5"/>` +
      `<rect x="96" y="${FLOOR - 238}" width="18" height="214" fill="#2C3168" stroke="${INK}" stroke-width="4"/><rect x="446" y="${FLOOR - 238}" width="18" height="214" fill="#2C3168" stroke="${INK}" stroke-width="4"/>` +
      `<rect x="150" y="${FLOOR - 470}" width="250" height="180" rx="10" fill="#0E1030" stroke="${INK}" stroke-width="7"/>` +
      `<rect x="166" y="${FLOOR - 454}" width="218" height="148" rx="4" fill="#3D2030" opacity="${0.75 + 0.25 * Math.sin(t * 9)}"/>` +
      `<text x="275" y="${FLOOR - 370}" text-anchor="middle" font-family="${FM}" font-weight="800" font-size="34" fill="#FF6B7D">500</text>` +
      `<rect x="255" y="${FLOOR - 290}" width="40" height="30" fill="#2C3168" stroke="${INK}" stroke-width="4"/>`;
    s += `<rect x="-10" y="${FLOOR - 24}" width="${W + 20}" height="26" fill="#1B1E48" stroke="${INK}" stroke-width="4"/>` + floorBoards();
    return s;
  }
  function bgServer(t) {
    let s = `<rect width="${W}" height="${H}" fill="#161936"/>`;
    for (let r = 0; r < 4; r++) {
      const x = 40 + r * 262;
      s += `<rect x="${x}" y="520" width="220" height="${FLOOR - 540}" rx="8" fill="#22265A" stroke="${INK}" stroke-width="7"/>`;
      for (let u = 0; u < 9; u++) {
        const y = 548 + u * 84;
        s += `<rect x="${x + 18}" y="${y}" width="184" height="62" rx="4" fill="#1B1E48" stroke="#12143A" stroke-width="3"/>`;
        for (let l = 0; l < 3; l++) {
          const on = hash(r * 31 + u * 7 + l * 3 + Math.floor(t * 6 + l)) > 0.45;
          const red = hash(r * 13 + u * 5 + l) > 0.82;
          s += `<circle cx="${x + 40 + l * 26}" cy="${y + 31}" r="7" fill="${on ? (red ? '#FF5468' : '#7CF29A') : '#2C3168'}"/>`;
        }
        s += `<rect x="${x + 124}" y="${y + 24}" width="60" height="14" rx="3" fill="#2C3168"/>`;
      }
    }
    s += `<rect x="-10" y="${FLOOR - 24}" width="${W + 20}" height="26" fill="#1B1E48" stroke="${INK}" stroke-width="4"/>` + floorBoards();
    return s;
  }
  const BGS = { hallway: bgHallway, bedroom: bgBedroom, server_room: bgServer };

  // ---------- acting: hands, face and head (rig options from pm-characters.js) ----------
  // Values: armL/armR = degrees raised from rest at the shoulder, tilt = head degrees,
  // lookX/lookY = -1..1 eye direction, brow = -1..1, talk = 0..1 mouth open.
  const S1 = Math.sin, AB = Math.abs;
  const GESTURES = {
    wave: (t) => ({ armR: 118 + 26 * S1(t * 14), tilt: 4, brow: 0.5 }),
    point: () => ({ armR: 72, brow: 0.6 }),
    shrug: (t) => ({ armL: 38, armR: 38, tilt: 9, brow: 1, lookY: -0.3 }),
    celebrate: (t) => ({ armL: 142 + 12 * S1(t * 12), armR: 142 + 12 * S1(t * 12 + 1.2), tilt: 6 * S1(t * 6), brow: 0.8, talk: 0.5 + 0.5 * AB(S1(t * 9)) }),
    cower: (t) => ({ armL: 112 + 5 * S1(t * 42), armR: 112 + 5 * S1(t * 42 + 1), tilt: -7, brow: 1, lookX: 0.7 * S1(t * 8.5) }),
    facepalm: () => ({ armL: 152, tilt: 11, lookY: 1, brow: -0.6 }),
    think: (t) => ({ armL: 42, tilt: 7, lookX: 0.6, lookY: -1, brow: 0.8 }),
    nod: (t) => ({ tilt: 5 * S1(t * 9), lookY: 0.3 + 0.5 * S1(t * 9), brow: 0.3 }),
    shake_head: (t) => ({ tilt: 9 * S1(t * 11), lookX: S1(t * 11), brow: -0.5 }),
    type: (t) => ({ armR: 14 + 9 * AB(S1(t * 16)), armL: 8 + 7 * AB(S1(t * 16 + 1.3)), lookY: 1, brow: -0.3 }),
    beckon: (t) => ({ armL: 58 + 24 * S1(t * 8), tilt: -4, brow: 0.6 }),
    dance: (t) => ({ armL: 70 + 55 * S1(t * 9), armR: 70 + 55 * S1(t * 9 + Math.PI), tilt: 7 * S1(t * 4.5) }),
    laugh: (t) => ({ talk: AB(S1(t * 17)), tilt: 6 * S1(t * 8.5), armL: 50 + 20 * S1(t * 17), armR: 50 + 20 * S1(t * 17 + 1), brow: 0.7 }),
    gasp: (t) => ({ armL: 62, armR: 62, brow: 1, talk: 0.95, tilt: -3 }),
    tremble: (t) => ({ armL: 16 + 4 * S1(t * 40), armR: 16 + 4 * S1(t * 40 + 1), lookX: 0.8 * S1(t * 6.3), brow: 1 }),
    look_up: () => ({ lookY: -1, brow: 0.6 }),
    look_down: () => ({ lookY: 1, brow: -0.3 }),
    look_left: () => ({ lookX: -1 }),
    look_right: () => ({ lookX: 1 }),
  };
  // eye saccades: hold a gaze, then dart quickly to the next one
  function gaze(seed, T, period) {
    const n = T / period + hash(seed) * 7, i = Math.floor(n), fr = n - i;
    const w = ease.inout(clamp((fr - 0.82) / 0.18, 0, 1));
    return [mix(hash(i * 3.1 + seed) * 2 - 1, hash((i + 1) * 3.1 + seed) * 2 - 1, w), mix(hash(i * 7.7 + seed) - 0.5, hash((i + 1) * 7.7 + seed) - 0.5, w)];
  }
  function autoActing(a, st, ctx, lt, dur, T, idx) {
    const who = a.who, other = ctx.others.find((o) => o.idx !== idx);
    const toward = other ? Math.sign(other.x - st.x) || 1 : 0;
    const [gx, gy] = gaze(idx * 13 + 5, T, 1.7);
    const r = { lookX: toward * 0.7 + gx * 0.3, lookY: gy * 0.6 };
    if (who === 'junior') { r.armL = 4 + 3 * S1(T * 1.3 + idx); r.armR = 3 + 3 * S1(T * 1.1 + idx + 2); }
    if (st.expr === 'scared') Object.assign(r, GESTURES.tremble(T));
    const t = ctx.type;
    if (t === 'pager' && who === 'junior') Object.assign(r, GESTURES.cower(T));
    if (t === 'code') { r.lookY = -1; r.lookX = gx * 0.4; if (who === 'junior') Object.assign(r, GESTURES.think(T), { lookX: 0.3 + gx * 0.3 }); }
    if (t === 'crash') {
      if (who === 'junior') Object.assign(r, GESTURES.cower(T));
      else if (st.expr === 'happy') Object.assign(r, GESTURES.laugh(T));
    }
    if (t === 'fix') {
      if (who === 'junior') Object.assign(r, lt < ctx.fixAt ? GESTURES.type(T) : GESTURES.celebrate(T));
      else if (lt >= ctx.fixAt) { r.tilt = -10; r.brow = 1; }
      else r.lookY = -1;
    }
    if (t === 'outro' && who === 'junior') Object.assign(r, GESTURES.wave(T));
    if (ctx.speaker === who && ctx.talking) {
      // lip flap: syllable rhythm + a little head bob while the line is being said
      r.talk = 0.15 + 0.85 * AB(S1(T * 13 + 2 * S1(T * 5.3)));
      r.tilt = (r.tilt || 0) + 2.5 * S1(T * 7);
      r.brow = Math.max(r.brow || 0, 0.4 * AB(S1(T * 3)));
      if (other) r.lookX = toward * 0.8;
    } else if (ctx.speaker && ctx.speakerX != null && ctx.speaker !== who && t === 'scene') {
      r.lookX = Math.sign(ctx.speakerX - st.x) * 0.85; // listeners look at whoever is talking
    }
    return r;
  }
  function acting(a, st, ctx, lt, dur, T, idx) {
    let base = autoActing(a, st, ctx, lt, dur, T, idx);
    const list = (a.gestures || []).slice();
    if (a.gesture) list.unshift({ g: a.gesture, at: a.gesture_at || 0 });
    const p = lt / Math.max(0.01, dur);
    let cur = base;
    list.filter((x) => GESTURES[x.g]).sort((x, y) => (x.at || 0) - (y.at || 0)).forEach((x) => {
      const start = (x.at || 0) * dur;
      if (lt < start) return;
      const tgt = Object.assign({}, base, GESTURES[x.g](T - start));
      const w = prog(lt, start, start + 0.3, ease.inout);
      const prev = cur;
      cur = {};
      new Set([...Object.keys(prev), ...Object.keys(tgt)]).forEach((k) => { cur[k] = mix(prev[k] || 0, tgt[k] || 0, w); });
    });
    // ease every rig channel in from rest at the start of the beat so cuts never pop
    const inW = prog(lt, 0, 0.22, ease.out);
    const o = {};
    for (const k of ['armL', 'armR', 'tilt', 'lookX', 'lookY', 'brow', 'talk']) {
      let v = (cur[k] || 0) * (k === 'lookX' || k === 'lookY' ? 1 : inW);
      if (k === 'lookX' && a.flip) v = -v;
      const qs = { armL: 1, armR: 1, tilt: 0.5, lookX: 0.1, lookY: 0.1, brow: 0.1, talk: 0.125 }[k];
      v = q(v, qs);
      if (v) o[k] = v;
    }
    if (a.who === 'caller' && (o.armR || o.armL)) st.opts.recv = q((st.opts.recv || 0) + 0.25 * Math.max(o.armR || 0, o.armL || 0) * (0.6 + 0.4 * S1(T * 10)), 1);
    if (a.who !== 'junior' && a.who !== 'ollie' && a.who !== 'twins') { delete o.armL; delete o.armR; }
    if (a.who === 'leak' || a.who === 'caller' || a.who === 'twins') { st.rot += (o.tilt || 0) * 0.5; delete o.tilt; }
    Object.assign(st.opts, o);
  }

  // ---------- actors ----------
  function actorState(a, lt, dur, T, idx, ctx) {
    const p = lt / Math.max(0.01, dur);
    const st = { x: a.x == null ? 0.5 : a.x, scale: a.scale || 1, op: a.opacity == null ? 1 : a.opacity, dy: 0, rot: 0, sx: 1, sy: 1, expr: a.expr || 'neutral', opts: {} };
    if (a.to) {
      const pm = prog(lt, 0, dur * 0.85, ease.inout);
      if (a.to.x != null) st.x = mix(st.x, a.to.x, pm);
      if (a.to.scale != null) st.scale = mix(st.scale, a.to.scale, pm);
    }
    if (a.expr_to && p >= (a.expr_at == null ? 0.5 : a.expr_at)) st.expr = a.expr_to;
    const who = a.who;
    // signature idles keep each character alive even when the beat gives no action
    if (who === 'junior') st.sy = 1 + 0.012 * Math.sin(T * 2.6 + idx);
    if (who === 'null') st.dy = -10 * Math.sin(T * 1.7 + idx);
    if (who === 'caller') { st.opts.spin = q((T * 140) % 360, 4); st.opts.recv = q(3 * Math.sin(T * 9), 1); }
    if (who === 'twins') st.opts.lean = q(5 + 2.5 * Math.sin(T * 3.2), 0.5);
    if (who === 'leak') { const wb = 0.025 * Math.sin(T * 3.4); st.sx = 1 + wb; st.sy = 1 - wb; }
    if (who === 'ollie') st.rot = 2 * Math.sin(T * 1.3);
    st.opts.blink = ((T + idx * 0.7) % 3.3) < 0.12;

    switch (a.action) {
      case 'enter_left': st.x = mix(-0.35, st.x, prog(lt, 0, 0.7, ease.out)); break;
      case 'enter_right': st.x = mix(1.35, st.x, prog(lt, 0, 0.7, ease.out)); break;
      case 'exit_left': st.x = mix(st.x, -0.45, prog(lt, dur - 0.7, dur, ease.inout)); break;
      case 'exit_right': st.x = mix(st.x, 1.45, prog(lt, dur - 0.7, dur, ease.inout)); break;
      case 'shake': st.x += 0.006 * Math.sin(T * 70); st.expr = a.expr || 'scared'; break;
      case 'hop': { const h = lt % 0.6; st.dy -= 36 * Math.abs(Math.sin(Math.PI * h / 0.6)); break; }
      case 'grow': st.scale *= mix(1, a.amount || 1.8, prog(lt, 0, dur * 0.8, ease.inout)); break;
      case 'shrink': st.scale *= mix(1, a.amount || 0.4, prog(lt, 0, dur * 0.8, ease.inout)); break;
      case 'pop_in': st.scale *= prog(lt, 0, 0.45, ease.back); break;
      case 'fade_in': st.op *= prog(lt, 0, 0.6); break;
      case 'fade_out': st.op *= 1 - prog(lt, dur * 0.4, dur); break;
      case 'defeated': st.expr = 'scared'; st.scale *= mix(1, 0.55, prog(lt, dur * 0.35, dur, ease.inout)); st.op *= mix(1, 0.15, prog(lt, dur * 0.5, dur)); break;
      case 'peek': st.x = mix(a.x > 0.5 ? 1.25 : -0.25, st.x, prog(lt, 0.2, 1.0, ease.out)); break;
      case 'spin': st.opts.dial = q(290 * prog(lt, 0, dur * 0.4, ease.inout) - 290 * prog(lt, dur * 0.5, dur * 0.9, ease.inout), 2); st.opts.recv = q(9 * Math.sin(T * 9), 1); break;
      case 'float': st.dy -= 24 + 14 * Math.sin(T * 2.2); break;
    }
    if (who === 'null' && a.action !== 'fade_in' && a.action !== 'fade_out') st.op *= 0.92; // he's barely there
    if (ctx) acting(a, st, ctx, lt, dur, T, idx);
    return st;
  }

  function renderActor(a, lt, dur, T, idx, ctx) {
    const st = actorState(a, lt, dur, T, idx, ctx);
    if (st.op <= 0.01 || st.scale <= 0.01) return { html: '', head: null };
    const copies = a.who === 'caller' && a.copies ? Math.max(1, Math.round(a.copies * (a.action === 'stack' ? prog(lt, 0, dur * 0.8, ease.inout) : 1))) : 1;
    let html = '', head = null;
    for (let c = 0; c < copies; c++) {
      const sc = st.scale * Math.pow(0.78, c);
      const g = geom(a.who, sc);
      const cx = st.x * W;
      const left = cx - g.cxOff;
      const stackLift = c === 0 ? 0 : (() => { let up = 0; for (let j = 0; j < c; j++) up += geom(a.who, st.scale * Math.pow(0.78, j)).h * 0.62; return up; })();
      const wobble = c > 0 ? Math.sin(T * 3 + c) * (2 + c * 1.5) : 0;
      const top = FLOOR - g.footY + (a.y_off || 0) + st.dy - stackLift;
      const opts = Object.assign({ expr: st.expr }, st.opts);
      const flip = a.flip ? ' scaleX(-1)' : '';
      const ox = ((g.d.cx - g.d.x0) / g.d.w) * 100, oy = ((g.d.floor - g.d.y0) / g.d.h) * 100;
      html += `<div style="position:absolute;left:${left.toFixed(1)}px;top:${top.toFixed(1)}px;width:${g.w.toFixed(1)}px;height:${g.h.toFixed(1)}px;opacity:${st.op.toFixed(3)};transform-origin:${ox}% ${oy}%;transform:rotate(${(st.rot + wobble).toFixed(2)}deg) scale(${st.sx.toFixed(4)},${st.sy.toFixed(4)})${flip};z-index:${10 + (a.z || 0)}">${charSVG(a.who, opts, S * sc)}</div>`;
      html += `<div style="position:absolute;left:${(cx - g.w * 0.32).toFixed(1)}px;top:${(FLOOR - 10 - (a.y_off || 0) * 0).toFixed(1)}px;width:${(g.w * 0.64).toFixed(1)}px;height:22px;border-radius:50%;background:rgba(8,9,28,${(0.45 * st.op).toFixed(2)});z-index:5"></div>`;
      if (c === copies - 1) head = { x: cx, y: top + g.headOff, w: g.w, h: g.h, who: a.who, cyMid: top + g.h * 0.45 };
      if (a.who === 'junior' && c === 0) {
        const fx = a.flip ? -1 : 1;
        // the flashlight rides the right arm: rotate the lens around the shoulder pivot (170,180)
        const ang = -(st.opts.armR || 0) * Math.PI / 180, ca = Math.cos(ang), sa = Math.sin(ang);
        const lxu = 170 + (LENS.x - 170) * ca - (LENS.y - 180) * sa, lyu = 180 + (LENS.x - 170) * sa + (LENS.y - 180) * ca;
        head.lens = { x: left + (a.flip ? g.w - (lxu - g.d.x0) * g.k : (lxu - g.d.x0) * g.k), y: top + (lyu - g.d.y0) * g.k, dir: fx };
      }
    }
    return { html, head };
  }

  // ---------- UI pieces ----------
  // which dialogue line is up at lt. Voiced beats carry real timings (_say_t: [start, length] per line);
  // otherwise the lines split the beat evenly. p = progress through the line's slot, typed = share of text shown.
  function sayAt(b, says, lt, dur) {
    if (!says.length) return null;
    const st = b._say_t;
    if (st && st.length === says.length) {
      let i = 0;
      while (i + 1 < st.length && lt >= st[i + 1][0] - 0.1) i++;
      const [t0, d] = st[i], end = i + 1 < st.length ? st[i + 1][0] - 0.1 : dur;
      return { i, p: clamp((lt - t0 + 0.1) / Math.max(0.3, end - t0 + 0.1), 0, 1),
        typed: clamp((lt - t0) / Math.max(0.2, d * 0.9), 0, 1), talking: lt > t0 && lt < t0 + d };
    }
    const seg = dur / says.length, i = clamp(Math.floor(lt / seg), 0, says.length - 1), p = (lt - i * seg) / seg;
    return { i, p, typed: clamp(p * 2.2, 0, 1), talking: p > 0.04 && p < 0.5 };
  }

  function bubble(h, text, p, color, side, typed) {
    if (!h) return '';
    const shown = text.slice(0, Math.ceil(text.length * (typed == null ? clamp(p * 2.2, 0, 1) : typed)));
    const pop = prog(p, 0, 0.12, ease.back);
    const w = Math.min(820, Math.max(300, text.length * 22 + 80));
    let x = clamp(h.x - w / 2, 40, W - 40 - w);
    const y = Math.max(300, h.y - 210);
    const tailX = clamp(h.x, x + 60, x + w - 60);
    return `<div style="position:absolute;left:${x}px;top:${y}px;width:${w}px;z-index:60;transform:scale(${pop.toFixed(3)});transform-origin:${tailX - x}px 170px">
      <div style="background:${CREAM};border:6px solid ${INK};border-radius:34px;padding:22px 30px;font-family:${FS};font-weight:700;font-size:40px;line-height:1.18;color:${INK};box-shadow:0 8px 0 ${INK};min-height:60px">
        <span style="display:block;font-family:${FM};font-size:22px;letter-spacing:.18em;color:${color};-webkit-text-stroke:0;margin-bottom:6px;filter:brightness(.7)">${esc((NAMES[h.who] || '').toUpperCase())}</span>${esc(shown)}<span style="opacity:0">${esc(text.slice(shown.length))}</span></div>
      <svg width="60" height="46" style="position:absolute;left:${tailX - x - 30}px;bottom:-38px;overflow:visible"><path d="M8,0 L30,40 L48,0" fill="${CREAM}" stroke="${INK}" stroke-width="6" stroke-linejoin="round"/><rect x="4" y="-8" width="48" height="10" fill="${CREAM}"/></svg>
    </div>`;
  }

  const KWS = 'function|return|if|else|const|let|var|for|while|new|class|def|async|await|import|from|null|undefined|None|true|false|True|False|this|self|in|of|elif|lambda|try|catch|except|finally|throw|raise|public|static|void|int|String|synchronized|go|func|defer|chan';
  const TOK = new RegExp('(\\/\\/.*$|#.*$)|("(?:[^"\\\\]|\\\\.)*"|\'(?:[^\'\\\\]|\\\\.)*\'|`[^`]*`)|\\b(' + KWS + ')\\b|\\b(\\d+(?:\\.\\d+)?)\\b|([A-Za-z_]\\w*)(?=\\s*\\()', 'g');
  function hl(line) {
    let out = '', last = 0, m;
    TOK.lastIndex = 0;
    while ((m = TOK.exec(line))) {
      out += esc(line.slice(last, m.index));
      const [tok, com, str, kw, num, fn] = m;
      const color = com ? '#6870B8' : str ? '#B5E48C' : kw ? '#FF8FB1' : num ? '#FFC66D' : '#7FD1FF';
      out += `<span style="color:${color}${com ? ';font-style:italic' : ''}">${esc(tok)}</span>`;
      last = m.index + tok.length;
      if (!tok.length) TOK.lastIndex++;
    }
    return out + esc(line.slice(last));
  }
  function codePanel(b, lt, dur, T) {
    const lines = (b.lines || []).slice(0, 9);
    const typeEnd = b.typing === false ? 0 : Math.min(dur * 0.55, 0.35 + lines.join('').length * 0.028);
    const total = lines.join('\n').length;
    let budget = typeEnd <= 0 ? Infinity : Math.floor(total * prog(lt, 0.25, typeEnd, (x) => x));
    const fixAt = b.type === 'fix' ? dur * 0.38 : Infinity;
    const isFixed = lt >= fixAt;
    const fixLine = b.fix_line == null ? -1 : b.fix_line - 1;
    const hlSet = new Set((b.highlight || []).map((n) => n - 1));
    const errOn = b.error && lt > typeEnd + 0.2 && !(b.type === 'fix' && isFixed);
    const inP = prog(lt, 0, 0.35, ease.back);
    const shakeX = errOn && lt - typeEnd < 0.5 ? 8 * Math.sin(T * 80) * (1 - (lt - typeEnd) / 0.5) : 0;
    const longest = Math.max(0, ...lines.map((l) => l.length), b.after ? b.after.length : 0);
    const fs = longest <= 28 ? 40 : longest <= 33 ? 36 : longest <= 38 ? 32 : 28;
    let rows = '';
    lines.forEach((ln, i) => {
      let text = ln;
      if (budget !== Infinity) { const take = clamp(budget, 0, ln.length); text = ln.slice(0, take); budget -= ln.length + 1; }
      let rowBg = 'transparent', content;
      if (i === fixLine && b.type === 'fix') {
        const after = b.after || ln;
        const pf = prog(lt, fixAt, fixAt + 0.8, (x) => x);
        if (!isFixed) { content = hl(ln); rowBg = 'rgba(255,84,104,.22)'; }
        else {
          const typed = after.slice(0, Math.ceil(after.length * pf));
          content = `<span style="color:#FF7A8A;text-decoration:line-through;opacity:${(1 - pf).toFixed(2)};position:absolute">${esc(ln)}</span><span>${hl(typed)}</span>`;
          rowBg = `rgba(124,242,154,${(0.28 * pf).toFixed(2)})`;
        }
      } else {
        content = hl(text);
        if (hlSet.has(i) && errOn) rowBg = 'rgba(255,84,104,.24)';
      }
      const caret = budget !== Infinity && budget < 0 && budget > -ln.length - 2 && text.length < ln.length ? '<span style="background:#FFE7A0;color:#FFE7A0">_</span>' : '';
      rows += `<div style="display:flex;background:${rowBg};border-radius:6px;min-height:${Math.round(fs * 1.45)}px;align-items:center;position:relative"><span style="width:52px;color:#4E5596;text-align:right;margin-right:22px;flex:none">${i + 1}</span><span style="white-space:pre;position:relative">${content}${caret}</span></div>`;
    });
    const fname = b.file || (b.lang === 'python' ? 'haunted.py' : b.lang === 'java' ? 'Haunted.java' : 'haunted.js');
    let err = '';
    if (errOn) {
      const ep = prog(lt, typeEnd + 0.2, typeEnd + 0.55, ease.back);
      err = `<div style="margin-top:22px;transform:scale(${ep.toFixed(3)});transform-origin:left top;background:#3B0D1B;border:5px solid #FF5468;border-radius:16px;padding:16px 22px;color:#FFD6DC;font-family:${FM};font-weight:800;font-size:33px;line-height:1.25;white-space:normal">${esc(b.error)}</div>`;
    }
    if (b.type === 'fix' && isFixed) {
      const ep = prog(lt, fixAt + 0.8, fixAt + 1.1, ease.back);
      err = `<div style="margin-top:22px;transform:scale(${ep.toFixed(3)});transform-origin:left top;background:#0F3B24;border:5px solid #7CF29A;border-radius:16px;padding:16px 22px;color:#D9FFE3;font-family:${FM};font-weight:800;font-size:33px;line-height:1.25;white-space:normal">${esc(b.note || 'Fixed. The haunting stops.')}</div>`;
    }
    return `<div style="position:absolute;left:${54 + shakeX}px;top:290px;width:${W - 108}px;z-index:50;transform:scale(${inP.toFixed(3)});transform-origin:50% 0">
      <div style="background:#0E1030;border:7px solid ${INK};border-radius:28px;box-shadow:0 12px 0 ${INK}, 0 0 80px rgba(127,209,255,.18);overflow:hidden">
        <div style="display:flex;align-items:center;gap:12px;padding:18px 26px;background:#1B1E48;border-bottom:5px solid ${INK}">
          <span style="width:20px;height:20px;border-radius:50%;background:#FF5468"></span><span style="width:20px;height:20px;border-radius:50%;background:#FFC66D"></span><span style="width:20px;height:20px;border-radius:50%;background:#7CF29A"></span>
          <span style="margin-left:14px;font-family:${FM};font-weight:700;font-size:26px;color:${MOON}">${esc(fname)}</span>
        </div>
        <div style="padding:22px 26px 26px 6px;font-family:${FM};font-weight:700;font-size:${fs}px;color:${CREAM}">${rows}${err ? `<div style="padding-left:20px">${err}</div>` : ''}</div>
      </div></div>`;
  }

  function captions(text, lt, dur) {
    if (!text) return '';
    const words = text.split(/\s+/).filter(Boolean);
    const per = (dur - 0.3) / Math.max(1, words.length);
    const cur = Math.floor((lt - 0.1) / per);
    // show a sliding window of ~7 words so captions stay big and readable
    const start = Math.max(0, Math.floor(Math.max(0, cur) / 7) * 7);
    const win = words.slice(start, start + 7);
    const html = win.map((w, i) => {
      const gi = start + i, on = gi <= cur;
      return `<span style="color:${gi === cur ? '#FFE7A0' : on ? CREAM : 'rgba(231,235,248,.55)'}">${esc(w)}</span>`;
    }).join(' ');
    return `<div style="position:absolute;left:70px;right:70px;top:1430px;z-index:80;text-align:center;font-family:${FS};font-weight:700;font-size:52px;line-height:1.2;-webkit-text-stroke:2px ${INK};text-shadow:0 5px 0 ${INK},0 0 24px rgba(10,11,30,.9)">${html}</div>`;
  }

  function lightLayer(b, lt, dur, T, heads) {
    const light = b.light || 'dark';
    let s = '';
    if (light === 'flashlight') {
      const j = heads.find((h) => h && h.lens);
      const tgt = heads.find((h) => h && h.who !== 'junior');
      if (j && tgt) {
        const L = j.lens, tx = tgt.x, ty = tgt.cyMid;
        const flick = lt < 0.35 ? (hash(Math.floor(T * 30)) > 0.5 ? 1 : 0.15) : 1;
        const dx = tx - L.x, dy = ty - L.y, len = Math.hypot(dx, dy) || 1, nx = -dy / len, ny = dx / len, r = tgt.h * 0.45 + 30;
        const ex = L.x + dx * 1.6, ey = L.y + dy * 1.6, R2 = r * 1.6;
        const pts = [[L.x + nx * 10, L.y + ny * 10], [ex + nx * R2, ey + ny * R2], [ex - nx * R2, ey - ny * R2], [L.x - nx * 10, L.y - ny * 10]].map((v) => v.map((n) => n.toFixed(1)).join(',')).join(' ');
        s += `<svg width="${W}" height="${H}" style="position:absolute;left:0;top:0;z-index:30;mix-blend-mode:screen;opacity:${flick}"><defs><linearGradient id="bm" gradientUnits="userSpaceOnUse" x1="${L.x}" y1="${L.y}" x2="${ex}" y2="${ey}"><stop offset="0" stop-color="#FFE7A0" stop-opacity="0.55"/><stop offset="0.6" stop-color="#FFE7A0" stop-opacity="0.16"/><stop offset="1" stop-color="#FFE7A0" stop-opacity="0"/></linearGradient><radialGradient id="sp"><stop offset="0" stop-color="#FFE7A0" stop-opacity="0.3"/><stop offset="1" stop-color="#FFE7A0" stop-opacity="0"/></radialGradient></defs><polygon points="${pts}" fill="url(#bm)"/><ellipse cx="${tx}" cy="${ty}" rx="${r * 1.1}" ry="${r * 1.15}" fill="url(#sp)"/></svg>`;
      }
    }
    let vig = light === 'normal' ? 0.25 : 0.62;
    if (light === 'flicker') vig = hash(Math.floor(T * 14)) > 0.78 ? 0.92 : 0.5;
    s += `<div style="position:absolute;inset:0;z-index:40;pointer-events:none;background:radial-gradient(ellipse 75% 55% at 50% 52%, rgba(8,9,28,0) 40%, rgba(8,9,28,${vig}) 100%)"></div>`;
    if (light === 'red') s += `<div style="position:absolute;inset:0;z-index:41;background:#FF2440;mix-blend-mode:multiply;opacity:${(0.25 + 0.2 * Math.sin(T * 7)).toFixed(3)}"></div><div style="position:absolute;inset:0;z-index:41;background:#FF2440;opacity:${(0.06 + 0.06 * Math.sin(T * 7)).toFixed(3)}"></div>`;
    return s;
  }

  function brandBug(ep, T) {
    return `<div style="position:absolute;left:0;right:0;top:205px;z-index:90;text-align:center;font-family:${FM};font-weight:800;font-size:24px;letter-spacing:.32em;color:${MOON};opacity:.75;text-shadow:0 3px 0 ${INK}">PROD MANOR${ep.series_tag ? ' · ' + esc(ep.series_tag.toUpperCase()) : ''}</div>`;
  }

  // ---------- beat renderers ----------
  function renderBeat(ep, b, lt, dur, T) {
    let stage = '', ui = '';
    const bg = BGS[b.bg] || (b.type === 'pager' ? bgBedroom : b.type === 'crash' ? bgServer : bgHallway);
    const cam = b.camera || {};
    const z = mix(cam.zoom_from || 1, cam.zoom_to || (b.type === 'scene' ? 1.05 : 1.02), prog(lt, 0, dur, ease.inout));
    const fx = (cam.focus_x == null ? 0.5 : cam.focus_x) * W;
    let shake = b.shake || b.type === 'crash' ? (b.type === 'crash' ? 14 * (1 - prog(lt, 0, 1.4)) + 3 : 6) : 0;
    const sx = shake * Math.sin(T * 61), sy = shake * Math.cos(T * 47);

    let actors = b.actors || [];
    if (!actors.length) {
      if (b.type === 'pager') actors = [{ who: 'junior', expr: 'scared', x: 0.5, action: 'shake' }];
      if (b.type === 'crash') actors = [{ who: 'junior', expr: 'scared', x: 0.28, action: 'shake' }, { who: ep.monster, expr: 'happy', x: 0.72, action: 'hop' }];
      if (b.type === 'fix') actors = [{ who: 'junior', expr: 'happy', x: 0.27 }, { who: ep.monster, expr: 'scared', x: 0.73, action: 'defeated' }];
      if (b.type === 'code') actors = [{ who: 'junior', expr: 'scared', x: 0.3, scale: 0.85 }, { who: ep.monster, expr: 'happy', x: 0.72, scale: 0.85 }];
    }
    if (b.type === 'code' || b.type === 'fix') {
      // keep characters below the editor panel: shrink them as the code grows
      const n = (b.lines || []).length, cap = n <= 3 ? 0.78 : n <= 5 ? 0.62 : 0.5;
      actors = actors.map((a) => Object.assign({}, a, { scale: Math.min(a.scale || 1, cap) }));
    }
    // who is speaking right now (bubbles play in order across the beat)
    const saysAll = (b.say || []).filter((s) => s && s.text);
    let speaker = null, talking = false;
    const line = sayAt(b, saysAll, lt, dur);
    if (line) { speaker = saysAll[line.i].who; talking = line.talking; }
    const ctx = { type: b.type, speaker, talking, fixAt: dur * 0.38,
      others: actors.map((a, i) => ({ idx: i, who: a.who, x: a.x == null ? 0.5 : a.x })) };
    const sa = actors.find((a) => a.who === speaker);
    ctx.speakerX = sa ? (sa.x == null ? 0.5 : sa.x) : null;
    const heads = [];
    actors.forEach((a, i) => { if (!NAMES[a.who]) return; const r = renderActor(a, lt, dur, T, i, ctx); stage += r.html; heads.push(r.head); });

    // title card: monster silhouette reveal
    if (b.type === 'title') {
      const who = b.monster || ep.monster;
      const g = geom(who, { twins: 1.6, leak: 1.5, caller: 1.5, null: 1.05, ollie: 0.82 }[who] || 1.1);
      const rev = prog(lt, 0.5, 1.3, ease.inout);
      const sil = rev < 1;
      stage += `<div style="position:absolute;left:${(W / 2 - g.cxOff).toFixed(1)}px;top:${(FLOOR - g.footY - 10 * Math.sin(T * 2)).toFixed(1)}px;z-index:12;filter:brightness(${mix(0.25, 1, rev).toFixed(3)})">${charSVG(who, { expr: rev > 0.8 ? 'happy' : 'neutral', silhouette: sil && rev < 0.5, blink: (T % 3.3) < 0.12, spin: q((T * 140) % 360, 4) }, S * g.k / S)}</div>`;
      const tp = prog(lt, 0.15, 0.6, ease.back);
      ui += `<div style="position:absolute;left:60px;right:60px;top:300px;z-index:70;text-align:center;transform:scale(${tp.toFixed(3)})">
        <div style="font-family:${FM};font-weight:800;font-size:28px;letter-spacing:.3em;color:${MOON}">${esc(b.kicker || 'TONIGHT\'S HAUNTING')}</div>
        <div style="font-family:${FD};font-size:${(b.text || '').length > 22 ? 96 : 118}px;text-wrap:balance;line-height:1.02;color:${COLORS[who]};text-shadow:0 8px 0 ${INK},0 0 50px rgba(10,11,30,.7);margin-top:14px">${esc(b.text || ep.title)}</div>
        ${b.sub ? `<div style="font-family:${FS};font-weight:700;font-size:44px;line-height:1.2;color:${CREAM};margin-top:22px;text-shadow:0 4px 0 ${INK}">${esc(b.sub)}</div>` : ''}
      </div>`;
    }

    if (b.type === 'pager') {
      const buzz = Math.sin(T * 90) * 10 * (hash(Math.floor(T * 3)) > 0.3 ? 1 : 0.2);
      const pin = prog(lt, 0, 0.35, ease.back);
      ui += `<div style="position:absolute;left:150px;right:150px;top:330px;z-index:70;transform:translateX(${buzz.toFixed(1)}px) rotate(${(buzz * 0.25).toFixed(2)}deg) scale(${pin.toFixed(3)})">
        <div style="background:#0E1030;border:8px solid ${INK};border-radius:44px;padding:30px;box-shadow:0 14px 0 ${INK},0 0 90px rgba(255,84,104,.35)">
          <div style="background:#3B0D1B;border:5px solid #FF5468;border-radius:24px;padding:26px;text-align:center">
            <div style="font-family:${FM};font-weight:800;font-size:96px;color:#FF6B7D;line-height:1">${esc(b.time || '3:00 AM')}</div>
            <div style="font-family:${FM};font-weight:800;font-size:38px;color:#FFD6DC;margin-top:14px;letter-spacing:.08em">${esc(b.text || 'PROD IS DOWN')}</div>
          </div>
          <div style="font-family:${FS};font-weight:700;font-size:30px;color:${MOON};text-align:center;margin-top:18px">${esc(b.sub || 'PagerDuty · Severity 1')}</div>
        </div></div>`;
    }

    if (b.type === 'code' || b.type === 'fix') ui += codePanel(b, lt, dur, T);

    if (b.type === 'crash') {
      const ip = prog(lt, 0.05, 0.4, ease.back);
      let glitch = '';
      for (let i = 0; i < 6; i++) { const y = hash(i * 9 + Math.floor(T * 20)) * H; glitch += `<div style="position:absolute;left:0;right:0;top:${y.toFixed(0)}px;height:${(8 + hash(i + Math.floor(T * 20)) * 40).toFixed(0)}px;background:rgba(255,84,104,.18);transform:translateX(${((hash(i * 3 + Math.floor(T * 25)) - 0.5) * 80).toFixed(0)}px);z-index:45"></div>`; }
      ui += glitch + `<div style="position:absolute;left:60px;right:60px;top:320px;z-index:70;transform:scale(${ip.toFixed(3)})">
        <div style="font-family:${FD};font-size:130px;line-height:1;color:#FF5468;text-align:center;text-shadow:0 8px 0 ${INK}">${esc(b.title || 'CRASH!')}</div>
        <div style="margin-top:26px;background:#0E1030;border:6px solid #FF5468;border-radius:22px;padding:22px 26px;font-family:${FM};font-weight:800;font-size:34px;line-height:1.3;color:#FFD6DC;box-shadow:0 10px 0 ${INK}">${esc(b.text || 'Uncaught Error')}</div></div>`;
    }

    if (b.type === 'outro') {
      const ip = prog(lt, 0.1, 0.55, ease.back);
      const next = b.next_monster && NAMES[b.next_monster] ? b.next_monster : null;
      if (next) {
        const g = geom(next, 0.9), px = prog(lt, dur * 0.45, dur * 0.75, ease.out);
        stage += `<div style="position:absolute;left:${(W - g.w * 0.62 * px).toFixed(1)}px;top:${(FLOOR - g.footY).toFixed(1)}px;z-index:12;filter:brightness(.55)">${charSVG(next, { expr: 'happy', silhouette: true }, S * 0.9)}</div>`;
      }
      ui += `<div style="position:absolute;left:60px;right:60px;top:300px;z-index:70;text-align:center;transform:scale(${ip.toFixed(3)})">
        <div style="font-family:${FM};font-weight:800;font-size:30px;letter-spacing:.3em;color:#7CF29A">${esc(b.kicker || 'THE LESSON')}</div>
        <div style="margin-top:18px;background:#0E1030;border:7px solid ${INK};border-radius:30px;padding:30px 34px;font-family:${FS};font-weight:700;font-size:50px;line-height:1.2;color:${CREAM};box-shadow:0 12px 0 ${INK}">${esc(b.lesson || '')}</div>
        <div style="margin-top:34px;font-family:${FD};font-size:60px;line-height:1.1;text-wrap:balance;color:#FFE7A0;text-shadow:0 6px 0 ${INK}">${esc(b.cta || 'Follow before the next bug wakes up')}</div>
        ${next ? `<div style="margin-top:20px;font-family:${FM};font-weight:800;font-size:28px;letter-spacing:.2em;color:${COLORS[next]};opacity:${prog(lt, dur * 0.6, dur * 0.8).toFixed(2)}">NEXT: ${esc(NAMES[next].toUpperCase())}</div>` : ''}
      </div>`;
    }

    // dialogue bubbles, sequential across the beat
    if (line) {
      const s = saysAll[line.i];
      const h = heads.find((x) => x && x.who === s.who) || heads[0];
      ui += bubble(h, s.text, line.p, COLORS[s.who] || CREAM, null, line.typed);
    }

    if (['title', 'pager', 'crash', 'outro'].includes(b.type) || b.on_screen) ui = `<div style="position:absolute;left:0;right:0;top:0;height:1100px;z-index:42;background:linear-gradient(to bottom, rgba(10,11,30,.82) 0%, rgba(10,11,30,.6) 55%, rgba(10,11,30,0) 100%)"></div>` + ui;
    ui += lightLayer(b, lt, dur, T, heads);
    if (b.type !== 'title' && b.type !== 'outro') {
      // voiced narration: captions start with the narrator and run at his pace
      const nt = b._narr_t;
      if (!nt) ui += captions(b.narration, lt, dur);
      else if (lt >= nt[0] - 0.05) ui += captions(b.narration, lt - nt[0], nt[1] + 0.3);
    }
    if (b.on_screen) ui += `<div style="position:absolute;left:60px;right:60px;top:${b.type === 'scene' ? 300 : 1270}px;z-index:75;text-align:center;font-family:${FD};font-size:76px;line-height:1.05;color:#FFE7A0;text-shadow:0 6px 0 ${INK}">${esc(b.on_screen)}</div>`;

    const bgSvg = `<svg width="${W}" height="${H}" style="position:absolute;left:0;top:0">${bg(T)}</svg>`;
    return `<div style="position:absolute;inset:0;transform-origin:${fx}px ${FLOOR - 300}px;transform:translate(${sx.toFixed(1)}px,${sy.toFixed(1)}px) scale(${z.toFixed(4)})">${bgSvg}${stage}</div>${ui}`;
  }

  // ---------- timeline ----------
  let EP = null, CUES = [], TOTAL = 0;
  function load(ep) {
    EP = ep; CUES = []; let t = 0;
    (ep.beats || []).forEach((b) => { const d = Math.max(0.8, +b.dur || 3); CUES.push({ b, t0: t, d }); t += d; });
    TOTAL = t;
    return { total: TOTAL, beats: CUES.map((c) => ({ type: c.b.type, t0: c.t0, d: c.d })) };
  }
  const root = () => document.getElementById('stage');
  function seek(T) {
    if (!EP) return;
    let i = CUES.findIndex((c) => T < c.t0 + c.d); if (i < 0) i = CUES.length - 1;
    const c = CUES[i], lt = T - c.t0;
    let html = renderBeat(EP, c.b, lt, c.d, T) + brandBug(EP, T);
    // cut transitions: quick dip at beat starts (skip on crash for a hard cut), flash on crash, fade-in from black at t=0
    const dip = i > 0 && c.b.type !== 'crash' ? 1 - prog(lt, 0, 0.18) : 0;
    const open = 1 - prog(T, 0, 0.35);
    const close = prog(T, TOTAL - 0.35, TOTAL);
    const black = Math.max(dip * 0.85, open, close);
    if (black > 0.01) html += `<div style="position:absolute;inset:0;background:#0B0C1F;z-index:200;opacity:${black.toFixed(3)}"></div>`;
    if (c.b.type === 'crash' && lt < 0.12) html += `<div style="position:absolute;inset:0;background:#FFF;z-index:201;opacity:${(1 - lt / 0.12).toFixed(3)}"></div>`;
    // film grain (static noise texture shifted per frame)
    html += `<div style="position:absolute;inset:-40px;z-index:150;pointer-events:none;opacity:.07;background-image:url(&quot;data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='220' height='220' filter='url(%23n)'/></svg>&quot;);transform:translate(${(hash(Math.floor(T * 24)) * 40 - 20).toFixed(0)}px,${(hash(Math.floor(T * 24) + 7) * 40 - 20).toFixed(0)}px)"></div>`;
    root().innerHTML = html;
  }
  window.PMR = { load, seek, W, H, NAMES, COLORS, get total() { return TOTAL; } };
})();
