#!/usr/bin/env bash
# sneakernet-update.bash — Air-Gap Sideloading Script with Integrity Verification
# Location: /usr/local/bin/sneakernet-update.bash (Proxmox Host)
#
# Usage: sneakernet-update.bash [--models] [--images] [--all]
#
# Requirements:
#   - USB must be mounted at /mnt/usb before running
#   - Checksum files (*.sha256) must be present alongside each artefact
#
# Compliance: NIST 800-53 SI-7 (Software & Information Integrity), SA-12 (Supply Chain)
set -euo pipefail

USB_PATH="/mnt/usb/updates"
CLAUDE_LXC=101
OLLAMA_LXC=102
HASH_CMD="sha256sum"

# ── Helpers ───────────────────────────────────────────────────────────────────

log_info()  { echo "[INFO]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"; }
log_ok()    { echo "[PASS]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"; }
log_error() { echo "[ERROR] $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }

verify_sha256() {
    local file="$1"
    local checksum_file="${file}.sha256"

    if [[ ! -f "$checksum_file" ]]; then
        log_error "Missing checksum file: ${checksum_file}"
        log_error "ABORT: Cannot verify integrity of ${file}."
        return 1
    fi

    log_info "Verifying SHA-256: $(basename "$file")"
    if ! ${HASH_CMD} --check --status "$checksum_file"; then
        log_error "INTEGRITY FAILURE: SHA-256 mismatch for ${file}."
        log_error "ABORT: Possible supply chain compromise. Do NOT deploy."
        return 1
    fi
    log_ok "Integrity verified: $(basename "$file")"
    return 0
}

# ── USB Mount Check ───────────────────────────────────────────────────────────

if [[ ! -d "$USB_PATH" ]]; then
    log_error "USB path not found: ${USB_PATH}"
    log_error "Mount the encrypted USB at /mnt/usb before running this script."
    exit 1
fi

# ── Model Weight Sideloading ──────────────────────────────────────────────────

sideload_models() {
    if [[ ! -d "${USB_PATH}/models" ]]; then
        log_info "No models directory on USB — skipping model update."
        return 0
    fi

    log_info "Sideloading LLM model weights..."
    local model_count=0

    while IFS= read -r -d '' model_file; do
        [[ "$model_file" == *.sha256 ]] && continue
        verify_sha256 "$model_file" || exit 1
        cp -v "$model_file" "/tank/ollama-models/"
        (( model_count++ )) || true
    done < <(find "${USB_PATH}/models" -type f -print0)

    if [[ "$model_count" -eq 0 ]]; then
        log_info "No model files found in ${USB_PATH}/models."
        return 0
    fi

    log_info "Refreshing Ollama model list..."
    pct exec "$OLLAMA_LXC" -- ollama list
    log_ok "Model sideload complete (${model_count} file(s))."
}

# ── Podman Image Sideloading ──────────────────────────────────────────────────

sideload_images() {
    local image_tar="${USB_PATH}/images/sandbox.tar"
    if [[ ! -f "$image_tar" ]]; then
        log_info "No sandbox.tar on USB — skipping image update."
        return 0
    fi

    verify_sha256 "$image_tar" || exit 1

    log_info "Pushing image archive to LXC ${CLAUDE_LXC}..."
    pct push "$CLAUDE_LXC" "$image_tar" "/tmp/sandbox.tar"

    log_info "Loading Podman image inside LXC ${CLAUDE_LXC}..."
    pct exec "$CLAUDE_LXC" -- podman load -i /tmp/sandbox.tar

    log_info "Cleaning up archive from LXC..."
    pct exec "$CLAUDE_LXC" -- rm -f /tmp/sandbox.tar

    log_ok "Image sideload complete."
}

# ── Main ──────────────────────────────────────────────────────────────────────

MODE="${1:---all}"

log_info "=== Sideloading Procedure Started (mode: ${MODE}) ==="

case "$MODE" in
    --models) sideload_models ;;
    --images) sideload_images ;;
    --all)    sideload_models; sideload_images ;;
    *)
        echo "Usage: $0 [--models|--images|--all]"
        exit 1
        ;;
esac

log_ok "=== Sideloading Complete ==="
