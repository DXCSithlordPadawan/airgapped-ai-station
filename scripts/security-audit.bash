#!/usr/bin/env bash
# security-audit.bash — Host-Level CIS/FIPS Compliance Audit
# Location: /usr/local/bin/security-audit.bash (Proxmox Host)
#
# Complement to security_compliance_audit.py — runs bash-native checks
# that do not require a Python interpreter.
#
# Compliance: NIST 800-53 AU-2 | CIS Level 2 | FIPS 140-3
set -euo pipefail

PASS=0
WARN=0
FAIL=0
LOG_DIR="/var/log/airgap"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/security_audit_$(date -u '+%Y%m%d_%H%M%S').log"

# ── Logging ───────────────────────────────────────────────────────────────────

log() { echo "$*" | tee -a "$LOG_FILE"; }
pass()  { log "[PASS]  $*"; (( PASS++ )) || true;  }
warn()  { log "[WARN]  $*"; (( WARN++ )) || true;  }
fail()  { log "[FAIL]  $*"; (( FAIL++ )) || true;  }
info()  { log "[INFO]  $*"; }

# ── Checks ────────────────────────────────────────────────────────────────────

check_fips() {
    info "Checking FIPS 140-3 mode..."
    local fips_val
    fips_val=$(cat /proc/sys/crypto/fips_enabled 2>/dev/null || echo "unavailable")
    if [[ "$fips_val" == "1" ]]; then
        pass "FIPS 140-3 mode: ENABLED"
    elif [[ "$fips_val" == "unavailable" ]]; then
        fail "FIPS node not found — kernel module missing?"
    else
        fail "FIPS 140-3 mode: DISABLED (value=${fips_val})"
    fi
}

check_zfs_arc() {
    info "Checking ZFS ARC limit..."
    local arc_max_bytes
    arc_max_bytes=$(cat /sys/module/zfs/parameters/zfs_arc_max 2>/dev/null || echo 0)
    local arc_max_gb=$(( arc_max_bytes / 1024 / 1024 / 1024 ))
    if [[ "$arc_max_bytes" -gt 0 && "$arc_max_gb" -le 16 ]]; then
        pass "ZFS ARC Max: ${arc_max_gb} GB (within 16 GB limit)"
    elif [[ "$arc_max_bytes" -eq 0 ]]; then
        warn "ZFS ARC Max: not set (unlimited — may impact LLM performance)"
    else
        warn "ZFS ARC Max: ${arc_max_gb} GB (exceeds 16 GB target)"
    fi
}

check_lxc_privileges() {
    info "Checking LXC container privilege levels..."
    local lxc_dir="/etc/pve/lxc"
    if [[ ! -d "$lxc_dir" ]]; then
        warn "LXC config directory not found: ${lxc_dir}"
        return
    fi
    for conf in "${lxc_dir}"/*.conf; do
        [[ -f "$conf" ]] || continue
        local vmid
        vmid=$(basename "$conf" .conf)
        if grep -q "unprivileged: 1" "$conf"; then
            pass "LXC ${vmid}: UNPRIVILEGED"
        else
            fail "LXC ${vmid}: PRIVILEGED — compliance violation"
        fi
    done
}

check_ssh_password_auth() {
    info "Checking SSH password authentication..."
    local sshd_config="/etc/ssh/sshd_config"
    if [[ ! -f "$sshd_config" ]]; then
        warn "sshd_config not found — SSH may not be installed."
        return
    fi
    if grep -qE "^PasswordAuthentication\s+no" "$sshd_config"; then
        pass "SSH password authentication: DISABLED"
    else
        fail "SSH password authentication may be ENABLED — check ${sshd_config}"
    fi
}

check_key_permissions() {
    info "Checking ZFS key directory permissions..."
    local key_dir="/etc/zfs/keys"
    if [[ ! -d "$key_dir" ]]; then
        warn "Key directory not found: ${key_dir}"
        return
    fi
    local perm
    perm=$(stat -c "%a" "$key_dir")
    if [[ "$perm" == "700" ]]; then
        pass "ZFS key directory permissions: 700 (correct)"
    else
        fail "ZFS key directory permissions: ${perm} (expected 700)"
    fi
}

# ── Summary ───────────────────────────────────────────────────────────────────

info "──────────────────────────────────────────────────────"
info " T5500 AIR-GAP SECURITY AUDIT"
info " Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
info "──────────────────────────────────────────────────────"

check_fips
check_zfs_arc
check_lxc_privileges
check_ssh_password_auth
check_key_permissions

info "──────────────────────────────────────────────────────"
info " PASS: ${PASS} | WARN: ${WARN} | FAIL: ${FAIL}"
info " Log: ${LOG_FILE}"

if [[ "$FAIL" -gt 0 ]]; then
    info " RESULT: NON-COMPLIANT"
    exit 1
fi
info " RESULT: COMPLIANT"
exit 0
