"""Lets you run the project as `python -m voiceloop ...` (same as the `voiceloop` command)."""

import sys

from voiceloop.cli import main

sys.exit(main())
