#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, r'str(ROOT.parent / 'q1n1' / 'tools')')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

import time

os.environ['SNAP_GUEST_MIB'] = '2048'
os.environ['SNAP_SMP_REPORT_PREFIX'] = f'qemu-boot-{int(time.time())}'
os.environ['SNAP_WATCHDOG'] = '3600'

import probes.run as pr

sys.argv = [
    'probes/run.py',
    'xnuboot',
    '--qemu',
    '--guest-profile', 'j700ap-26A428-bootfb-xars-uniform-no-audio',
    '--ramdisk', 'downloads/extracted/j700ap/basesystem-26A428.apfs',
    '--root-hash', 'downloads/extracted/j700ap/basesystem-26A428.root-hash',
    '--ramdisk-mode', 'iokit',
    '--graphics-boot',
    '--console', 'panel'
]

if __name__ == '__main__':
    sys.exit(pr.main())
