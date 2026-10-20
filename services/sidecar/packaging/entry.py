"""PyInstaller entry script (PyInstaller needs a file, not `-m app`)."""

from app.__main__ import main

if __name__ == "__main__":
    main()
