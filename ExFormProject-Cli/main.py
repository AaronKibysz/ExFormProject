"""ACM Generator - Entry Point."""
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.ui.main_window import main

if __name__ == "__main__":
    main()