import sys
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PhotoNamer")
    app.setOrganizationName("PhotoNamer")

    window = MainWindow()
    window.show()
    exit_code = app.exec()
    # Delete the window explicitly while the app object is still alive so
    # Qt can tear down WebEngine cleanly before Python's GC runs.
    del window
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
