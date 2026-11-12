#!/bin/zsh
set -e
cd "${0:A:h}"
if /usr/bin/curl --silent --fail --max-time 2 http://127.0.0.1:8766/api/overview >/dev/null; then
  /usr/bin/open http://127.0.0.1:8766/
  exit 0
fi
/usr/bin/python3 -m scout &
scout_pid=$!
sleep 1
/usr/bin/open http://127.0.0.1:8766/
wait "$scout_pid"
