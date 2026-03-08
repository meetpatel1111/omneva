"""Omneva — Native Cross-Platform Media Suite"""

import sys
import os

# Ensure src is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.app import OmnevaApp


def main():
    app = OmnevaApp(sys.argv)
    sys.exit(app.run())


if __name__ == '__main__':
    main()
