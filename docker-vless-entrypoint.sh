#!/bin/sh
set -eu

case "${VLESS_ENABLED:-0}" in
    1|true|TRUE|yes|YES)
        if [ ! -s /etc/xray/config.json ]; then
            echo 'VLESS is enabled, but config.json is missing or empty; using direct Docker networking' >&2
            touch /run/gateway.direct
            exec sleep infinity
        fi
        ;;
    *)
        echo 'VLESS is disabled; using direct Docker networking'
        touch /run/gateway.direct
        exec sleep infinity
        ;;
esac

UPLINK_IP=$(jq -r '.outbounds[] | select(.tag == "vless") | .settings.vnext[0].address' /etc/xray/config.json)
if [ -z "$UPLINK_IP" ] || [ "$UPLINK_IP" = null ]; then
    echo 'VLESS uplink address not found' >&2
    exit 1
fi
GATEWAY=$(ip -4 route show default | sed -n 's/.* via \([^ ]*\).*/\1/p' | head -n 1)
if [ -z "$GATEWAY" ]; then
    echo 'Docker network gateway not found' >&2
    exit 1
fi

# Only this container's network namespace is changed.
ip -4 route replace "$UPLINK_IP/32" via "$GATEWAY"
/usr/local/bin/xray run -config /etc/xray/config.json &
XRAY_PID=$!
echo "$XRAY_PID" > /run/xray.pid

i=0
until ip link show xray0 >/dev/null 2>&1; do
    if ! kill -0 "$XRAY_PID" 2>/dev/null; then
        echo 'Xray exited before creating the TUN interface' >&2
        exit 1
    fi
    i=$((i + 1))
    if [ "$i" -ge 100 ]; then
        echo 'Timed out waiting for Xray TUN interface' >&2
        exit 1
    fi
    sleep 0.1
done

# Every IPv4 destination except the VLESS uplink goes through Xray.
ip -4 route replace default dev xray0
# Avoid direct IPv6 egress if Docker enables IPv6 in the future.
ip -6 route replace unreachable default 2>/dev/null || true

trap 'kill "$XRAY_PID" 2>/dev/null || true' TERM INT
wait "$XRAY_PID"
