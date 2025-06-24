#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
hapmgr
Ham radio app manager
rel 0.6.1

part of i8zse hampack project (https://www.i8zse.it/hampack/)

Copyright (c) 2025 I8ZSE, Giorgio L. Rutigliano
(www.i8zse.it, www.i8zse.eu, www.giorgiorutigliano.it)

This is free software released under LGPL License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import sys
import subprocess
import os
from PyQt5.QtGui import QColor, QCloseEvent, QIcon
import locale
import shutil
import argparse
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QCheckBox, QLabel, QWidget, QHBoxLayout, \
    QTableWidgetItem, QTableWidget, QDialog
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QTranslator, QLocale, QCoreApplication, Qt
from babel.support import Translations
from hapmgr.mainwindow_ui import Ui_MainWindow
from hapmgr.about_ui import Ui_AboutDialog
from hapmgr.packages import Packs

class PackageWorker(QThread):
    """
    Worker thread for package updates
    """
    finished = pyqtSignal(str, bool)  # package_name, success
    output = pyqtSignal(str)

    def __init__(self, package_name, action):
        super().__init__()
        self.package_name = package_name
        self.action = action  # 'install' or 'remove'

    def run(self):
        try:
            if self.action == 'install':
                cmd = ['sudo', 'apt-get', 'install', '-y', self.package_name]
            else:
                cmd = ['sudo', 'apt-get', 'remove', '-y', self.package_name]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )

            for line in iter(process.stdout.readline, ''):
                self.output.emit(line.strip())

            process.wait()
            success = process.returncode == 0
            self.finished.emit(self.package_name, success)

        except Exception as e:
            self.output.emit(f"Error: {str(e)}")
            self.finished.emit(self.package_name, False)


class StatusWorker(QThread):
    """
    Worker thread for checking package status
    """
    status_updated = pyqtSignal(str, bool)  # package_name, is_installed
    finished = pyqtSignal()

    def __init__(self, packages):
        super().__init__()
        self.packages = packages

    def run(self):
        for package in self.packages:
            try:
                result = subprocess.run(
                    ['dpkg', '-l', package],
                    capture_output=True,
                    text=True
                )
                is_installed = result.returncode == 0 and 'ii' in result.stdout
                self.status_updated.emit(package, is_installed)
            except Exception:
                self.status_updated.emit(package, False)

        self.finished.emit()


class HamRadioManager(QMainWindow):

    _translate = QCoreApplication.translate

    def _(self, msg):
        self._translate("", msg)

    def __init__(self, translations):
        super().__init__()

        # Setup translations
        self.translations = translations
        self._ = self.translations.gettext

        self.packages = Packs(self.translations.gettext).packages
        def uitranslate(ambito, testo):
            return self._(testo)
        QCoreApplication.translate = uitranslate
        # Setup UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.package_status = {}
        self.package_checkboxes = {}
        self.worker = None
        self.status_worker = None

        self.setup_package_list()
        self.connect_signals()
        self.refresh_package_status()

    def setup_package_list(self):
        """
        Setup the package list with sortable columns
        """
        # table
        self.table = QTableWidget()
        self.ui.splitter.setStretchFactor(0, 2)
        self.ui.splitter.setStretchFactor(1, 1)

        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([self._("Sel"), self._("App"), self._("Desc"), self._("Pkg"), self._("Status")])
        self.table.setColumnWidth(0, 50)  # Checkbox
        self.table.setColumnWidth(1, 100)  # app
        self.table.setColumnWidth(2, 400)  # descr
        self.table.setColumnWidth(3, 100)  # meta-package
        self.table.setColumnWidth(4, 80)  # status
        # header alignmenr
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_item = self.table.horizontalHeaderItem(0)
        if header_item:
            header_item.setTextAlignment(Qt.AlignCenter)
        # sort headers
        self.table.setSortingEnabled(True)
        # self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionsClickable(True)
        # Nascondi l'intestazione verticale
        self.table.verticalHeader().setVisible(False)
        # Populate
        self.table.setRowCount(len(self.packages))
        self.package_checkboxes = {}

        for row, package in enumerate(self.packages):
            # Checkbox
            checkbox = QCheckBox()
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            # Aggiungi alla tabella
            self.table.setCellWidget(row, 0, checkbox_widget)
            self.table.setItem(row, 1, QTableWidgetItem(package['app']))
            self.table.setItem(row, 2, QTableWidgetItem(package['desc']))
            self.table.setItem(row, 3, QTableWidgetItem(package['pack']))
            self.table.setItem(row, 4, QTableWidgetItem("NotInst"))
            # Memorizza i riferimenti
            self.package_checkboxes[package['app']] = {
                'check': checkbox,
                'sts': False,
                'app': package['app'],
                'pack': package['pack'],
                'desc': package['desc'],
            }

        # Sostituisci il contenuto della scroll area
        self.ui.scrollArea.setWidget(self.table)

    def connect_signals(self):
        """
        Connect UI signals to slots
        """
        self.ui.selectAllBtn.clicked.connect(self.select_all_packages)
        self.ui.deselectAllBtn.clicked.connect(self.deselect_all_packages)
        self.ui.refreshBtn.clicked.connect(self.refresh_package_status)
        self.ui.installBtn.clicked.connect(self.install_selected)
        self.ui.removeBtn.clicked.connect(self.remove_selected)
        self.ui.actionAbout.triggered.connect(self.showabout)
        self.ui.actionExit.triggered.connect(self.exitapp)

    def refresh_package_status(self):
        """
        Refresh the installation status of all packages
        """
        self.ui.statusLabel.setText(self._('Checking package status...'))
        self.ui.progressBar.setVisible(True)
        self.ui.progressBar.setRange(0, 0)

        self.status_worker = StatusWorker(p['app'] for p in self.packages)
        self.status_worker.status_updated.connect(self.update_package_status)
        self.status_worker.finished.connect(self.status_check_finished)
        self.status_worker.start()

    def update_package_status(self, package_name, is_installed):
        """
        Update the status of a single package
        """
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)  # package name
            if item and item.text() == package_name:
                # update status
                status_item = self.table.item(row, 4)
                status_text = self._('Inst') if is_installed else self._('NotInst')
                status_item.setText(status_text)
                # mark color
                color = QColor(220, 255, 220) if is_installed else QColor(255, 220, 220)
                for col in range(self.table.columnCount()):
                    cell_item = self.table.item(row, col)
                    if cell_item:
                        cell_item.setBackground(color)
                widget = self.table.cellWidget(row, 0)  # Colonna 0 = checkbox
                if widget:
                    widget.setStyleSheet(f"background-color: {color.name()};")
                self.package_status[package_name] = is_installed
                break


    def status_check_finished(self):
        """
        Called when status check is complete
        """
        self.ui.progressBar.setVisible(False)
        self.ui.statusLabel.setText(self._('Ready'))

    def select_all_packages(self):
        """
        Select all package checkboxes
        """
        for widgets in self.package_checkboxes.values():
            widgets['checkbox'].setChecked(True)

    def deselect_all_packages(self):
        """
        Deselect all package checkboxes
        """
        for widgets in self.package_checkboxes.values():
            widgets['checkbox'].setChecked(False)

    def get_selected_packages(self):
        """
        Get list of selected packages
        """
        selected = []
        for package_name, widgets in self.package_checkboxes.items():
            if widgets['check'].isChecked():
                selected.append(package_name)
        return selected

    def install_selected(self):
        """
        Install selected packages
        """
        selected = self.get_selected_packages()
        if not selected:
            QMessageBox.warning(self, self._('No packages selected'),
                                self._('Please select packages first'))
            return

        # Confirmation dialog
        msg = self._('Install the following packages?') + '\n\n' + '\n'.join(selected)
        reply = QMessageBox.question(self, self._('Confirm Installation'), msg)

        if reply == QMessageBox.Yes:
            self.execute_package_operations(selected, 'install')

    def remove_selected(self):
        """
        Remove selected packages
        """
        selected = self.get_selected_packages()
        if not selected:
            QMessageBox.warning(self, self._('No packages selected'),
                                self._('Please select packages first'))
            return

        # Confirmation dialog
        msg = self._('Remove the following packages?') + '\n\n' + '\n'.join(selected)
        reply = QMessageBox.question(self, self._('Confirm Removal'), msg)

        if reply == QMessageBox.Yes:
            self.execute_package_operations(selected, 'remove')

    def execute_package_operations(self, packages, operation):
        """
        Execute package operations sequentially
        """
        self.ui.outputText.clear()
        self.ui.progressBar.setVisible(True)
        self.ui.progressBar.setRange(0, len(packages))
        self.ui.progressBar.setValue(0)

        action_text = self._('Installing') if operation == 'install' else self._('Removing')
        self.ui.statusLabel.setText(f"{action_text}...")

        # Disable buttons during operation
        self.ui.installBtn.setEnabled(False)
        self.ui.removeBtn.setEnabled(False)

        # Start with first package
        self.current_packages = packages.copy()
        self.current_operation = operation
        self.process_next_package()

    def process_next_package(self):
        """
        Process the next package in the queue
        """
        if not self.current_packages:
            # All packages processed
            self.operation_finished()
            return

        package = self.current_packages.pop(0)
        self.ui.outputText.append(f"\n{'=' * 50}")
        self.ui.outputText.append(f"Processing: {package}")
        self.ui.outputText.append(f"{'=' * 50}")

        self.worker = PackageWorker(package, self.current_operation)
        self.worker.output.connect(self.update_output)
        self.worker.finished.connect(self.package_operation_finished)
        self.worker.start()

    def package_operation_finished(self, package_name, success):
        """
        Called when a single package operation finishes
        """
        self.ui.progressBar.setValue(self.ui.progressBar.value() + 1)

        if success:
            self.ui.outputText.append(f"\n✓ {package_name}: {self._('Operation completed')}")
        else:
            self.ui.outputText.append(f"\n✗ {package_name}: {self._('Operation failed')}")

        # Process next package
        self.process_next_package()

    def operation_finished(self):
        """
        Called when all operations are complete
        """
        self.ui.progressBar.setVisible(False)
        self.ui.statusLabel.setText(self._('Ready'))

        # Re-enable buttons
        self.ui.installBtn.setEnabled(True)
        self.ui.removeBtn.setEnabled(True)

        # Refresh status
        QTimer.singleShot(1000, self.refresh_package_status)

    def update_output(self, text):
        """
        Update output text area
        """
        self.ui.outputText.append(text)
        # Auto-scroll to bottom
        scrollbar = self.ui.outputText.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


    def showabout(self):
        """
        SHow about dialog (modal)
        """
        AboutDialog = QDialog()
        aui = Ui_AboutDialog()
        aui.setupUi(AboutDialog)
        AboutDialog.move(self.geometry().center())
        AboutDialog.exec()

    def exitapp(self):
        """
        Close app
        """
        self.close()

def main():
    parser = argparse.ArgumentParser(description="Hamradio apps install manager")
    parser.add_argument('-l', '--lang', type=str, help='Country lang code [it, en, de, fr, es]')
    args = parser.parse_args()
    if args.lang is None:
        args.lang = locale.setlocale(locale.LC_CTYPE).split(".")[0]
        if ("_") in args.lang:
            lang, country = args.lang.split("_")
            if lang.lower() != lang:
                # windows
                args.lang = {
                    'Italian': 'it',
                    'English': 'en',
                    'French': 'fr',
                    'German': 'de',
                    'Spanish': 'es'}[lang]
    else:
        lang = args.lang
    # Setup translations
    translations = Translations.load('locale', lang, domain='messages')
    _ = translations.gettext

    app = QApplication(sys.argv)
    app.setApplicationName("Ham Radio Package Manager")
    app.setWindowIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.svg")))
    window = HamRadioManager(translations)

    # Check if running as root/sudo
    if shutil.which("apt-get") is None:
        QMessageBox.critical(
            None,
            _("Critical error!"),
            _("Operating sistem is not debian compatible"),
            QMessageBox.Ok
        )


    if os.geteuid() != 0:
        QMessageBox.warning(
            None,
            _("Superuser not detected!"),
            _("Some functions requires super user capabilities"),
            QMessageBox.Ok
        )

    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()