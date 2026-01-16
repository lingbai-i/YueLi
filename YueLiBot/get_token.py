import sys
import os
sys.path.append(os.getcwd())

from src.webui.core.auth import get_token_manager

try:
    token_manager = get_token_manager()
    print(f"TOKEN: {token_manager.get_token()}")
except Exception as e:
    print(f"Error: {e}")
