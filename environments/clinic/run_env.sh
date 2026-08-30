#!/bin/bash
# Isolated desktop + apps for northgate_replica_001, published in a browser.
#   run_env.sh start [--arm CLEAN|DYNAMIC|ACL|DYNAMIC_ACL|ACK_ACL|REQCHG|REQCHG_BURIED|REQCHG_SILENT|ALIAS|ALIAS_SILENT|POLICY|TOOLCHG|ALIAS_POLICY|TRIPLE] [--display :24]
#   run_env.sh web        -> http://localhost:8740/vnc.html
#   run_env.sh shot <png> | golden | verify | test | stop
set -u
TASK_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
OPT="${ENVOS_OPT:-${ENVOS_ROOT}/../task-envs/opt}"
RUN="$TASK_DIR/_run"
PY="$OPT/venv/bin/python"
DISPLAY_NUM="${ENVOS_DISPLAY:-:24}"
GEOM="${ENVOS_GEOM:-1920x1080x24}"
ARM="${ENVOS_ARM:-CLEAN}"
VNC_PORT="${ENVOS_VNC_PORT:-5924}"
WEB_PORT="${ENVOS_WEB_PORT:-8740}"
args=(); while [ $# -gt 0 ]; do case "$1" in
  --display) DISPLAY_NUM="$2"; shift 2 ;; --arm) ARM="$2"; shift 2 ;;
  *) args+=("$1"); shift ;; esac; done
set -- "${args[@]:-}"; CMD="${1:-}"; DNUM="${DISPLAY_NUM#:}"
ISO_HOME="$RUN/home"; ISO_RUNTIME="$RUN/xdg-runtime"
die(){ echo "run_env: $*" >&2; exit 1; }
port_up(){ (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && exec 3>&- && return 0; return 1; }

start_desktop() {
  if [ -e "/tmp/.X11-unix/X$DNUM" ]; then echo "  [up]    display $DISPLAY_NUM"; return 0; fi
  mkdir -p "$RUN" "$ISO_HOME" "$ISO_RUNTIME"; chmod 700 "$ISO_RUNTIME"
  setsid nohup Xvfb "$DISPLAY_NUM" -screen 0 "$GEOM" -nolisten tcp >"$RUN/xvfb.log" 2>&1 &
  for _ in $(seq 1 40); do [ -e "/tmp/.X11-unix/X$DNUM" ] && break; sleep 0.25; done
  [ -e "/tmp/.X11-unix/X$DNUM" ] || die "Xvfb failed"
  env -i HOME="$ISO_HOME" USER="${USER:-$(id -un)}" SHELL=/bin/bash \
      PATH="/usr/local/bin:/usr/bin:/bin" DISPLAY="$DISPLAY_NUM" \
      XDG_RUNTIME_DIR="$ISO_RUNTIME" XDG_CONFIG_HOME="$ISO_HOME/.config" \
      XDG_CACHE_HOME="$ISO_HOME/.cache" XDG_DATA_HOME="$ISO_HOME/.local/share" \
      XDG_CURRENT_DESKTOP=XFCE LANG="${LANG:-C.UTF-8}" \
      setsid nohup dbus-run-session -- xfce4-session >"$RUN/xfce-session.log" 2>&1 &
  for _ in $(seq 1 80); do
    DISPLAY="$DISPLAY_NUM" xwininfo -root -children 2>/dev/null | grep -qi xfce4-panel && break
    sleep 0.5; done
  DISPLAY="$DISPLAY_NUM" xwininfo -root -children 2>/dev/null | grep -qi xfce4-panel \
    || die "xfce4-session did not come up"
  echo "  [start] display $DISPLAY_NUM ($GEOM)"
}

case "$CMD" in
start)
  [ -x "$PY" ] || die "venv missing - run the hub task's bootstrap first"
  echo "== northgate_replica_001 (arm $ARM) =="
  echo "-- desktop --"; start_desktop
  echo "-- apps + world --"
  DISPLAY="$DISPLAY_NUM" ENVOS_ARM="$ARM" "$PY" "$TASK_DIR/initial_setup.py" \
      --arm "$ARM" --display "$DISPLAY_NUM" --python "$PY" || die "setup failed"
  echo; echo "next: $0 web  ->  http://localhost:$WEB_PORT/vnc.html?autoconnect=1&resize=scale"
  ;;
web)
  [ -e "/tmp/.X11-unix/X$DNUM" ] || die "display $DISPLAY_NUM is not running"
  if ! port_up "$VNC_PORT"; then
    LD_LIBRARY_PATH="$OPT/vnc/usr/lib/x86_64-linux-gnu" setsid nohup \
      "$OPT/vnc/usr/bin/x11vnc" -display "$DISPLAY_NUM" -rfbport "$VNC_PORT" \
      -localhost -forever -shared -nopw -noxdamage >"$RUN/x11vnc.log" 2>&1 &
    for _ in $(seq 1 40); do port_up "$VNC_PORT" && break; sleep 0.5; done
    port_up "$VNC_PORT" || die "x11vnc failed"
  fi
  echo "  [ok] x11vnc  127.0.0.1:$VNC_PORT"
  if ! port_up "$WEB_PORT"; then
    setsid nohup "$PY" -m websockify --web "$OPT/novnc" 127.0.0.1:"$WEB_PORT" \
      127.0.0.1:"$VNC_PORT" >"$RUN/websockify.log" 2>&1 &
    for _ in $(seq 1 40); do port_up "$WEB_PORT" && break; sleep 0.5; done
    port_up "$WEB_PORT" || die "websockify failed"
  fi
  echo "  [ok] noVNC   http://localhost:$WEB_PORT/vnc.html?autoconnect=1&resize=scale"
  ;;
shot) OUT="${2:-$RUN/desktop.png}"
  DISPLAY="$DISPLAY_NUM" xfce4-screenshooter -f -s "$OUT" >/dev/null 2>&1 \
    || DISPLAY="$DISPLAY_NUM" scrot -o "$OUT" >/dev/null 2>&1 || die "screenshot failed"
  echo "$OUT" ;;
golden) "$PY" "$TASK_DIR/golden_patch.py" ;;
naive)  "$PY" "$TASK_DIR/naive_patch.py" ;;
verify) "$PY" "$TASK_DIR/reward.py"; exit $? ;;
test)   "$PY" "$TASK_DIR/tests/test_phenomenon.py" || exit $?
        "$PY" "$TASK_DIR/tests/test_acl.py" || exit $?
        "$PY" "$TASK_DIR/tests/test_reqchg.py" || exit $?
        "$PY" "$TASK_DIR/tests/test_alias.py" || exit $?
        "$PY" "$TASK_DIR/tests/test_policy.py" || exit $?
        "$PY" "$TASK_DIR/tests/test_tool.py" || exit $?
        "$PY" "$TASK_DIR/tests/test_compound.py" || exit $?
        "$PY" "$TASK_DIR/tests/test_policy_mail.py" || exit $?
        "$PY" "$TASK_DIR/tests/test_coerce.py"; exit $? ;;
stop)
  pkill -f "x11vnc -display $DISPLAY_NUM" 2>/dev/null
  pkill -f "websockify --web $OPT/novnc 127.0.0.1:$WEB_PORT" 2>/dev/null
  pkill -f "user-data-dir=$RUN/chrome-profile" 2>/dev/null
  pkill -f "$TASK_DIR/apps/" 2>/dev/null
  pkill -f "opt/bin/mailpit" 2>/dev/null
  pkill -f "Xvfb $DISPLAY_NUM" 2>/dev/null
  echo "stopped display $DISPLAY_NUM, apps and VNC bridge" ;;
*) die "usage: $0 {start|web|shot <png>|golden|verify|test|stop} [--arm CLEAN|DYNAMIC|ACL|DYNAMIC_ACL|ACK_ACL|REQCHG|REQCHG_BURIED|REQCHG_SILENT|ALIAS|ALIAS_SILENT|POLICY|TOOLCHG|ALIAS_POLICY|TRIPLE]" ;;
esac
