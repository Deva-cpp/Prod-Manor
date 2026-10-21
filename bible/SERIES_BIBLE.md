# PROD MANOR — Series Bible (the producer brain reads this before every pitch)

## The show
Prod Manor is a comedy-horror series of 25–40 second vertical Instagram Reels. Each monster is a programming bug come to life. They wake at 3:00 AM after someone deploys on a Friday. Junior, a sleep-deprived junior developer, has to defeat one with a one-line fix. Every episode teaches exactly ONE real programming concept, correctly, in a way a beginner understands in one viewing and a senior developer finds funny.

Tone: cute-creepy. Spooky, never gory. Funny, never cringe. The monsters are lonely, mischievous or hungry, not evil. Junior is brave but terrified.

## The cast (never invent new characters)
| id | name | bug family | personality | signature gag |
|---|---|---|---|---|
| junior | Junior | the hero | sleep-deprived junior dev, orange hoodie, empty coffee mug, console.log flashlight | whispers "it works on my machine" as a protective spell; it never works |
| null | The Null | null / undefined / missing values | shy, polite, lonely ghost; an empty bedsheet with nothing inside | wants to help, but crashes everything when you call a method on him; "Nobody ever checks on me..." |
| caller | The Caller | recursion, stack overflow, infinite loops, call stack | chatty rotary phone, spiral eye, never hangs up | the call is coming from inside the function; phones stack into a tower until it topples |
| twins | Fork & Join | race conditions, deadlocks, concurrency, async ordering | identical gremlin twins who act at exactly the same moment | both grab the last cookie at once; "After you." "No, after YOU." forever |
| leak | The Leak | memory leaks, unbounded growth, cleanup, performance | adorable magenta slime that grows every time it is fed | eats listeners/intervals; the world slows down as it grows; only says "...more?" |
| ollie | Ollie One-Off | off-by-one, indexing, loop bounds, fenceposts | tall, too-polite neighbor, always exactly one off | knocks on door 11 when you live at 10; clock strikes 13; counts from 0 |

## Episode structure (the beat sheet every pitch must follow)
1. HOOK (0–2s): a `pager` beat (3:00 AM, PROD IS DOWN) or a `title` beat whose `sub` is a scroll-stopping line. The first two seconds decide reach. The hook must create a question, a threat or a relatable pain ("This ghost crashes your app just by existing").
2. TITLE: name the haunting (an episode title in the style "Nobody Checked On Him", "The Call Is Coming From Inside The Function").
3. ENCOUNTER: a `scene` where the monster appears, usually with `light: "flashlight"`. One short line of dialogue.
4. THE BUG: a `code` beat with 2–6 short lines of REAL code that actually has the bug. The `error` must be the real error message (or real symptom) that language produces.
5. CONSEQUENCE: a `crash` beat or a `scene` showing the effect physically (tower of phones, slime filling the hall, twins stuck in a doorway).
6. TURN: the monster's sad/funny line that hints at the fix.
7. THE FIX: a `fix` beat that changes exactly one line (`fix_line`, `after`). The `note` explains WHY in under 14 words.
8. OUTRO: `outro` beat with the one-line lesson, the CTA, and `next_monster` teasing a different monster.

## Funny, interesting, real (every episode, no exceptions)
- REAL WORLD: every bug is one developers actually ship, in a situation they recognise: a Friday deploy, a hotfix during a demo, a login page that crashes for users with no profile photo, a cart total off by one item, a search box that fires 40 requests while you type, a dashboard that gets slower every hour it stays open, two payment clicks that charge twice. Name the real-world symptom (what the user or the on-call dev sees) before showing the code.
- FUNNY: at least two real laughs per episode, not just puns. What works: a spooky voice saying something painfully mundane, Junior's panic being way bigger than the bug, the monster being reasonable and polite about destroying prod, painfully relatable dev pain (Slack pings at 3 AM, "works on my machine", "who approved this PR?" "...you did"). The narrator stays deadpan; never explain the joke.
- INTERESTING: give a senior developer something too. Name the real error, a common wrong fix, or a "wait, really?" detail, but keep it one concept a beginner gets in one viewing.

## Writing rules
- Total 25–40 seconds, 6–9 beats. Every beat dur 1.8–5s.
- Narration: a calm, dry storyteller voice. Max 16 words per beat. Not on every beat (3–5 beats). Never read the code aloud character by character.
- Dialogue bubbles: max 9 words each, max 2 per beat. Characters speak in character.
- Every line is VOICED, horror-comedy style, so write for the ear: deep, clear, deadpan horror-trailer narrator, Junior's simple, scared young boy's voice, The Null's tiny echoing whisper, The Caller down a crackly phone line where each word echoes itself, Fork & Join speaking in eerie unison, The Leak's slow gloopy rumble, Ollie's slow too-polite butler warble. The joke lands when a spooky voice says something mundane ("...more?", "Room four, I presume?") or Junior panics about something tiny. Use punctuation for delivery ("...", "?!", short. clipped. words.). Write words, not symbols: "three A M", "equals equals", never "===" or "3AM". Dialogue and narration in the same beat play one after another, so keep a beat with both to about 20 words in total.
- Code: max 6 lines, each line max 34 characters, real syntax, runnable. Prefer JavaScript or Python; occasionally Java, Go or TypeScript. Name things plainly (user, items, count).
- The fix must be the correct, idiomatic fix — no hand-waving. If the honest answer is "it depends", pick a simpler concept.
- No real brands, no real people, no copyrighted characters. No emoji inside beats (captions are fine).
- Captions: first line is a hook sentence, then 1–2 lines that teach the concept, then a comment-bait question. 300–600 characters. 6–10 hashtags, mixing big (#coding #programming) and niche (#javascript #python #webdev #codinghumor).
- `cover_text`: 2–3 words, uppercase, readable as a thumbnail.

## Beat schema (only these fields render)
Common fields on any beat: type, dur, narration, sfx (list from: pager, ring, crash, ding, whoosh, thud, creak, heartbeat, slurp, glitch), on_screen (big yellow text), shake (bool), camera {zoom_from, zoom_to, focus_x}.
- pager: time, text, sub
- title: text, sub, kicker, monster
- scene: bg (hallway | bedroom | server_room), light (dark | flashlight | flicker | red | normal), actors[], say[{who, text}]
- code: lang, file, lines[], highlight[line numbers], error, actors[]
- crash: title, text, actors[]
- fix: lang, file, lines[] (the buggy version), fix_line (1-based), after (the fixed line), note, actors[]
- outro: lesson, cta, kicker, next_monster

Actor: {who, expr (neutral | happy | scared), x (0–1 across the screen), scale (0.5–1.6), flip, action, to {x, scale}, expr_to, expr_at, copies (caller only, tower size), opacity, z}
Gestures (hands, face and head acting — use them; still characters look dead):
  gesture: one of wave, point, shrug, celebrate, cower, facepalm, think, nod, shake_head, type, beckon, dance, laugh, gasp, tremble, look_up, look_down, look_left, look_right
  gesture_at: 0–0.95, when in the beat it starts (default 0)
  gestures: up to 4 timed changes in one beat, e.g. [{"g": "think", "at": 0}, {"g": "point", "at": 0.5}]
Actions: idle, enter_left, enter_right, exit_left, exit_right, shake, hop, grow, shrink, pop_in, fade_in, fade_out, defeated, peek, spin (caller dial), float, stack (caller: copies build into a tower; use with copies 3–5).
Junior faces right, so put him on the left (x 0.2–0.35) with the monster on the right (x 0.65–0.8). Use `flashlight` when Junior and a monster share a scene.

## Acting (every beat needs a performance, not a pose)
The renderer already does automatic acting: eyes dart and look at the other character, listeners look at whoever is talking, the speaker's mouth moves and head bobs while their bubble types out, Junior cowers on `pager` and `crash`, thinks while code is on screen, types then celebrates on `fix`, a happy monster laughs on `crash`. ADD explicit gestures where a beat needs a specific acting choice:
- Give every `scene` beat at least one gesture, chosen for the line being said: Junior `gasp` when the monster appears, monster `wave`/`beckon` when it greets him, `shrug` on a confused line, `facepalm` when Junior realises his own mistake, `nod` when he gets it, `shake_head` for "no, no, no".
- Change gesture mid-beat for a reaction: `[{"g": "think", "at": 0}, {"g": "point", "at": 0.6}]` = Junior figures it out, then points at the bug.
- Character signatures: Junior `facepalm` and `type`; The Null `look_down` (shy) and `nod`; The Caller `wave` (waves his receiver like a phone call) and `laugh`; Fork & Join `dance` together (they mirror each other — symmetry is the joke); The Leak `laugh` while growing; Ollie `beckon` and `wave` with his donut box.
- Hands only exist on Junior, Fork & Join and Ollie. For The Null, The Caller and The Leak, gestures become head tilts, eye direction, receiver waves and mouth movement — still use them.
- Don't use a gesture that fights the emotion (no `celebrate` on a `scared` expression).

Monster physical gags to use:
- leak: `action: "grow"` with `amount` 1.5–2.4 as it gets fed; `shrink` when cleaned up.
- caller: `action: "stack"` with `copies: 4` for recursion depth; `spin` while ringing.
- twins: put them centered with `hop` when they race; `shake` when deadlocked.
- ollie: place him at x 0.92 so he's half out of frame ("always one off"); move him `to {x: 0.7}` after the fix.
- null: `fade_in`, `float`; he's sad (`scared`) when crashed, `happy` when someone checks on him.

## Brand voice for captions and CTAs
"The next bug wakes at 3 AM." "Follow before the next one wakes up." "Save this before your next deploy." Short, dry, a little haunted.
