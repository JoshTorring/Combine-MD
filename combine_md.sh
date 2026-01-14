#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/ObsidianVault"
  exit 1
fi

VAULT="$1"

OUTDIR_NAME="combined_output_folder"
TMPDIR_NAME="_tmp_md_flat"
OUTRTF_NAME="combined.rtf"

# Folder names to ignore (by name)
IGNORE_DIRS=(".obsidian" "$OUTDIR_NAME" "Config" "Old_Notes" "Todo" "US_Trip" "Unsorted" "Admin")

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Clean output in the target vault
rm -rf "$VAULT/$OUTDIR_NAME"
mkdir -p "$VAULT/$OUTDIR_NAME/$TMPDIR_NAME"

# Build --ignore args safely
IGNORE_ARGS=()
for d in "${IGNORE_DIRS[@]}"; do
  IGNORE_ARGS+=(--ignore "$d")
done

python3 "$SCRIPT_DIR/combine_md.py" "$VAULT" \
  --outdir-name "$OUTDIR_NAME" \
  --tmpdir-name "$TMPDIR_NAME" \
  "${IGNORE_ARGS[@]}"

# Combine all temp flat MDs into one RTF (safe with spaces) — works on default macOS bash too
(
  cd "$VAULT/$OUTDIR_NAME"
  if ! ls -1 "$TMPDIR_NAME"/*.md >/dev/null 2>&1; then
    echo "No temp .md files found in $VAULT/$OUTDIR_NAME/$TMPDIR_NAME"
    exit 1
  fi
  pandoc -s "$TMPDIR_NAME"/*.md -o "$OUTRTF_NAME"
)

echo "Done:"
echo "  $VAULT/$OUTDIR_NAME/$OUTRTF_NAME"
