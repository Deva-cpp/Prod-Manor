#!/usr/bin/env bash
# One-time setup for instant mode: deploys relay/worker.js to your free Cloudflare account and points
# the Telegram bot at it. Run from the repo root: bash scripts/setup_relay.sh
set -euo pipefail
cd "$(dirname "$0")/../relay"
echo "== 0/5 Installing Cloudflare's wrangler tool (first time takes a minute)"
npm install --no-audit --no-fund
W="./node_modules/.bin/wrangler"

echo "== 1/5 Log in to Cloudflare (a browser window opens; click Allow)"
$W whoami 2>/dev/null | grep -q "You are logged in" || $W login

echo "== 2/5 Storage for pending taps"
if grep -q REPLACED_BY_SETUP_SCRIPT wrangler.toml; then
  id=$($W kv namespace create UPDATES 2>&1 | grep -oE '[0-9a-f]{32}' | head -1)
  [ -n "$id" ] || { echo "Could not create the KV namespace. Run: $W kv namespace create UPDATES"; exit 1; }
  sed -i.bak "s/REPLACED_BY_SETUP_SCRIPT/$id/" wrangler.toml && rm -f wrangler.toml.bak
fi

echo "== 3/5 Deploy the relay"
out=$($W deploy 2>&1 | tee /dev/stderr) || true
url=$(printf '%s' "$out" | grep -oE 'https://[a-zA-Z0-9.-]+\.workers\.dev' | head -1)
if [ -z "$url" ]; then
  if printf '%s' "$out" | grep -q "workers.dev subdomain"; then
    echo; echo ">> New Cloudflare account: pick your free workers.dev name once at the onboarding link above"
    echo ">> (dash.cloudflare.com → Workers & Pages), then run this script again. It continues from here."
  else
    echo "Deploy didn't print a workers.dev URL. Check the output above."
  fi
  exit 1
fi

echo "== 4/5 Secrets (typing is hidden)"
put() { printf '%s' "$2" | $W secret put "$1" >/dev/null && echo "  saved $1"; }
read -rsp "  Telegram bot token (from @BotFather): " v; echo; put TELEGRAM_BOT_TOKEN "$v"
read -rp  "  Telegram chat id (the number the bot sent you): " v; put TELEGRAM_CHAT_ID "$v"
read -rsp "  GitHub token (fine-grained, Prod-Manor only, Actions: Read and write): " v; echo; put GH_TOKEN "$v"
relay_secret=$(openssl rand -hex 24); put RELAY_SECRET "$relay_secret"

cat <<EOF

== 5/5 Add these two values in GitHub, then come back here
  https://github.com/Deva-cpp/Prod-Manor/settings/secrets/actions
    Secrets tab   → New repository secret → Name: RELAY_SECRET        Value: $relay_secret
    Variables tab → New repository variable → Name: TELEGRAM_RELAY_URL  Value: $url
EOF
read -rp "Press Enter once both are saved to switch the bot to instant mode... "
curl -fsS -X POST "$url/setup" -H "Authorization: Bearer $relay_secret"; echo
echo "Done. Tap a button in Telegram: you should see '⏳ Got it' right away."
