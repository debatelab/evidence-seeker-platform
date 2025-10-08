#!/usr/bin/env bash
# Update a pinned GitHub Action SHA in workflow files.
# Usage: scripts/update-action-sha.sh <owner/repo> <tag> [workflow_file]
# Example: scripts/update-action-sha.sh actions/checkout v5.1.0 .github/workflows/ci.yml
# Will replace the existing 40-char SHA for that action with the SHA of the provided tag
# and update the trailing comment with the tag.
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: $0 <owner/repo> <tag> [workflow_file]" >&2
  exit 1
fi

ACTION_REPO="$1"
TAG="$2"
WORKFLOW_FILE="${3:-.github/workflows/ci.yml}"

if [[ ! -f "$WORKFLOW_FILE" ]]; then
  echo "Workflow file not found: $WORKFLOW_FILE" >&2
  exit 2
fi

# Obtain the commit SHA for the tag
SHA=$(git ls-remote "https://github.com/${ACTION_REPO}.git" "$TAG" | awk '{print $1}' | head -n1)
if [[ -z "$SHA" ]]; then
  echo "Could not resolve tag $TAG for $ACTION_REPO" >&2
  exit 3
fi

# Escape slashes for sed
ESC_ACTION_REPO=$(printf '%s\n' "$ACTION_REPO" | sed 's/[\/.&]/\\&/g')
ESC_SHA=$(printf '%s\n' "$SHA" | sed 's/[\/.&]/\\&/g')
ESC_TAG=$(printf '%s\n' "$TAG" | sed 's/[\/.&]/\\&/g')

# Replace the uses line: uses: <repo>@<40sha> # comment
# Keep existing spacing; update SHA and trailing comment to reflect tag
TMP_FILE=$(mktemp)
awk -v repo="$ACTION_REPO" -v sha="$SHA" -v tag="$TAG" '
  BEGIN {changed=0}
  {
    if ($0 ~ "uses: " repo "@" && $0 ~ /#[ ]?v?[0-9]/) {
      sub(/@[a-f0-9]{40}/, "@" sha);
      sub(/# .*/, "# " tag);
      changed=1;
    } else if ($0 ~ "uses: " repo "@" && $0 !~ /#/) {
      # line without a trailing comment; append one
      sub(/@[a-f0-9]{40}/, "@" sha);
      $0 = $0 " # " tag;
      changed=1;
    }
    print;
  }
  END { if (changed==0) { exit 5 } }
' "$WORKFLOW_FILE" > "$TMP_FILE" || {
  status=$?
  if [[ $status -eq 5 ]]; then
    echo "No matching pinned action line found for $ACTION_REPO in $WORKFLOW_FILE" >&2
  else
    echo "Failed to process file" >&2
  fi
  rm -f "$TMP_FILE"
  exit 4
}

mv "$TMP_FILE" "$WORKFLOW_FILE"

echo "Updated $ACTION_REPO to $TAG ($SHA) in $WORKFLOW_FILE"
