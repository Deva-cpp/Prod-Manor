# Prod Manor — Style Guide & Animation Rules

The approved visual source is [`design/Prod Manor - Style Guide.html`](../design/Prod%20Manor%20-%20Style%20Guide.html) (open it in a browser). This file is the text version of its rules, plus the animation rules the renderer follows. The cast library `renderer/pm-characters.js` is the same one the style guide was approved with. With no animation applied, it draws every character byte-for-byte as approved.

## 1. Line
- Colour deep navy **#1A1C3A**, never pure black.
- Weight is 1% of the character's height. It scales with the character, not the screen.
- Hand-drawn wobble on every line, props included. Lines breathe; they never look ruled.
- Round caps and round corners. Limbs merge into one outline with no seams inside a sleeve.
- Interior lines (brows, folds, seams) at about 70% of the outline weight.

## 2. Light & shadow
- One light: the moon, upper-left.
- One shadow tone per colour, cut as a crescent on the lower-right edge (about 8% of the shape's width).
- Flat fills only: no gradients, rim lights or second highlight tone.
- Two exceptions: the Null's cold glow, and the Leak's 80% translucency plus one gloss streak.
- Paper grain sits over the finished frame, never inside a character.

## 3. Palette
The manor is cold: navy and violet. Each character owns exactly one accent, used nowhere else. Junior's orange is the only warm colour in the house.

| Manor | Hex |
|---|---|
| Ink | #1A1C3A |
| Blackout | #0B0C1F |
| Hallway wall | #2A2E62 |
| Wainscot | #22265A |
| Violet shadow | #3B336E |
| Moonlight | #C9D3F4 |
| Flashlight | #FFE7A0 |

| Character | Base / shadow |
|---|---|
| Junior · hoodie orange | #F38A2D / #C4601C |
| The Null · sheet white | #EEF1F8 / #AEBBDD · glow #8CC8FF |
| The Caller · blood red | #C8233A / #87152B |
| Fork & Join · acid green | #97E52E / #5B9F1F |
| The Leak · magenta (80%) | #D9369E / #9C1F72 |
| Ollie · mustard suit | #D9AA2A / #9E7616 |

## 4. Shape language
One base shape per character, then one exaggerated feature. Soft and round reads safe. Tilted, mirrored or spreading reads wrong, and that wrongness is the bug.
- **Junior**: soft pear, slouched, swallowed by the hoodie. Exaggerate the hoodie, eye bags and the one tuft.
- **The Null**: drooping bell tilted 5°. Eye holes are real holes; emotion lives in the hole shapes and fabric folds.
- **The Caller**: trapezoid around a circle. Everything spirals. Never hangs up.
- **Fork & Join**: two mirrored gumdrops. Symmetry is the joke; always posed as reflections.
- **The Leak**: puddle-dome. Spreads, never stands. Swallowed objects float inside.
- **Ollie One-Off**: tall rectangle tilted 7°. Everything is one step off.

## 5. Silhouette test
Every character must be nameable as a solid black silhouette at Reel-thumbnail size.

## 6. Built for cut-out
Rig-ready layers with clean overlaps. Mouths and eyes are swap sets, not redraws.
- Head: hair and tuft as one piece
- Face: eye, brow and mouth swaps
- Arms: sleeve and hand, pivot at the shoulder
- Props ride the hand they're held in (Junior's laptop, mug and flashlight; Ollie's donut box)

## 7. Type
- **Griffy**: titles and names, in the character's accent with a 4–8 px ink drop. Never body copy.
- **JetBrains Mono**: on-screen code, timestamps, prop labels, the Null's tag.
- **DM Sans**: captions and explainer copy. Bold, 1–2 lines, centre-safe.

## 8. Dos & don'ts
- **Do:** keep every character nameable as a silhouette. Hide the bug joke in the design. Push one feature hard. Make eyes big enough to act. Build in separable parts.
- **Don't:** use pure black, gradients or a second highlight. Draw hair strands or folds that can't be cut out. Borrow another character's accent. Go gory. Set prop text too small to read.

---

## 9. Animation rules (how the renderer acts)

The rig moves the approved parts and never redraws them. Rig channels on every character:

| Channel | Range | What moves |
|---|---|---|
| `armL` / `armR` | degrees raised from rest | Junior's arms at the shoulders (laptop and mug ride the left, flashlight the right; the beam follows), Fork & Join's arms, Ollie's front arm with the donut box and his back arm |
| `tilt` | degrees | Junior's head + face at the neck, Ollie's head, the Null's whole sheet (others: whole-body lean) |
| `lookX` / `lookY` | −1…1 | pupils (Junior, twins, Leak, Ollie), the Caller's spiral eye, the Null's eye holes |
| `brow` | −1…1 | Junior's and Ollie's brows |
| `talk` | 0…1 | mouth swap: open/close on every mouth; the Null's eye holes squash instead (he has no mouth) |

**Automatic acting, always on:**
- Breathing and idles (Junior's squash, the Null's float, the Caller's spinning eye, the twins' lean, the Leak's wobble, Ollie's sway), plus blinks.
- Eye saccades: hold a gaze, then dart. Characters look at each other.
- **Lip-sync:** the speaker's mouth flaps in a syllable rhythm and their head bobs while the bubble types out. Listeners turn their eyes to the speaker.
- Context performances:
  - `pager`: Junior cowers.
  - `code`: everyone looks up at the editor and Junior thinks.
  - `crash`: Junior cowers and a happy monster laughs.
  - `fix`: Junior types, then celebrates when the fix lands, while the monster droops.
  - `outro`: Junior waves.
  - Any `scared` expression trembles with darting eyes.

**Directed gestures** (set by the brain per actor, blended in over 0.3s so nothing pops): wave, point, shrug, celebrate, cower, facepalm, think, nod, shake_head, type, beckon, dance, laugh, gasp, tremble, look_up, look_down, look_left, look_right. You can sequence up to 4 per beat:

```json
{"who": "junior", "expr": "scared", "x": 0.25,
 "gestures": [{"g": "gasp", "at": 0.15}, {"g": "point", "at": 0.55}]}
```

**Motion principles:**
- Every rig channel eases in from rest at each cut, so nothing snaps.
- Gestures overshoot slightly, and secondary motion (bob, tremble) rides on top.
- Hands exist only on Junior, Fork & Join and Ollie. The Null, the Caller and the Leak act with head tilt, eyes, mouth and the Caller's receiver.
- Fork & Join mirror each other's gestures, because symmetry is the joke.
- Never let a gesture fight the expression.
