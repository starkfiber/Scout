#!/bin/sh
set -eu
SCOUT_RF2_ROOT=${SCOUT_RF2_ROOT:-"$HOME/.codex/plugins/cache/riverflow-local/rf2/0.12.0"}
if [ ! -x "$SCOUT_RF2_ROOT/tools/build-program.sh" ] || [ ! -x "$SCOUT_RF2_ROOT/output/native-compiler/rf2c" ]; then
 printf '%s\n' 'RF² compiler not found; set SCOUT_RF2_ROOT to a compatible installed RF² root.' >&2
 exit 1
fi
SCOUT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SCOUT_BUILD=$(mktemp -d "${TMPDIR:-/tmp}/scout-rf2.XXXXXX")
trap 'rm -rf "$SCOUT_BUILD"' EXIT HUP INT TERM
"$SCOUT_RF2_ROOT/tools/build-program.sh" "$SCOUT_RF2_ROOT/output/native-compiler/rf2c" "$SCOUT_DIR/probe.rf2" "$SCOUT_BUILD/image" --opt
"$SCOUT_RF2_ROOT/tools/build-program.sh" "$SCOUT_RF2_ROOT/output/native-compiler/rf2c" "$SCOUT_DIR/dir_service.rf2" "$SCOUT_BUILD/service"
mkdir -p "$SCOUT_DIR/bin"
cp "$SCOUT_BUILD/image/program" "$SCOUT_DIR/bin/scout-dir.new.$$"
cp "$SCOUT_BUILD/service/program" "$SCOUT_DIR/bin/scout-dir-service.new.$$"
mv -f "$SCOUT_DIR/bin/scout-dir.new.$$" "$SCOUT_DIR/bin/scout-dir"
mv -f "$SCOUT_DIR/bin/scout-dir-service.new.$$" "$SCOUT_DIR/bin/scout-dir-service"
codesign --verify "$SCOUT_DIR/bin/scout-dir"
codesign --verify "$SCOUT_DIR/bin/scout-dir-service"
printf '%s\n' "$SCOUT_DIR/bin/scout-dir"
printf '%s\n' "$SCOUT_DIR/bin/scout-dir-service"
