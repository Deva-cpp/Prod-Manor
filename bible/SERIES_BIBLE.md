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

## Writing rules
- Total 25–40 seconds, 6–9 beats. Every beat dur 1.8–5s.
- Narration: a calm, dry storyteller voice. Max 16 words per beat. Not on every beat (3–5 beats). Never read the code aloud character by character.
- Dialogue bubbles: max 9 words each, max 2 per beat. Characters speak in character.
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
Actions: idle, enter_left, enter_right, exit_left, exit_right, shake, hop, grow, shrink, pop_in, fade_in, fade_out, defeated, peek, spin (caller dial), float, stack (caller: copies build into a tower; use with copies 3–5).
Junior faces right, so put him on the left (x 0.2–0.35) with the monster on the right (x 0.65–0.8). Use `flashlight` when Junior and a monster share a scene.

Monster physical gags to use:
- leak: `action: "grow"` with `amount` 1.5–2.4 as it gets fed; `shrink` when cleaned up.
- caller: `action: "stack"` with `copies: 4` for recursion depth; `spin` while ringing.
- twins: put them centered with `hop` when they race; `shake` when deadlocked.
- ollie: place him at x 0.92 so he's half out of frame ("always one off"); move him `to {x: 0.7}` after the fix.
- null: `fade_in`, `float`; he's sad (`scared`) when crashed, `happy` when someone checks on him.

## Brand voice for captions and CTAs
"The next bug wakes at 3 AM." "Follow before the next one wakes up." "Save this before your next deploy." Short, dry, a little haunted.
