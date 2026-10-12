"""Application entrypoint for DocCompare desktop app."""

import sys
from ui.main_window import MainWindow


def main() -> None:
    """Launches DocCompare desktop interface."""
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
