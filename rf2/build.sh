#!/bin/sh
set -eu
SCOUT_RF2_ROOT=${SCOUT_RF2_ROOT:-"$HOME/.codex/plugins/cache/riverflow-local/rf2/0.12.0"}
if [ ! -x "$SCOUT_RF2_ROOT/tools/build-program.sh" ] || [ ! -x "$SCOUT_RF2_ROOT/output/native-compiler/rf2c" ]; then
 printf '%s\n' 'RF² compiler not found; set SCOUT_RF2_ROOT to a compatible installed RF² root.' >&2
 exit 1
fi
SCOUT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SCOUT_BIN=${SCOUT_RF2_BIN:-"$SCOUT_DIR/bin"}
SCOUT_BUILD=$(mktemp -d "${TMPDIR:-/tmp}/scout-rf2.XXXXXX")
trap 'rm -rf "$SCOUT_BUILD"' EXIT HUP INT TERM
"$SCOUT_RF2_ROOT/tools/build-program.sh" "$SCOUT_RF2_ROOT/output/native-compiler/rf2c" "$SCOUT_DIR/probe.rf2" "$SCOUT_BUILD/image" --opt
"$SCOUT_RF2_ROOT/tools/build-program.sh" "$SCOUT_RF2_ROOT/output/native-compiler/rf2c" "$SCOUT_DIR/dir_service.rf2" "$SCOUT_BUILD/service"
clang -O2 -std=c11 -Wall -Wextra -Werror "$SCOUT_DIR/../native/scout_index.c" -lsqlite3 -o "$SCOUT_BUILD/index-worker"
codesign -s - --force "$SCOUT_BUILD/index-worker"
codesign --verify "$SCOUT_BUILD/image/program"
codesign --verify "$SCOUT_BUILD/service/program"
codesign --verify "$SCOUT_BUILD/index-worker"
mkdir -p "$SCOUT_BIN"
cp "$SCOUT_BUILD/image/program" "$SCOUT_BIN/scout-dir.new.$$"
cp "$SCOUT_BUILD/service/program" "$SCOUT_BIN/scout-dir-service.new.$$"
cp "$SCOUT_BUILD/index-worker" "$SCOUT_BIN/scout-index-worker.new.$$"
mv -f "$SCOUT_BIN/scout-dir.new.$$" "$SCOUT_BIN/scout-dir"
mv -f "$SCOUT_BIN/scout-dir-service.new.$$" "$SCOUT_BIN/scout-dir-service"
mv -f "$SCOUT_BIN/scout-index-worker.new.$$" "$SCOUT_BIN/scout-index-worker"
codesign --verify "$SCOUT_BIN/scout-dir"
codesign --verify "$SCOUT_BIN/scout-dir-service"
codesign --verify "$SCOUT_BIN/scout-index-worker"
printf '%s\n' "$SCOUT_BIN/scout-dir"
printf '%s\n' "$SCOUT_BIN/scout-dir-service"
printf '%s\n' "$SCOUT_BIN/scout-index-worker"
