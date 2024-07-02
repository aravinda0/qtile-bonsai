# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


import multiprocessing
import sys

from PySide6.QtWidgets import QApplication, QWidget


def main():
    def run_qt_app():
        title = sys.argv[1]

        app = QApplication([])
        window = QWidget()
        window.setWindowTitle(title)
        window.show()
        app.exec()

    process = multiprocessing.Process(target=run_qt_app)
    process.start()

    sys.stdout.write(str(process.pid))


if __name__ == "__main__":
    main()
