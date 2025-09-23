import os

# Ensure external pytest plugins (web3.tools etc.) are not auto-loaded
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
