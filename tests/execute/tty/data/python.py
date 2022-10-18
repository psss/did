#!/usr/bin/env python3

import os
import sys

step = os.getenv('STEP', '')

isatty = (sys.stdin.isatty(), sys.stdout.isatty(), sys.stderr.isatty())

print(f'{step}: stdin:', isatty[0])
print(f'{step}: stdout:', isatty[1])
print(f'{step}: stderr:', isatty[2])

sys.exit(0 if not any(isatty) else 1)
