"""
This file allows VSCODE to run flask apps using the launch button.
"""
import sys
import re
from flask.cli import main
sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
sys.exit(main())
