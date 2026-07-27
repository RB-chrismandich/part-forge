#!/usr/bin/env bash
# Run the Blender-dependent half of the part_kit regression harness.
#
# Separate from smoke.sh on purpose. That script's header promises nothing in it
# needs Blender, which is what lets it run anywhere; the cost is that every
# function which has ever shipped a wrong artifact from this repo sits outside it.
# This wrapper is the opt-in other half.
#
# Blender exits 0 whether or not the script inside it failed, so kit_smoke.py
# writes its verdict to $KIT_SMOKE_STATUS and this reads it back.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"

if [[ ! -x "$BLENDER" ]]; then
    echo "  kit_smoke: no Blender at $BLENDER"
    echo "  Set BLENDER=/path/to/blender. On macOS the .app path alone will not run"
    echo "  a script; the binary is inside Contents/MacOS/."
    exit 2
fi

STATUS_FILE="$(mktemp -t kit_smoke_status)"
trap 'rm -f "$STATUS_FILE"' EXIT
printf '1' >"$STATUS_FILE"

KIT_SMOKE_STATUS="$STATUS_FILE" "$BLENDER" -b -noaudio \
    --python "$ROOT/.claude/scripts/kit_smoke.py" 2>&1 |
    sed -n '/^geometry kernel/,/^  KIT SMOKE/p'

exit "$(cat "$STATUS_FILE")"
