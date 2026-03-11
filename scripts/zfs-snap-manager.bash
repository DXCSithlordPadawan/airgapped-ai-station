#!/usr/bin/env bash
# zfs-snap-manager.bash — ZFS Snapshot Manager with Policy Enforcement
# Location: /usr/local/bin/zfs-snap-manager.bash (Proxmox Host)
#
# Usage:
#   zfs-snap-manager.bash --dataset tank/workspace --keep 7
#   zfs-snap-manager.bash --policy /etc/airgap/policy.yml  (run all datasets)
#
# Compliance: NIST 800-53 CP-9 (System Backup) | CIS Level 2
set -euo pipefail

POLICY_FILE="/etc/airgap/policy.yml"
SNAP_PREFIX="autosnap_"

# ── Helpers ───────────────────────────────────────────────────────────────────

log_info()  { echo "[INFO]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"; }
log_ok()    { echo "[PASS]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"; }
log_error() { echo "[ERROR] $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }

# ── Input Validation ─────────────────────────────────────────────────────────

validate_dataset() {
    local dataset="$1"
    # Dataset names: alphanumeric, slashes, hyphens, underscores only
    if [[ ! "$dataset" =~ ^[a-zA-Z0-9_/\-]+$ ]]; then
        log_error "Invalid dataset name: '${dataset}'"
        log_error "Dataset names must match: [a-zA-Z0-9_/-]+"
        exit 1
    fi
}

validate_keep() {
    local keep="$1"
    # Must be a positive integer
    if [[ ! "$keep" =~ ^[1-9][0-9]*$ ]]; then
        log_error "Invalid keep count: '${keep}'"
        log_error "Keep count must be a positive integer (e.g. 7)."
        exit 1
    fi
}

# ── Snapshot & Prune ─────────────────────────────────────────────────────────

snapshot_and_prune() {
    local target="$1"
    local keep="$2"

    validate_dataset "$target"
    validate_keep    "$keep"

    local snap_name="${target}@${SNAP_PREFIX}$(date -u '+%Y-%m-%d_%H%M')"

    # Create snapshot
    if ! zfs snapshot "$snap_name"; then
        log_error "Failed to create snapshot: ${snap_name}"
        exit 1
    fi
    log_ok "Created snapshot: ${snap_name}"

    # Prune oldest snapshots beyond keep count
    local old_snaps
    old_snaps=$(
        zfs list -H -t snapshot -o name -s creation \
            | grep "^${target}@${SNAP_PREFIX}" \
            | head -n "-${keep}" \
        || true
    )

    if [[ -z "$old_snaps" ]]; then
        log_info "No snapshots to prune for ${target} (keep=${keep})."
        return 0
    fi

    while IFS= read -r snap; do
        if zfs destroy "$snap"; then
            log_ok "Pruned old snapshot: ${snap}"
        else
            log_error "Failed to destroy snapshot: ${snap}"
        fi
    done <<< "$old_snaps"
}

# ── Policy Mode (reads policy.yml via simple grep — no yq dependency) ────────

run_from_policy() {
    if [[ ! -f "$POLICY_FILE" ]]; then
        log_error "Policy file not found: ${POLICY_FILE}"
        exit 1
    fi

    log_info "Reading snapshot policy from: ${POLICY_FILE}"

    # Parse policy.yml for dataset/daily pairs using awk
    # Handles blocks:  tank/workspace:\n    daily: 7
    local current_dataset=""
    while IFS= read -r line; do
        # Match a dataset line (no leading spaces, ends with colon)
        if [[ "$line" =~ ^([a-zA-Z0-9_/\-]+):$ ]]; then
            current_dataset="${BASH_REMATCH[1]}"
        fi
        # Match daily retention line
        if [[ -n "$current_dataset" && "$line" =~ daily:[[:space:]]*([0-9]+) ]]; then
            local keep="${BASH_REMATCH[1]}"
            if [[ "$keep" -gt 0 ]]; then
                log_info "Policy: ${current_dataset} → keep ${keep} daily snapshots"
                snapshot_and_prune "$current_dataset" "$keep"
            else
                log_info "Policy: ${current_dataset} → daily=0, skipping snapshot."
            fi
            current_dataset=""
        fi
    done < "$POLICY_FILE"
}

# ── Argument Parsing ─────────────────────────────────────────────────────────

usage() {
    echo "Usage:"
    echo "  $0 --dataset <pool/dataset> --keep <count>"
    echo "  $0 --policy [policy_file]"
    exit 1
}

if [[ $# -eq 0 ]]; then usage; fi

MODE=""
DATASET_ARG=""
KEEP_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dataset) DATASET_ARG="$2"; shift 2 ;;
        --keep)    KEEP_ARG="$2";    shift 2 ;;
        --policy)
            MODE="policy"
            if [[ $# -gt 1 && "$2" != --* ]]; then
                POLICY_FILE="$2"; shift
            fi
            shift
            ;;
        *) usage ;;
    esac
done

if [[ "$MODE" == "policy" ]]; then
    run_from_policy
elif [[ -n "$DATASET_ARG" && -n "$KEEP_ARG" ]]; then
    snapshot_and_prune "$DATASET_ARG" "$KEEP_ARG"
else
    usage
fi
