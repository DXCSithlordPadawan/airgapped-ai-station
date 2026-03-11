#!/usr/bin/env bash
# zfs-key-manager.sh — ZFS Encryption Key Lifecycle Manager
# Location: /usr/local/bin/zfs-key-manager.sh (Proxmox Host)
#
# Usage:
#   zfs-key-manager.sh generate <dataset>   — Create a new FIPS-validated key
#   zfs-key-manager.sh load     <dataset>   — Load key for a dataset
#   zfs-key-manager.sh rotate   <dataset>   — Rotate key for a dataset
#
# Compliance: NIST 800-53 SC-12, SC-13 | FIPS 140-3 | CIS Level 2
set -euo pipefail

KEY_DIR="/etc/zfs/keys"
FIPS_PATH="/proc/sys/crypto/fips_enabled"

ACTION="${1:-}"
DATASET="${2:-}"

# ── Helpers ───────────────────────────────────────────────────────────────────

log_info()  { echo "[INFO]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"; }
log_ok()    { echo "[PASS]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"; }
log_error() { echo "[ERROR] $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }

require_arg() {
    if [[ -z "${DATASET}" ]]; then
        log_error "Missing dataset argument."
        echo "Usage: $0 {generate|load|rotate} <dataset_name>"
        exit 1
    fi
}

# ── FIPS Pre-Check — GAP-SEC-02 fix ──────────────────────────────────────────
# Key material must only be generated when the kernel FIPS DRBG is active.
assert_fips_enabled() {
    if [[ ! -f "$FIPS_PATH" ]]; then
        log_error "FIPS kernel node not found at ${FIPS_PATH}."
        log_error "Cannot generate key material without FIPS 140-3 validated DRBG."
        exit 1
    fi
    local fips_val
    fips_val=$(cat "$FIPS_PATH")
    if [[ "$fips_val" != "1" ]]; then
        log_error "FIPS mode is NOT active (value=${fips_val})."
        log_error "Enable FIPS: add 'fips=1' to GRUB_CMDLINE_LINUX_DEFAULT and reboot."
        exit 1
    fi
    log_ok "FIPS 140-3 mode confirmed active — proceeding with key generation."
}

dataset_key_path() {
    # Converts dataset slashes to underscores: tank/workspace -> tank_workspace
    echo "${KEY_DIR}/${DATASET//\//_}.key"
}

# ── Actions ───────────────────────────────────────────────────────────────────

generate_key() {
    assert_fips_enabled
    mkdir -p "$KEY_DIR"
    chmod 700 "$KEY_DIR"
    local key_path
    key_path=$(dataset_key_path)

    log_info "Generating FIPS-compliant 256-bit AES key for dataset: ${DATASET}"
    # /dev/urandom on a FIPS kernel routes through the FIPS DRBG
    dd if=/dev/urandom of="$key_path" bs=32 count=1 status=none
    chmod 600 "$key_path"
    log_ok "Key created: ${key_path}"
}

load_key() {
    local key_path
    key_path=$(dataset_key_path)

    if [[ ! -f "$key_path" ]]; then
        log_error "Key file not found: ${key_path}"
        exit 1
    fi

    log_info "Loading key for dataset: ${DATASET}"
    zfs load-key "$DATASET"
    log_ok "Key loaded: ${DATASET}"
}

rotate_key() {
    assert_fips_enabled
    local key_path
    key_path=$(dataset_key_path)
    local new_key="${KEY_DIR}/${DATASET//\//_}_new.key"

    log_info "Rotating key for dataset: ${DATASET}"

    # Ensure key is loaded before rotation
    zfs load-key "$DATASET" 2>/dev/null || true

    # Generate replacement key
    dd if=/dev/urandom of="$new_key" bs=32 count=1 status=none
    chmod 600 "$new_key"

    # Apply new key
    zfs change-key -o keylocation="file://${new_key}" "$DATASET"

    # Atomically replace old key with new
    mv "$new_key" "$key_path"
    log_ok "Key rotated for dataset: ${DATASET}"
}

# ── Dispatch ──────────────────────────────────────────────────────────────────

require_arg

case "$ACTION" in
    generate) generate_key ;;
    load)     load_key     ;;
    rotate)   rotate_key   ;;
    *)
        echo "Usage: $0 {generate|load|rotate} <dataset_name>"
        exit 1
        ;;
esac
