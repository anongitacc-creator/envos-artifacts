#!/usr/bin/env python3
"""
Atlas video for hub_xapp_commit_003.

The renderer is shared with every other EnvOS task (envos-atlas/render.py) so
the template cannot drift between videos. Everything specific to this task -
its applications, its task text, and one block per arm describing the
phenomenon along the six axes - lives in `atlas.spec.json` beside this
environment. Adding a phenomenon is an entry there, never a change here.

The previous per-task renderer is kept as make_atlas.legacy.py.

Usage: make_atlas.py <run_dir> [--out atlas.mp4]
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.dirname(HERE)
ATLAS = os.environ.get(
    "ENVOS_ATLAS_HOME", "${ENVOS_ROOT}/envos-atlas")

os.environ.setdefault("ENVOS_ATLAS_SPEC", os.path.join(ENV, "atlas.spec.json"))
sys.argv[0] = os.path.join(ATLAS, "render.py")
sys.path.insert(0, ATLAS)
runpy.run_path(sys.argv[0], run_name="__main__")
