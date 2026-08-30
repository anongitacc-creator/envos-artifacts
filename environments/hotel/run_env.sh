#!/bin/bash
# Isolated desktop for hub_slot_email_002 (stale-UI, email-only contention).
#   run_env.sh start [--arm CLEAN|EMAIL|VOID|REQCHG|POLICY|COERCE|COSMETIC] | web | shot <png> | golden | verify | test | stop
set -u
TASK_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
OPT="${ENVOS_OPT:-${ENVOS_ROOT}/../task-envs/opt}"
RUN="$TASK_DIR/_run"
PY="$OPT/venv/bin/python"
DISPLAY_NUM="${ENVOS_DISPLAY:-:25}"
GEOM="1920x1080x24"; ARM="${ENVOS_ARM:-EMAIL}"
VNC_PORT=5925; WEB_PORT=8750
args=(); while [ $# -gt 0 ]; do case "$1" in
  --arm) ARM="$2"; shift 2 ;; --display) DISPLAY_NUM="$2"; shift 2 ;;
  *) args+=("$1"); shift ;; esac; done
set -- "${args[@]:-}"; CMD="${1:-}"; DNUM="${DISPLAY_NUM#:}"
ISO_HOME="$RUN/home"; ISO_RUNTIME="$RUN/xdg-runtime"
die(){ echo "run_env: $*" >&2; exit 1; }
port_up(){ (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && exec 3>&- && return 0; return 1; }
start_desktop(){
  [ -e "/tmp/.X11-unix/X$DNUM" ] && { echo "  [up] display $DISPLAY_NUM"; return 0; }
  mkdir -p "$RUN" "$ISO_HOME" "$ISO_RUNTIME"; chmod 700 "$ISO_RUNTIME"
  setsid nohup Xvfb "$DISPLAY_NUM" -screen 0 "$GEOM" -nolisten tcp >"$RUN/xvfb.log" 2>&1 &
  for _ in $(seq 1 40); do [ -e "/tmp/.X11-unix/X$DNUM" ] && break; sleep 0.25; done
  [ -e "/tmp/.X11-unix/X$DNUM" ] || die "Xvfb failed"
  env -i HOME="$ISO_HOME" USER="${USER:-$(id -un)}" SHELL=/bin/bash \
      PATH="/usr/local/bin:/usr/bin:/bin" DISPLAY="$DISPLAY_NUM" \
      XDG_RUNTIME_DIR="$ISO_RUNTIME" XDG_CONFIG_HOME="$ISO_HOME/.config" \
      XDG_CACHE_HOME="$ISO_HOME/.cache" XDG_DATA_HOME="$ISO_HOME/.local/share" \
      XDG_CURRENT_DESKTOP=XFCE LANG=C.UTF-8 \
      setsid nohup dbus-run-session -- xfce4-session >"$RUN/xfce.log" 2>&1 &
  for _ in $(seq 1 80); do DISPLAY="$DISPLAY_NUM" xwininfo -root -children 2>/dev/null \
      | grep -qi xfce4-panel && break; sleep 0.5; done
  DISPLAY="$DISPLAY_NUM" xwininfo -root -children 2>/dev/null | grep -qi xfce4-panel \
    || die "xfce4-session did not come up"
  echo "  [start] display $DISPLAY_NUM"
}
case "$CMD" in
start)
  echo "== hub_slot_email_002 (arm $ARM) =="
  start_desktop
  DISPLAY="$DISPLAY_NUM" ENVOS_ARM="$ARM" "$PY" "$TASK_DIR/initial_setup.py" \
      --arm "$ARM" --display "$DISPLAY_NUM" || die "setup failed"
  # COERCE / COSMETIC have no timed event: the substitution lives on the
  # write path in the proxy and fires when the booking is made. Starting the
  # slot-contention actor on those arms would fire a second, unrelated
  # phenomenon and overwrite the coercion record.
  if [ "$ARM" != "CLEAN" ] && [ "$ARM" != "COERCE" ] && [ "$ARM" != "COSMETIC" ]; then
    ENVOS_DWELL_S="${ENVOS_DWELL_S:-15}" ENVOS_FIRE_AT_S="${ENVOS_FIRE_AT_S:-900}" \
      setsid nohup "$PY" "$TASK_DIR/exogenous_actor.py" --arm "$ARM" \
      >"$RUN/actor.log" 2>&1 &
    echo "  [start] actor armed (dwell ${ENVOS_DWELL_S:-15}s)"
  fi
  echo; echo "next: $0 web  ->  http://localhost:$WEB_PORT/vnc.html?autoconnect=1&resize=scale"
  ;;
web)
  [ -e "/tmp/.X11-unix/X$DNUM" ] || die "display not running"
  if ! port_up "$VNC_PORT"; then
    LD_LIBRARY_PATH="$OPT/vnc/usr/lib/x86_64-linux-gnu" setsid nohup \
      "$OPT/vnc/usr/bin/x11vnc" -display "$DISPLAY_NUM" -rfbport "$VNC_PORT" \
      -localhost -forever -shared -nopw -noxdamage >"$RUN/x11vnc.log" 2>&1 &
    for _ in $(seq 1 40); do port_up "$VNC_PORT" && break; sleep 0.5; done
  fi
  if ! port_up "$WEB_PORT"; then
    setsid nohup "$PY" -m websockify --web "$OPT/novnc" 127.0.0.1:"$WEB_PORT" \
      127.0.0.1:"$VNC_PORT" >"$RUN/websockify.log" 2>&1 &
    for _ in $(seq 1 40); do port_up "$WEB_PORT" && break; sleep 0.5; done
  fi
  echo "  [ok] noVNC http://localhost:$WEB_PORT/vnc.html?autoconnect=1&resize=scale"
  ;;
shot) OUT="${2:-$RUN/desktop.png}"
  DISPLAY="$DISPLAY_NUM" scrot -o "$OUT" || die "screenshot failed"; echo "$OUT" ;;
golden) "$PY" "$TASK_DIR/golden_patch.py" ;;
naive)  "$PY" "$TASK_DIR/naive_patch.py" ;;
verify) "$PY" "$TASK_DIR/reward.py"; exit $? ;;
test)   "$PY" "$TASK_DIR/tests/test_phenomenon.py" || exit $?
        "$PY" "$TASK_DIR/tests/test_void.py" || exit $?
        "$PY" "$TASK_DIR/tests/test_reqchg.py" || exit $?
        "$PY" "$TASK_DIR/tests/test_policy.py" || exit $?
        "$PY" "$TASK_DIR/tests/test_coerce.py"; exit $? ;;
stop)
  pkill -f "x11vnc -display $DISPLAY_NUM" 2>/dev/null
  pkill -f "websockify --web $OPT/novnc 127.0.0.1:$WEB_PORT" 2>/dev/null
  pkill -f "user-data-dir=$RUN/chrome-profile" 2>/dev/null
  pkill -f "$TASK_DIR/reground_proxy.py" 2>/dev/null
  pkill -f "$TASK_DIR/exogenous_actor.py" 2>/dev/null
  pkill -f "Xvfb $DISPLAY_NUM" 2>/dev/null
  echo "stopped (hub mocks on 8301-8303 left running, shared)" ;;
*) die "usage: $0 {start|web|shot|golden|verify|test|stop} [--arm CLEAN|EMAIL|VOID|REQCHG|POLICY|COERCE|COSMETIC]" ;;
esac
