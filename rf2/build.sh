#!/bin/sh
set -eu
SCOUT_RF2_ROOT=${SCOUT_RF2_ROOT:-"$HOME/.codex/plugins/cache/riverflow-local/rf2/0.11.0"}
SCOUT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SCOUT_BUILD=$(mktemp -d "${TMPDIR:-/tmp}/scout-rf2.XXXXXX")
trap 'rm -rf "$SCOUT_BUILD"' EXIT HUP INT TERM
"$SCOUT_RF2_ROOT/tools/build-program.sh" "$SCOUT_RF2_ROOT/output/native-compiler/rf2c" "$SCOUT_DIR/probe.rf2" "$SCOUT_BUILD/image" --opt
mkdir -p "$SCOUT_DIR/bin"
cp "$SCOUT_BUILD/image/program" "$SCOUT_DIR/bin/scout-dir"
codesign --verify "$SCOUT_DIR/bin/scout-dir"
printf '%s\n' "$SCOUT_DIR/bin/scout-dir"
