#!/bin/sh
# Saves a stock-site API key (git-ignored) without showing it on screen or passing it through the chat.
#     sh scripts/stock_key.sh pixabay      (or: pexels)
cd "$(dirname "$0")/.." || exit 1
site=${1:-pixabay}
case "$site" in
    pixabay|pexels) ;;
    *) echo "Uso: sh scripts/stock_key.sh pixabay   (o pexels)"; exit 1 ;;
esac
printf 'Pegá tu clave de %s (no se va a ver mientras la pegás) y apretá Enter: ' "$site"
stty -echo 2>/dev/null
IFS= read -r key
stty echo 2>/dev/null
echo
key=$(printf '%s' "$key" | tr -d '[:space:]')
if [ -z "$key" ]; then
    echo "No pegaste nada. Volvé a correr: sh scripts/stock_key.sh $site"
    exit 1
fi
umask 077
printf '%s\n' "$key" > ".${site}_key"
echo "Listo: clave guardada en $(pwd)/.${site}_key"
