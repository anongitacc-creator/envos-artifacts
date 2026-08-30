#!/bin/bash
# =============================================================================
# Build the kit-local toolchain and verify every dependency.
#
#   setup/install.sh               build whatever is missing, then report
#   setup/install.sh --check-only  report only, build nothing
#
# What gets built, all under $ENVOS_OPT (default <kit>/.kit - no root needed):
#   venv/    python + websockify + playwright + pillow
#   vnc/     x11vnc unpacked from Ubuntu .debs (apt-get download, no install)
#   novnc/   noVNC v1.5.0 (the browser VNC client)
#
# What must already exist on the machine (apt packages, need root once):
#   xvfb xfce4 dbus-x11 xdotool scrot ffmpeg fonts-dejavu-core
#   google-chrome (or chromium), nodejs+npm (>=18, to serve the Hub mocks),
#   the `claude` CLI (the agent under test),
#   and a CUA-Gym-Hub checkout with expedia_mock + gmail_mock built.
# =============================================================================
set -u
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
export ENVOS_KIT="${ENVOS_KIT:-$(dirname "$HERE")}"
[ -f "$ENVOS_KIT/config.local.env" ] && . "$ENVOS_KIT/config.local.env"
. "$ENVOS_KIT/config.env"
CHECK_ONLY=0; [ "${1:-}" = "--check-only" ] && CHECK_ONLY=1
PY="$ENVOS_OPT/venv/bin/python"
FAIL=0

say(){ printf '  %-4s %s\n' "$1" "$2"; if [ "$1" = FAIL ]; then FAIL=1; fi; return 0; }
have(){ command -v "$1" >/dev/null 2>&1; }

if [ "$CHECK_ONLY" -eq 0 ]; then
  echo "== building kit toolchain in $ENVOS_OPT =="
  mkdir -p "$ENVOS_OPT"
  if [ ! -x "$PY" ]; then
    python3 -m venv "$ENVOS_OPT/venv" || { echo "venv creation failed"; exit 1; }
    "$ENVOS_OPT/venv/bin/pip" install -q --upgrade pip
  fi
  "$PY" -c "import websockify, playwright, PIL" 2>/dev/null || \
    "$ENVOS_OPT/venv/bin/pip" install -q -r "$HERE/requirements.txt" \
      || { echo "pip install failed"; exit 1; }
  if [ ! -x "$ENVOS_OPT/vnc/usr/bin/x11vnc" ]; then
    echo "  fetching x11vnc (unpacked from .debs, no root)"
    mkdir -p "$ENVOS_OPT/debs" "$ENVOS_OPT/vnc"
    ( cd "$ENVOS_OPT/debs" && \
      for p in x11vnc libvncserver1 libvncclient1 libssl3t64 libjpeg-turbo8; do
        apt-get download "$p" >/dev/null 2>&1; done
      for d in *.deb; do [ -f "$d" ] && dpkg-deb -x "$d" "$ENVOS_OPT/vnc"; done )
  fi
  if [ ! -d "$ENVOS_OPT/novnc" ]; then
    echo "  fetching noVNC v1.5.0"
    curl -sfL -o "$ENVOS_OPT/novnc.tgz" \
      https://github.com/novnc/noVNC/archive/refs/tags/v1.5.0.tar.gz \
      && tar xzf "$ENVOS_OPT/novnc.tgz" -C "$ENVOS_OPT" \
      && mv -f "$ENVOS_OPT/noVNC-1.5.0" "$ENVOS_OPT/novnc"
    rm -f "$ENVOS_OPT/novnc.tgz"
  fi
fi

echo "== preflight =="
[ -x "$PY" ] && say PASS "venv            $ENVOS_OPT/venv" \
             || say FAIL "venv            missing - run ./envctl install"
"$PY" -c "import websockify, playwright, PIL" 2>/dev/null \
  && say PASS "python deps     websockify + playwright + pillow" \
  || say FAIL "python deps     incomplete"
[ -x "$ENVOS_OPT/vnc/usr/bin/x11vnc" ] && say PASS "x11vnc          $ENVOS_OPT/vnc" \
  || say FAIL "x11vnc          missing (apt-get download failed? install x11vnc system-wide and set ENVOS_OPT)"
[ -d "$ENVOS_OPT/novnc" ] && say PASS "noVNC           $ENVOS_OPT/novnc" \
  || say FAIL "noVNC           missing"
for c in Xvfb xfce4-session dbus-run-session xdotool scrot ffmpeg npm; do
  have "$c" && say PASS "$(printf '%-15s' "$c") $(command -v "$c")" \
            || say FAIL "$(printf '%-15s' "$c") not on PATH (apt install)"
done
[ -x "$CHROME_BIN" ] && say PASS "chrome          $CHROME_BIN" \
  || say FAIL "chrome          $CHROME_BIN not executable (set CHROME_BIN)"
have claude && say PASS "claude CLI      $(command -v claude)" \
  || say FAIL "claude CLI      not on PATH - the agent under test"
[ -f /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf ] \
  && say PASS "dejavu fonts    (atlas rendering)" \
  || say FAIL "dejavu fonts    apt install fonts-dejavu-core"
if [ -d "$CUA_GYM_HUB/websites" ]; then
  ok=1
  for a in expedia_mock gmail_mock; do
    [ -d "$CUA_GYM_HUB/websites/$a/dist" ] || ok=0
  done
  [ "$ok" -eq 1 ] && say PASS "CUA-Gym-Hub     $CUA_GYM_HUB (both mocks built)" \
    || say FAIL "CUA-Gym-Hub     mocks not built: cd $CUA_GYM_HUB && ./install-all.sh --only expedia_mock --build (and gmail_mock)"
else
  say FAIL "CUA-Gym-Hub     not found at $CUA_GYM_HUB - git clone https://github.com/xlang-ai/CUA-Gym-Hub and set CUA_GYM_HUB"
fi
for f in expedia_mock gmail_mock; do
  [ -s "$ENVOS_KIT/hub/app_defaults/$f.json" ] \
    && say PASS "app defaults    $f.json" \
    || say FAIL "app defaults    $f.json missing - see hub/README.md (prime_defaults.py)"
done

echo
[ "$FAIL" -eq 0 ] && echo "all checks passed - next: ./envctl start --arm CLEAN" \
                  || echo "fix the FAIL lines above, then re-run ./envctl check"
exit "$FAIL"
