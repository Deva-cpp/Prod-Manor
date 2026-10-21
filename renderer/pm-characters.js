// Prod Manor — character library. Every character is built from separable, named parts
// (cut-out ready) as SVG strings. Exposes window.PM, window.PMChar, window.PMDemo.
(function () {
  const INK = '#1A1C3A';
  const OW = 7; // under-stroke width → 3.5u visible outline (≈1% of Junior's height)
  const PAL = {
    junior: { base: '#F38A2D', shade: '#C4601C', skin: '#EDBE98', skinSh: '#C98E6C', hair: '#2F2542', hairSh: '#1E1830', denim: '#3D4374', denimSh: '#2A2F57', phones: '#5A6296', phonesSh: '#3C4372', shoe: '#E2E4EF', shoeSh: '#A4A9C8', bags: '#9C77B0', laptop: '#8E95BC', laptopSh: '#646B94', cream: '#ECE6D6', creamSh: '#B8B09A', lens: '#FFE7A0', eye: '#F7F3EA', mouth: '#5B2533', tongue: '#E0707A', mug: '#E9E6F2', mugSh: '#B3B0CC', mugIn: '#3B3456' },
    null: { base: '#EEF1F8', shade: '#AEBBDD', glow: '#8CC8FF', blush: '#C7D9FF', tag: '#FFFFFF' },
    caller: { base: '#C8233A', shade: '#87152B', dial: '#F2E3C8', dialSh: '#CDB792', hole: '#3A1020', eyeW: '#FFF8EC', mouth: '#3B0D1B', teeth: '#FFF6E6', tongue: '#E35A6C', foot: '#33243F', plug: '#3A3658', prong: '#C9CDE0' },
    twins: { base: '#97E52E', shade: '#5B9F1F', eye: '#F3F6DF', mouth: '#1F2B12', fang: '#FFFFFF' },
    leak: { base: '#D9369E', shade: '#9C1F72', eye: '#FBEFF7', mouth: '#5A1440', ear: '#F3C9AE', earSh: '#C99A80', mug: '#E9E6F2', mugSh: '#B3B0CC', cable: '#8E95BC', tooth: '#FFFBF0' },
    ollie: { base: '#D9AA2A', shade: '#9E7616', skin: '#E9DECF', skinSh: '#BBAA95', hair: '#3B3653', hairSh: '#27233D', shirt: '#F2EBD9', tie: '#2E3266', button: '#7A5A16', shoe: '#3A3658', shoeSh: '#24213E', eye: '#FFFFFF', teeth: '#FFFBF0', box: '#EFE6D2', boxSh: '#C3B596', choc: '#7A4B3A', van: '#F1D9A8', win: '#2E2440' }
  };

  const f = (n) => Math.round(n * 10) / 10;
  const E = (cx, cy, rx, ry) => { ry = ry == null ? rx : ry; return `M${f(cx - rx)},${f(cy)}a${f(rx)},${f(ry)} 0 1,0 ${f(2 * rx)},0a${f(rx)},${f(ry)} 0 1,0 ${f(-2 * rx)},0Z`; };
  const R = (x, y, w, h, r) => { r = Math.min(r || 0, w / 2, h / 2); return `M${f(x + r)},${f(y)}h${f(w - 2 * r)}a${r},${r} 0 0 1 ${r},${r}v${f(h - 2 * r)}a${r},${r} 0 0 1 ${-r},${r}h${f(-(w - 2 * r))}a${r},${r} 0 0 1 ${-r},${-r}v${f(-(h - 2 * r))}a${r},${r} 0 0 1 ${r},${-r}Z`; };
  function tube(x1, y1, x2, y2, w1, w2) {
    const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L, a = w1 / 2, b = w2 / 2;
    return `M${f(x1 + nx * a)},${f(y1 + ny * a)}L${f(x2 + nx * b)},${f(y2 + ny * b)}A${b},${b} 0 0 0 ${f(x2 - nx * b)},${f(y2 - ny * b)}L${f(x1 - nx * a)},${f(y1 - ny * a)}A${a},${a} 0 0 0 ${f(x1 + nx * a)},${f(y1 + ny * a)}Z`;
  }
  function bz(P, t) { const u = 1 - t; return [0, 1].map((j) => u * u * u * P[0][j] + 3 * u * u * t * P[1][j] + 3 * u * t * t * P[2][j] + t * t * t * P[3][j]); }

  function kit(pre) {
    let n = 0;
    const k = { fx: 1 };
    k.id = () => pre + (n++);
    k.ink = (d, w) => `<path d="${d}" fill="${INK}" stroke="${INK}" stroke-width="${w == null ? OW : w}" stroke-linejoin="round"/>`;
    k.fill = (d, c, s, o) => {
      if (!s) return `<path d="${d}" fill="${c}"/>`;
      o = o == null ? 6 : o; const i = k.id();
      return `<clipPath id="${i}"><path d="${d}"/></clipPath><path d="${d}" fill="${s}"/><g clip-path="url(#${i})"><path d="${d}" fill="${c}" transform="translate(${-o * k.fx} ${-o})"/></g>`;
    };
    k.part = (d, c, s, o, w) => k.ink(d, w) + k.fill(d, c, s, o);
    k.grp = (arr) => arr.map((a) => k.ink(a[0], a[4])).join('') + arr.map((a) => k.fill(a[0], a[1], a[2], a[3])).join('');
    k.ln = (d, w, c, extra) => `<path d="${d}" fill="none" stroke="${c || INK}" stroke-width="${w || 5}" stroke-linecap="round" stroke-linejoin="round"${extra || ''}/>`;
    k.iln = (d, w, c) => k.ln(d, w + OW, INK) + k.ln(d, w, c);
    k.clip = (d, inner) => { const i = k.id(); return `<clipPath id="${i}"><path d="${d}"/></clipPath><g clip-path="url(#${i})">${inner}</g>`; };
    return k;
  }
  const txt = (x, y, s, size, extra) => `<text x="${x}" y="${y}" font-family="JetBrains Mono, monospace" font-size="${size}" font-weight="800" fill="${INK}" text-anchor="middle"${extra || ''}>${s}</text>`;

  function coil(k, P, loops, r, w, c) {
    const N = Math.round(loops * 20), pts = [];
    for (let i = 0; i <= N; i++) {
      const t = i / N, a = bz(P, t), b = bz(P, Math.min(1, t + 0.01)), a0 = bz(P, Math.max(0, t - 0.01));
      let tx = b[0] - a0[0], ty = b[1] - a0[1]; const L = Math.hypot(tx, ty) || 1; tx /= L; ty /= L;
      const ph = 2 * Math.PI * loops * t, env = Math.min(1, t * 6, (1 - t) * 6);
      pts.push([a[0] - ty * r * env * Math.sin(ph) + tx * r * 0.85 * env * Math.cos(ph), a[1] + tx * r * env * Math.sin(ph) + ty * r * 0.85 * env * Math.cos(ph)]);
    }
    let s = '';
    for (let i = 0; i < N; i += 10) {
      const seg = pts.slice(i, Math.min(N, i + 10) + 1);
      const d = seg.map((p, j) => (j ? 'L' : 'M') + f(p[0]) + ',' + f(p[1])).join('');
      s += k.ln(d, w + OW, INK) + k.ln(d, w, c);
    }
    return s;
  }

  // ───────────────────────── JUNIOR ─────────────────────────
  function junior(k, o) {
    const C = PAL.junior, e = o.expr || 'neutral', ex = o.explode || 0;
    const P = (name, dx, dy, s) => `<g data-part="${name}" transform="translate(${f(dx * ex * 60)} ${f(dy * ex * 60)})">${s}</g>`;
    let s = '';
    s += P('laptop', -0.9, 0.2, `<g transform="rotate(-8 34 228)">${k.part(R(12, 184, 44, 88, 6), C.laptop, C.laptopSh, 5)}${k.part(E(34, 214, 7), C.base, null, 0, 5)}</g>`);
    s += P('legs', 0, 0.8,
      k.part(R(66, 288, 38, 58, 10), C.denim, C.denimSh, 5) + k.part(R(116, 288, 38, 58, 10), C.denim, C.denimSh, 5) +
      k.part('M54,352C54,338 64,334 86,334C100,334 108,340 108,352C108,358 104,362 98,362L62,362C56,362 54,358 54,352Z', C.shoe, C.shoeSh, 4) +
      k.part('M166,352C166,338 156,334 134,334C120,334 112,340 112,352C112,358 116,362 122,362L158,362C164,362 166,358 166,352Z', C.shoe, C.shoeSh, 4));
    let t = k.part('M44,170C48,154 80,146 110,146C140,146 172,154 176,170L190,282C192,294 184,298 174,298L46,298C36,298 28,294 30,282Z', C.base, C.shade, 10);
    t += k.ln('M34,284L186,284', 3.5);
    t += k.part('M68,236L152,236C156,236 158,240 159,244L166,274L54,274L61,244C62,240 64,236 68,236Z', C.base, C.shade, 4, 5);
    t += k.part('M56,172C56,148 84,138 110,138C136,138 164,148 164,172C150,162 132,158 110,158C88,158 70,162 56,172Z', C.shade, null);
    t += k.iln('M97,166L93,206', 3.5, C.cream) + k.iln('M123,166L127,206', 3.5, C.cream);
    t += k.iln('M62,172Q110,212 158,172', 8, C.phones) + k.part(E(60, 172, 15, 18), C.phones, C.phonesSh, 4) + k.part(E(160, 172, 15, 18), C.phones, C.phonesSh, 4);
    s += P('torso', 0, 0.25, t);
    // viewer-left arm: laptop clamp + empty mug hooked on a finger
    let aL = k.part(tube(52, 180, 40, 258, 34, 26), C.base, C.shade, 6);
    aL += `<g transform="rotate(10 40 280)">${k.iln(E(40, 287, 7, 9), 3.5, C.mug)}${k.part(R(8, 276, 28, 28, 5), C.mug, C.mugSh, 4, 5)}${k.part(E(22, 278, 14, 4), C.mugIn, null, 0, 4)}</g>`;
    aL += k.part(E(40, 268, 11, 11), C.skin, C.skinSh, 3, 5);
    s += P('armL', -1, 0.15, aL);
    // viewer-right arm: console.log flashlight
    let aR = k.part(tube(170, 180, 206, 228, 34, 26), C.base, C.shade, 6);
    aR += `<g transform="rotate(8 212 234)">${k.part(R(200, 222, 66, 24, 6), C.cream, C.creamSh, 4)}${k.part(R(212, 226, 50, 16, 2), '#2A2D52', null, 0, 3)}<text x="237" y="236.6" font-family="JetBrains Mono, monospace" font-size="7.2" font-weight="800" fill="${C.cream}" text-anchor="middle">console.log</text>${k.part('M264,220L282,212L282,256L264,248Z', C.phones, C.phonesSh, 3)}${k.part(E(283, 234, 4.5, 22), C.lens, null, 0, 5)}</g>`;
    aR += k.part(E(210, 234, 12, 12), C.skin, C.skinSh, 3, 5);
    s += P('armR', 1, 0.15, aR);
    let h = k.part(E(52, 106, 11, 13), C.skin, C.skinSh, 3) + k.part(E(168, 106, 11, 13), C.skin, C.skinSh, 3);
    h += k.part(E(110, 100, 60, 57), C.skin, C.skinSh, 8);
    h += k.grp([['M100,40C94,20 108,4 130,6C118,12 114,24 122,40Z', C.hair, C.hairSh, 4], ['M50,102C44,58 74,34 110,34C148,34 176,58 170,102C162,86 152,78 140,80L130,68L120,82L106,68L94,84C82,78 64,86 50,102Z', C.hair, C.hairSh, 5]]);
    s += P('head', 0, -0.9, h);
    // face
    let fc = `<path d="M74,122Q88,136 102,122Q88,130 74,122Z" fill="${C.bags}"/><path d="M118,122Q132,136 146,122Q132,130 118,122Z" fill="${C.bags}"/>`;
    if (e === 'happy') fc += k.ln('M75,110Q88,96 101,110', 5) + k.ln('M119,110Q132,96 145,110', 5);
    else if (o.blink) fc += k.ln('M74,108Q88,114 102,108', 5) + k.ln('M118,108Q132,114 146,108', 5);
    else {
      const sc = e === 'scared', rx = sc ? 16 : 15, ry = sc ? 19 : 17, pr = sc ? 4.5 : 7;
      fc += k.part(E(88, 106, rx, ry), C.eye, null, 0, 5) + k.part(E(132, 106, rx, ry), C.eye, null, 0, 5);
      fc += `<circle cx="89" cy="108" r="${pr}" fill="${INK}"/><circle cx="131" cy="108" r="${pr}" fill="${INK}"/><circle cx="91.6" cy="105" r="2.4" fill="#fff"/><circle cx="133.6" cy="105" r="2.4" fill="#fff"/>`;
    }
    const brows = { neutral: ['M74,90Q84,82 99,84', 'M121,84Q136,82 146,90'], scared: ['M72,84Q82,72 98,74', 'M122,74Q138,72 148,84'], happy: ['M74,84Q86,76 98,80', 'M122,80Q134,76 146,84'] }[e] || ['M74,90Q84,82 99,84', 'M121,84Q136,82 146,90'];
    fc += k.ln(brows[0], 5.5) + k.ln(brows[1], 5.5) + k.ln('M106,121Q111,127 115,120', 4);
    if (e === 'happy') fc += k.part('M94,134Q110,138 128,133Q124,154 110,154Q96,154 94,134Z', C.mouth, null, 0, 5) + `<ellipse cx="111" cy="148" rx="7" ry="3.5" fill="${C.tongue}"/>`;
    else if (e === 'scared') fc += k.part('M98,136Q110,130 122,136Q124,150 110,152Q96,150 98,136Z', C.mouth, null, 0, 5) + `<path d="M100,138Q110,134 120,138L120,141Q110,138 100,141Z" fill="#fff"/>`;
    else fc += k.ln('M96,140Q102,136 108,140Q114,144 122,139', 4.5);
    s += P('face', 0, -1.6, fc);
    return { x0: 0, y0: 0, w: 292, h: 368, floor: 362, cx: 110, top: 4, under: `<ellipse cx="112" cy="362" rx="84" ry="9" fill="#090A1E" opacity="0.35"/>`, body: s };
  }

  // ───────────────────────── THE NULL ─────────────────────────
  function nul(k, o) {
    const C = PAL.null, e = o.expr || 'neutral';
    const SHEET = 'M100,4C106,4 108,12 112,16C146,22 164,50 164,90C164,150 186,222 196,288C186,284 176,272 166,274C158,276 156,292 146,292C136,292 134,276 124,276C114,276 112,296 100,296C88,296 86,278 76,278C66,278 64,292 54,292C44,292 42,274 34,274C24,274 14,284 4,288C14,222 36,150 36,90C36,50 54,22 88,16C92,12 94,4 100,4Z';
    let eyes;
    if (e === 'happy') eyes = [['M64,106C66,88 90,88 92,106C86,100 70,100 64,106Z', ''], ['M108,106C110,88 134,88 136,106C130,100 114,100 108,106Z', '']];
    else if (o.blink) eyes = [['M64,101Q78,109 92,101Q78,105 64,101Z', ''], ['M108,101Q122,109 136,101Q122,105 108,101Z', '']];
    else if (e === 'scared') eyes = [[E(78, 98, 15, 20), ''], [E(122, 98, 15, 20), '']];
    else eyes = [[E(78, 100, 12, 18), 'rotate(14 78 100)'], [E(122, 100, 12, 18), 'rotate(-14 122 100)']];
    const ep = (fill, extra) => eyes.map((x) => `<path d="${x[0]}"${x[1] ? ` transform="${x[1]}"` : ''} fill="${fill}"${extra || ''}/>`).join('');
    const m = k.id();
    const folds = e === 'scared'
      ? ['M68,150C58,170 74,190 62,212C54,228 68,246 58,266', 'M132,150C142,170 128,190 140,212C148,228 134,246 146,262', 'M100,196C108,214 92,232 100,250C106,264 96,274 100,282']
      : ['M68,150C64,190 60,230 58,266', 'M132,150C138,190 142,228 146,262', 'M100,196C100,226 100,256 100,282'];
    let sheet = k.part(SHEET, C.base, C.shade, 9);
    sheet += folds.map((d) => k.ln(d, 5, C.shade)).join('') + k.ln('M96,20C92,27 88,32 82,36', 4, C.shade) + k.ln('M104,20C108,27 112,32 118,36', 4, C.shade);
    if (e !== 'scared') sheet += `<ellipse cx="62" cy="126" rx="10" ry="5" fill="${C.blush}"/><ellipse cx="138" cy="126" rx="10" ry="5" fill="${C.blush}"/>`;
    let s = `<g transform="rotate(-5 100 296)"><mask id="${m}" maskUnits="userSpaceOnUse" x="-60" y="-60" width="340" height="420"><rect x="-60" y="-60" width="340" height="420" fill="#fff"/>${ep('#000')}</mask>`;
    s += `<g mask="url(#${m})">${sheet}</g>${ep('none', ` stroke="${INK}" stroke-width="4.5" stroke-linejoin="round"`)}`;
    s += `<g data-part="tag" transform="translate(14 236) rotate(-14)">${k.part(R(-24, -12, 48, 24, 3), C.tag, null, 0, 5)}${k.ln('M-18,-12L-18,12', 2, '#AEBBDD', ' stroke-dasharray="3 3"')}${txt(3, 4.6, 'null', 13)}</g></g>`;
    const b = k.id();
    const under = `<filter id="${b}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="16"/></filter><ellipse cx="100" cy="334" rx="66" ry="8" fill="#090A1E" opacity="0.28"/><ellipse cx="96" cy="158" rx="100" ry="146" fill="${C.glow}" opacity="0.32" filter="url(#${b})"/>`;
    return { x0: -24, y0: -6, w: 236, h: 346, floor: 334, cx: 100, top: 4, under, body: s };
  }

  // ───────────────────────── THE CALLER ─────────────────────────
  function caller(k, o) {
    const C = PAL.caller, e = o.expr || 'neutral', dial = o.dial || 0, spin = o.spin || 0, rv = o.recv || 0;
    let s = coil(k, [[212, 186], [262, 222], [306, 172], [284, 112]], 7, 9, 6, C.base);
    const ang = Math.atan2(112 - 172, 284 - 306) * 180 / Math.PI + 90;
    s += `<g data-part="plug" transform="translate(284 112) rotate(${f(ang)})">${k.iln('M-4,-6L-4,-17', 3, C.prong)}${k.iln('M4,-6L4,-17', 3, C.prong)}${k.part(R(-9, -6, 18, 22, 4), C.plug, null, 0, 5)}</g>`;
    s += coil(k, [[50, 150], [24, 162], [-6, 140], [-20, 104]], 3.5, 6, 5, C.base);
    s += k.part('M70,84C64,66 70,50 86,44C94,52 98,66 98,78Z', C.base, C.shade, 4) + k.part('M182,84C188,66 182,50 166,44C158,52 154,66 154,78Z', C.base, C.shade, 4);
    s += k.part(E(74, 208, 20, 9), C.foot, null) + k.part(E(178, 208, 20, 9), C.foot, null);
    s += k.part('M44,206C34,206 32,196 35,188L62,92C66,80 76,72 90,72L162,72C176,72 186,80 190,92L217,188C220,196 218,206 208,206Z', C.base, C.shade, 10);
    // dial face
    s += k.part(E(126, 116, 46), C.dial, C.dialSh, 4, 6);
    let holes = '';
    for (let i = 0; i < 10; i++) { const a = (90 + i * 33.33) * Math.PI / 180; holes += `<circle cx="${f(126 + 33 * Math.cos(a))}" cy="${f(116 + 33 * Math.sin(a))}" r="7.4" fill="${C.hole}" stroke="${INK}" stroke-width="2.5"/>`; }
    s += `<g data-part="dial" transform="rotate(${f(dial)} 126 116)">${holes}</g><path d="M147,152L158,163L150,164Z" fill="${INK}"/>`;
    s += k.part(E(126, 116, 20), C.eyeW, null, 0, 5);
    if (e === 'scared') s += `<circle cx="126" cy="116" r="4.5" fill="${INK}"/>`;
    else {
      let sp = ''; for (let i = 0; i <= 72; i++) { const th = i / 72 * 6 * Math.PI, rr = 1.5 + 15 * th / (6 * Math.PI); sp += (i ? 'L' : 'M') + f(126 + rr * Math.cos(th)) + ',' + f(116 + rr * Math.sin(th)); }
      s += `<g data-part="spiral" transform="rotate(${f(spin)} 126 116)">${k.ln(sp, 3)}</g><circle cx="126" cy="116" r="2.8" fill="${C.base}"/>`;
    }
    // grin
    if (e === 'scared') s += k.part('M96,172Q106,166 116,172Q126,178 136,172Q146,166 156,172Q150,190 126,190Q102,190 96,172Z', C.mouth, null, 0, 5);
    else {
      const M = e === 'happy' ? 'M62,164Q126,176 190,164Q182,204 126,204Q70,204 62,164Z' : 'M68,166Q126,176 184,166Q176,200 126,200Q76,200 68,166Z';
      s += k.ink(M, 6) + `<path d="${M}" fill="${C.mouth}"/>` + k.clip(M, `<rect x="56" y="150" width="140" height="31" fill="${C.teeth}"/>${[86, 106, 126, 146, 166].map((x) => k.ln(`M${x},160L${x},181`, 2.5)).join('')}${k.ln('M56,181L196,181', 3)}<ellipse cx="126" cy="${e === 'happy' ? 202 : 198}" rx="26" ry="10" fill="${C.tongue}"/>`) + k.ln(M, 4);
    }
    s += `<g data-part="receiver" transform="translate(6 62) rotate(${f(-38 + rv)})">${k.part('M-58,-4C-58,-14 -48,-18 -40,-12L40,-12C48,-18 58,-14 58,-4L58,14C58,22 34,22 34,12L34,6L-34,6L-34,12C-34,22 -58,22 -58,14Z', C.base, C.shade, 5)}</g>`;
    return { x0: -44, y0: 8, w: 368, h: 214, floor: 216, cx: 126, top: 40, under: `<ellipse cx="128" cy="215" rx="104" ry="9" fill="#090A1E" opacity="0.35"/>`, body: s };
  }

  // ───────────────────────── FORK & JOIN ─────────────────────────
  function gremlin(k, kind, e, blink) {
    const C = PAL.twins, G = C.base, GS = C.shade;
    let s = k.part('M20,74C6,64 -6,60 -14,60C-8,74 2,90 16,96Z', G, GS, 3) + k.part('M100,74C114,64 126,60 134,60C128,74 118,90 104,96Z', G, GS, 3);
    s += k.grp([[tube(44, 128, 40, 146, 16, 16), G, GS, 3], [E(37, 148, 12, 6), G, GS, 3], [tube(76, 128, 80, 146, 16, 16), G, GS, 3], [E(83, 148, 12, 6), G, GS, 3]]);
    s += kind === 'fork'
      ? k.iln('M60,42Q57,30 60,20', 4.5, G) + k.iln('M48,2L48,10Q48,20 60,20Q72,20 72,10L72,2', 4.5, G)
      : k.iln('M60,42Q57,32 60,21', 4.5, G) + k.iln(E(53, 12, 8.5), 4, G) + k.iln(E(67, 12, 8.5), 4, G) + k.iln('M59.5,6.5A8.5,8.5 0 0 1 59.5,17.5', 4, G);
    s += k.grp([[tube(18, 104, -2, 80, 12, 10), G, GS, 2], [E(-4, 76, 7.5), G, GS, 2]]);
    s += k.part('M60,40C92,40 108,66 108,96C108,124 94,138 60,138C26,138 12,124 12,96C12,66 28,40 60,40Z', G, GS, 8);
    s += k.grp([[tube(100, 106, 120, 98, 12, 10), G, GS, 2], [E(123, 97, 7.5), G, GS, 2]]);
    if (e === 'happy') s += k.ln('M32,88Q44,74 56,88', 5) + k.ln('M64,88Q76,74 88,88', 5);
    else if (blink) s += k.ln('M32,86Q44,92 56,86', 5) + k.ln('M64,86Q76,92 88,86', 5);
    else {
      const sc = e === 'scared', ry = sc ? 17 : 15, pr = sc ? 3.5 : 5.5, px = sc ? 0 : 4;
      [44, 76].forEach((x) => {
        const S = E(x, 84, 13, ry);
        s += k.part(S, C.eye, null, 0, 5) + `<circle cx="${x + px}" cy="${sc ? 84 : 88}" r="${pr}" fill="${INK}"/><circle cx="${x + px + 2}" cy="${sc ? 82 : 86}" r="1.8" fill="#fff"/>`;
        if (!sc) s += k.clip(S, `<path d="M${x - 16},60L${x + 16},60L${x + 16},${77}Q${x},${82} ${x - 16},${79}Z" fill="${G}"/>`) + k.ln(`M${x - 13},79Q${x},${82} ${x + 13},77`, 3.5);
      });
    }
    if (e === 'scared') s += k.part('M44,112Q52,106 60,112Q68,118 76,112Q74,124 60,124Q46,124 44,112Z', C.mouth, null, 0, 5);
    else {
      const M = e === 'happy' ? 'M30,100Q60,112 90,98Q84,132 58,130Q36,128 30,100Z' : 'M34,104Q60,114 88,100Q80,126 58,124Q40,122 34,104Z';
      s += k.part(M, C.mouth, null, 0, 5) + `<path d="M44,107L48,116L52,108Z" fill="${C.fang}"/><path d="M68,106L72,115L76,104Z" fill="${C.fang}"/>`;
    }
    return s;
  }
  function twins(k, o) {
    const lean = o.lean == null ? 5 : o.lean, e = o.expr || 'neutral';
    let s = `<g data-part="fork" transform="rotate(${f(lean)} 60 150)">${gremlin(k, 'fork', e, o.blink)}</g>`;
    k.fx = -1;
    s += `<g data-part="join" transform="translate(240 0) scale(-1 1) rotate(${f(lean)} 60 150)">${gremlin(k, 'join', e, o.blink)}</g>`;
    k.fx = 1;
    return { x0: -24, y0: -6, w: 288, h: 162, floor: 154, cx: 120, top: 2, under: `<ellipse cx="62" cy="154" rx="50" ry="6" fill="#090A1E" opacity="0.35"/><ellipse cx="178" cy="154" rx="50" ry="6" fill="#090A1E" opacity="0.35"/>`, body: s };
  }

  // ───────────────────────── THE LEAK ─────────────────────────
  function leak(k, o) {
    const C = PAL.leak, e = o.expr || 'neutral';
    const BODY = 'M34,222C18,222 12,208 24,200C30,156 42,104 74,70C98,44 122,34 144,34C180,34 208,54 224,92C238,126 240,166 244,198C258,204 256,222 238,222C224,228 206,218 190,224C174,230 154,220 134,226C114,232 94,220 74,226C58,230 44,220 34,222Z';
    const EAR = 'M0,-12C10,-12 14,-4 13,3C12,9 7,10 6,15C5,20 -1,21 -3,16C-6,8 -9,-12 0,-12Z';
    let s = `<g transform="rotate(-20 92 152)">${k.iln(E(108, 152, 6, 8), 3.5, C.mug)}${k.part(R(78, 138, 28, 30, 5), C.mug, C.mugSh, 3, 5)}</g>`;
    s += k.iln('M150,200C128,180 172,160 150,138C138,126 160,112 178,120', 4, C.cable) + `<g transform="translate(182 118) rotate(-20)">${k.part(R(-6, -7, 14, 14, 2), C.cable, null, 0, 4)}</g>`;
    [[118, 156, -20, 1.1], [190, 132, 25, 1], [104, 196, 10, 1], [204, 182, -30, 1.1], [164, 176, 40, 0.9], [68, 198, -10, 1], [212, 112, 15, 0.9], [136, 206, 0, 0.9], [84, 120, -35, 0.85]].forEach((a) => {
      s += `<g transform="translate(${a[0]} ${a[1]}) rotate(${a[2]}) scale(${a[3]})">${k.part(EAR, C.ear, C.earSh, 2, 5)}${k.ln('M1,-5C6,-5 7,1 3,4', 2.5)}</g>`;
    });
    s += `<g opacity="0.8">${k.fill(BODY, C.base, C.shade, 11)}</g>${k.ln(BODY, 7)}`;
    s += k.ln('M64,116C70,92 84,72 104,58', 9, '#fff', ' opacity="0.5"') + `<circle cx="58" cy="134" r="4.5" fill="#fff" opacity="0.5"/>`;
    if (e === 'happy') s += k.ln('M110,90Q126,74 142,90', 5) + k.ln('M158,92Q170,80 182,92', 5);
    else if (o.blink) s += k.ln('M110,88Q126,96 142,88', 5) + k.ln('M158,92Q170,98 182,92', 5);
    else {
      const sc = e === 'scared', g = sc ? 2 : 0;
      s += k.part(E(126, 86, 17 + g, 19 + g), C.eye, null, 0, 5) + k.part(E(170, 90, 13 + g, 15 + g), C.eye, null, 0, 5);
      s += sc ? `<circle cx="126" cy="86" r="3.5" fill="${INK}"/><circle cx="170" cy="90" r="3" fill="${INK}"/>`
        : `<circle cx="130" cy="91" r="7" fill="${INK}"/><circle cx="166" cy="94" r="6" fill="${INK}"/><circle cx="132.5" cy="88" r="2.3" fill="#fff"/><circle cx="168.5" cy="91.5" r="2" fill="#fff"/>`;
    }
    if (e === 'happy') s += k.part('M126,122Q148,132 172,120Q166,146 148,146Q130,146 126,122Z', C.mouth, null, 0, 5) + k.part(R(142, 126, 11, 12, 3), C.tooth, null, 0, 4);
    else if (e === 'scared') s += k.part(E(148, 134, 10, 9), C.mouth, null, 0, 5) + k.part(R(143, 125, 10, 10, 3), C.tooth, null, 0, 4);
    else s += k.part(R(141, 130, 11, 12, 3), C.tooth, null, 0, 4) + k.ln('M128,124Q148,138 170,122', 5);
    s += k.part(E(262, 216, 7, 6), C.base, C.shade, 2);
    return { x0: 0, y0: 24, w: 274, h: 212, floor: 224, cx: 134, top: 34, under: `<ellipse cx="136" cy="224" rx="122" ry="9" fill="#090A1E" opacity="0.35"/>`, body: s };
  }

  // ───────────────────────── OLLIE ONE-OFF ─────────────────────────
  function ollie(k, o) {
    const C = PAL.ollie, e = o.expr || 'neutral';
    let s = k.grp([[tube(134, 140, 146, 200, 16, 14), C.base, C.shade, 4], [tube(146, 200, 152, 256, 14, 12), C.base, C.shade, 4]]) + k.part(E(153, 263, 9, 11), C.skin, C.skinSh, 3);
    s += k.grp([[tube(88, 262, 84, 424, 20, 18), C.base, C.shade, 5], [tube(112, 262, 128, 348, 20, 18), C.base, C.shade, 5], [tube(128, 348, 136, 416, 18, 16), C.base, C.shade, 5]]);
    s += k.part('M46,438C54,430 70,420 86,420C96,420 100,428 98,436C97,440 94,442 88,442L50,442C46,442 44,440 46,438Z', C.shoe, C.shoeSh, 3);
    s += k.part('M122,412C134,408 152,414 168,426C172,430 170,435 164,435L130,430C121,428 117,418 122,412Z', C.shoe, C.shoeSh, 3);
    s += k.part(R(92, 100, 16, 32, 5), C.skin, C.skinSh, 3);
    s += k.part('M64,132C70,126 86,124 100,124C114,124 130,126 136,132L128,232C127,242 130,252 132,262L100,262L100,270L68,270C70,256 72,242 72,232Z', C.base, C.shade, 8);
    s += k.part('M86,125L100,172L114,125Z', C.shirt, null, 0, 5) + k.part('M96.5,134L103.5,134L106,160L100,168L94,160Z', C.tie, null, 0, 4);
    s += k.part('M84,126L99,172L76,152L82,142L76,134Z', C.base, C.shade, 3, 5) + k.part('M116,126L101,172L124,150L118,142L124,134Z', C.base, C.shade, 3, 5);
    s += k.ln('M100,172L100,262', 3.5) + k.ln('M95,191L105,189', 3);
    s += k.part(E(100, 206, 5), C.button, null, 0, 4) + k.part(E(100, 234, 5), C.button, null, 0, 4);
    s += `<g data-part="pin">${k.part(E(86, 148, 9), C.shirt, null, 0, 5)}${txt(86, 152.5, '0', 12)}</g>`;
    s += k.part(E(66, 68, 7, 10), C.skin, C.skinSh, 2) + k.part(E(134, 66, 7, 10), C.skin, C.skinSh, 2);
    s += k.part(E(100, 62, 34, 46), C.skin, C.skinSh, 7);
    s += k.part('M64,60C62,30 80,14 102,14C124,14 138,30 136,56C130,42 120,34 108,34C112,40 110,46 104,48C98,38 86,34 78,40C72,44 66,52 64,60Z', C.hair, C.hairSh, 4);
    // eyes: the right one sits 7u higher — on purpose
    if (e === 'happy') s += k.ln('M79,66Q86,58 93,66', 4.5) + k.ln('M109,59Q116,51 123,59', 4.5);
    else if (o.blink) s += k.ln('M79,64Q86,68 93,64', 4.5) + k.ln('M109,57Q116,61 123,57', 4.5);
    else {
      const sc = e === 'scared', ry = sc ? 10 : 8.5, pr = sc ? 2.4 : 3.6;
      s += k.part(E(86, 64, 7.5, ry), C.eye, null, 0, 4) + k.part(E(116, 57, 7.5, ry), C.eye, null, 0, 4) + `<circle cx="87" cy="65" r="${pr}" fill="${INK}"/><circle cx="117" cy="58" r="${pr}" fill="${INK}"/>`;
    }
    const by = e === 'scared' ? -5 : 0;
    s += k.ln(`M77,${51 + by}Q86,${45 + by} 95,${49 + by}`, 4.5) + k.ln(`M107,${44 + by}Q116,${38 + by} 125,${42 + by}`, 4.5) + k.ln('M101,66Q105,76 99,79', 4);
    const M = 'M68,84Q100,94 134,80Q126,108 100,108Q76,108 68,84Z';
    s += k.ink(M, 5) + `<path d="${M}" fill="${C.teeth}"/>` + k.clip(M, [80, 90, 100, 110, 120].map((x) => k.ln(`M${x},80L${x},112`, 2.2)).join('')) + k.ln(M, 3) + k.ln('M64,79Q66,84 70,86', 3.5) + k.ln('M138,76Q136,81 132,83', 3.5);
    // front arm + donut box
    s += k.grp([[tube(66, 138, 48, 196, 16, 14), C.base, C.shade, 4], [tube(48, 196, 28, 222, 14, 12), C.base, C.shade, 4]]) + k.part(E(26, 226, 12, 7), C.skin, C.skinSh, 2);
    let box = k.part('M-18,196L60,196L68,186L-8,186Z', C.box, null, 0, 5) + k.part(R(-18, 196, 78, 30, 3), C.box, C.boxSh, 4) + k.part(R(-10, 201, 62, 18, 5), C.win, null, 0, 4);
    [[6, C.choc], [26, C.van], [46, C.choc]].forEach((d) => { box += k.part(E(d[0], 211, 9, 6.5), d[1], null, 0, 3) + `<ellipse cx="${d[0]}" cy="211" rx="2.8" ry="2" fill="${C.win}"/>`; });
    s += `<g data-part="donuts">${box}</g>`;
    return { x0: 0, y0: 6, w: 204, h: 450, floor: 446, cx: 112, top: 18, under: `<ellipse cx="104" cy="444" rx="64" ry="8" fill="#090A1E" opacity="0.35"/>`, body: `<g transform="rotate(7 92 440)">${s}</g>` };
  }

  const CH = { junior, null: nul, caller, twins, leak, ollie };
  const SEEDS = { junior: 3, null: 7, caller: 11, twins: 5, leak: 9, ollie: 2 };
  const DIMS = {};
  function dims(who) { if (!DIMS[who]) { const r = CH[who](kit('d_'), {}); DIMS[who] = { x0: r.x0, y0: r.y0, w: r.w, h: r.h, floor: r.floor, cx: r.cx, top: r.top }; } return DIMS[who]; }
  function defs(pre, seed) {
    return `<filter id="${pre}w" x="-6%" y="-6%" width="112%" height="112%"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="${seed}"/><feDisplacementMap in="SourceGraphic" scale="4" xChannelSelector="R" yChannelSelector="G"/></filter>` +
      `<filter id="${pre}s" x="-10%" y="-10%" width="120%" height="120%" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 4 -1.6"/></filter>`;
  }
  function svg(who, opts, pre, scale) {
    opts = opts || {}; scale = scale || 1;
    const r = CH[who](kit(pre), opts);
    const wob = opts.wobble !== false;
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${r.x0} ${r.y0} ${r.w} ${r.h}" width="${f(r.w * scale)}" height="${f(r.h * scale)}" style="display:block;overflow:visible"><defs>${defs(pre, SEEDS[who])}</defs><g${opts.silhouette ? ` filter="url(#${pre}s)"` : ''}>${r.under || ''}<g${wob ? ` filter="url(#${pre}w)"` : ''}>${r.body}</g></g></svg>`;
  }

  // Style-guide demo shapes
  function demo(kind, pre, size) {
    const k = kit(pre), B = 'M60,12C92,12 108,38 108,66C108,96 90,110 60,110C30,110 12,96 12,66C12,38 28,12 60,12Z';
    let b = '', wob = false;
    const map = {
      'line-ok': () => { b = k.part(B, '#F38A2D', '#C4601C', 8); wob = true; },
      'line-black': () => { b = `<path d="${B}" fill="#F38A2D" stroke="#000" stroke-width="2.5"/>`; },
      'line-thin': () => { b = k.fill(B, '#F38A2D', '#C4601C', 8) + `<path d="${B}" fill="none" stroke="${INK}" stroke-width="1"/>`; },
      'shade-1': () => { b = `<path d="${B}" fill="#97E52E"/>`; },
      'shade-2': () => { b = k.fill(B, '#97E52E', '#5B9F1F', 9); },
      'shade-3': () => { b = k.part(B, '#97E52E', '#5B9F1F', 9); wob = true; },
      'shade-bad': () => { const g = k.id(); b = `<radialGradient id="${g}" cx="35%" cy="30%"><stop offset="0" stop-color="#E8FFB8"/><stop offset="1" stop-color="#3E7A12"/></radialGradient><path d="${B}" fill="url(#${g})" stroke="${INK}" stroke-width="7"/>`; },
      'g-junior': () => { b = k.part('M30,40C30,28 44,22 60,22C76,22 90,28 90,40L100,98C101,104 96,108 90,108L30,108C24,108 19,104 20,98Z', '#F38A2D', '#C4601C', 7); },
      'g-null': () => { b = k.part('M60,10C82,10 90,30 90,50C90,74 100,92 108,108L12,108C20,92 30,74 30,50C30,30 38,10 60,10Z', '#EEF1F8', '#AEBBDD', 7); },
      'g-caller': () => { b = k.part('M20,104L40,40L80,40L100,104Z', '#C8233A', '#87152B', 7) + k.part(E(60, 72, 20), '#F2E3C8', null); },
      'g-twins': () => { b = k.part(E(36, 70, 24), '#97E52E', '#5B9F1F', 5) + k.part(E(84, 70, 24), '#97E52E', '#5B9F1F', 5); },
      'g-leak': () => { b = `<g opacity="0.8">${k.fill('M10,104C10,66 30,30 60,30C90,30 110,66 110,104Z', '#D9369E', '#9C1F72', 7)}</g>` + k.ln('M10,104C10,66 30,30 60,30C90,30 110,66 110,104Z', 7); },
      'g-ollie': () => { b = `<g transform="rotate(7 60 112)">${k.part(R(48, 6, 24, 106, 5), '#D9AA2A', '#9E7616', 5)}</g>`; }
    };
    (map[kind] || map['line-ok'])();
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="${size}" height="${size}" style="display:block;overflow:visible"><defs>${defs(pre, 4)}</defs><g${wob ? ` filter="url(#${pre}w)"` : ''}>${b}</g></svg>`;
  }

  const bool = (v) => v === true || v === 'true';
  const uid = () => 'p' + Math.random().toString(36).slice(2, 7) + '_';
  function PMChar(p) {
    const ref = React.useRef(null); if (!ref.current) ref.current = uid();
    const who = CH[p.who] ? p.who : 'junior';
    const opts = { expr: p.expr || 'neutral', blink: bool(p.blink), dial: +p.dial || 0, spin: +p.spin || 0, recv: +p.recv || 0, lean: p.lean == null ? undefined : +p.lean, explode: +p.explode || 0, silhouette: bool(p.silhouette), wobble: !(p.wobble === false || p.wobble === 'false') };
    const d = dims(who);
    const sc = p.scale != null ? +p.scale : p.height != null ? +p.height / d.h : 1;
    const key = who + JSON.stringify(opts) + sc;
    const html = React.useMemo(() => svg(who, opts, ref.current, sc), [key]);
    return React.createElement('div', { style: Object.assign({ display: 'block', lineHeight: 0, width: f(d.w * sc), height: f(d.h * sc) }, p.style || {}), dangerouslySetInnerHTML: { __html: html } });
  }
  function PMDemo(p) {
    const ref = React.useRef(null); if (!ref.current) ref.current = uid();
    const size = +p.size || 120;
    const html = React.useMemo(() => demo(p.kind, ref.current, size), [p.kind, size]);
    return React.createElement('div', { style: { display: 'block', lineHeight: 0, width: size, height: size }, dangerouslySetInnerHTML: { __html: html } });
  }

  window.PM = { INK, PAL, svg, dims, kit };
  window.PMChar = PMChar;
  window.PMDemo = PMDemo;
  if (typeof module !== 'undefined') module.exports = { PMChar, PMDemo };
})();
