import os
import re
import sys
import shutil
import platform
import subprocess
import threading
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QDialog,
    QPushButton,
    QLineEdit,
    QLabel,
    QProgressBar,
    QFileDialog,
    QMessageBox,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
)


def resource_path(path):
    base = Path(
        getattr(
            sys,
            "_MEIPASS",
            Path(__file__).resolve().parent,
        )
    )

    return str(base / path)

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def get_dir_size(path):
    """Return the total size in bytes of all files in a directory recursively."""
    total = 0

    if not path or not os.path.isdir(path):
        return 0

    for root, _dirs, files in os.walk(path):
        for filename in files:
            filepath = os.path.join(root, filename)

            try:
                total += os.path.getsize(filepath)
            except OSError:
                pass

    return total


def format_size(size):
    """Format a byte count as a human-readable size."""
    if size < 1024:
        return f"{size} B"

    if size < 1024**2:
        return f"{size / 1024:.1f} KB"

    if size < 1024**3:
        return f"{size / 1024 ** 2:.1f} MB"

    if size < 1024**4:
        return f"{size / 1024 ** 3:.2f} GB"

    return f"{size / 1024 ** 4:.2f} TB"


# --------------------------------------------------------------------------- #
# Copy tool
# --------------------------------------------------------------------------- #
class CopyTool:
    def __init__(self):
        self.name = "robocopy" if IS_WINDOWS else "rsync"

    def is_installed(self):
        return shutil.which(self.name) is not None

    def get_package_manager(self):
        """Detect the available Linux package manager."""
        if not IS_LINUX:
            return None

        package_managers = (
            ("apt", "apt-get"),
            ("pacman", "pacman"),
            ("dnf", "dnf"),
            ("zypper", "zypper"),
        )

        for name, command in package_managers:
            if shutil.which(command):
                return name

        return None

    def get_version(self):
        if not self.is_installed():
            return None

        try:
            if IS_WINDOWS:
                output = subprocess.run(
                    ["robocopy", "/?"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                ).stdout

                match = re.search(
                    r"Version\s+([\d.]+)",
                    output,
                )

                return match.group(1) if match else "Built into Windows"

            output = subprocess.run(
                ["rsync", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout

            match = re.search(
                r"version\s+([\d.]+)",
                output,
            )

            if match:
                return match.group(1)

            lines = output.splitlines()

            return lines[0].strip() if lines else "Unknown"

        except Exception:
            return None

    def _run_package_command(self, arguments):
        """Run a package manager command using pkexec or sudo."""
        if not arguments:
            return False, "No package manager command was provided."

        if shutil.which("pkexec"):
            command = ["pkexec"] + arguments

            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode == 0:
                    return True, ""

                error = (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or f"Command exited with code {result.returncode}."
                )

                return False, error

            except FileNotFoundError:
                pass

            except subprocess.TimeoutExpired:
                return False, "The package manager operation timed out."

            except Exception as e:
                return False, f"Error running '{' '.join(command)}': {e}"

        if shutil.which("sudo"):
            command = ["sudo"] + arguments

            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode == 0:
                    return True, ""

                error = (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or f"Command exited with code {result.returncode}."
                )

                return False, error

            except FileNotFoundError:
                pass

            except subprocess.TimeoutExpired:
                return False, "The package manager operation timed out."

            except Exception as e:
                return False, f"Error running '{' '.join(command)}': {e}"

        return (
            False,
            "Neither pkexec nor sudo is available on this system.",
        )

    def install(self):
        """Install rsync using the detected Linux package manager."""
        if IS_WINDOWS:
            return (
                False,
                "robocopy is built into Windows and does not need to be installed.",
            )

        package_manager = self.get_package_manager()

        if package_manager is None:
            return (
                False,
                "No supported package manager was found.\n\n"
                "Supported package managers:\n"
                "• apt\n"
                "• pacman\n"
                "• dnf\n"
                "• zypper",
            )

        commands = {
            "apt": [
                "apt-get",
                "install",
                "-y",
                "rsync",
            ],
            "pacman": [
                "pacman",
                "-S",
                "--noconfirm",
                "rsync",
            ],
            "dnf": [
                "dnf",
                "install",
                "-y",
                "rsync",
            ],
            "zypper": [
                "zypper",
                "--non-interactive",
                "install",
                "rsync",
            ],
        }

        ok, message = self._run_package_command(commands[package_manager])

        if ok:
            return (
                True,
                f"rsync was installed successfully using " f"{package_manager}.",
            )

        return (
            False,
            f"Failed to install rsync using " f"{package_manager}.\n\n{message}",
        )

    def update(self):
        """Update rsync using the detected Linux package manager."""
        if IS_WINDOWS:
            return (
                False,
                "robocopy is included with Windows and is updated "
                "through Windows Update.",
            )

        package_manager = self.get_package_manager()

        if package_manager is None:
            return (
                False,
                "No supported package manager was found.\n\n"
                "Supported package managers:\n"
                "• apt\n"
                "• pacman\n"
                "• dnf\n"
                "• zypper",
            )

        commands = {
            "apt": [
                "apt-get",
                "install",
                "--only-upgrade",
                "-y",
                "rsync",
            ],
            "pacman": [
                "pacman",
                "-S",
                "--needed",
                "--noconfirm",
                "rsync",
            ],
            "dnf": [
                "dnf",
                "upgrade",
                "-y",
                "rsync",
            ],
            "zypper": [
                "zypper",
                "--non-interactive",
                "update",
                "rsync",
            ],
        }

        ok, message = self._run_package_command(commands[package_manager])

        if ok:
            return (
                True,
                f"rsync was updated successfully using "
                f"{package_manager}.\n\n"
                "The package was already up to date if no changes were needed.",
            )

        return (
            False,
            f"Failed to update rsync using " f"{package_manager}.\n\n{message}",
        )

    def build_command(self, src, dst, move):
        if IS_WINDOWS:
            # /E    : Copy all subdirectories, including empty ones
            # /MT:8 : Use 8 threads for faster copying
            # /R:2  : Retry failed copies up to 2 times
            # /W:1  : Wait 1 second between retries
            # /BYTES : Display file sizes in bytes
            # /ETA   : Display estimated time of arrival
            command = [
                "robocopy",
                src,
                dst,
                "/E",
                "/MT:8",
                "/R:2",
                "/W:1",
                "/BYTES",
                "/ETA",
            ]

            if move:
                command.append("/MOVE")

            return command

        # --info=progress2 shows overall transfer progress.
        # This avoids repeatedly scanning the destination directory.
        command = [
            "rsync",
            "-a",
            "--info=progress2",
            "--human-readable",
        ]

        if move:
            command.append("--remove-source-files")

        command.extend(
            [
                src.rstrip("/") + "/",
                dst,
            ]
        )

        return command


# --------------------------------------------------------------------------- #
# Copy worker
# --------------------------------------------------------------------------- #
class CopyWorker(QThread):
    progress = Signal(int)
    file_update = Signal(str)
    speed_update = Signal(str)
    finished_ok = Signal(bool)
    error = Signal(str)

    def __init__(self, src, dst, move):
        super().__init__()

        self.src = src
        self.dst = dst
        self.move = move

        self.proc = None
        self.paused = False
        self.cancelled = False

        self.tool = CopyTool()

        self.total_size = 0
        self.completed_files = 0
        self.total_files = 0

    def run(self):
        try:
            if not self.tool.is_installed():
                self.error.emit(
                    f"'{self.tool.name}' is not installed. "
                    "Open [About] to install it."
                )
                return

            # Calculate the source size only once.
            # The copy process itself does not repeatedly scan the destination.
            self.total_size = get_dir_size(self.src)

            if IS_WINDOWS:
                self.total_files = self._count_files(self.src)

            command = self.tool.build_command(
                self.src,
                self.dst,
                self.move,
            )

            popen_kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True,
                "bufsize": 1,
                "universal_newlines": True,
            }

            if IS_WINDOWS:
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self.proc = subprocess.Popen(
                command,
                **popen_kwargs,
            )

            if IS_LINUX:
                self._run_rsync()
            else:
                self._run_robocopy()

            if self.proc.poll() is None:
                self.proc.wait()

            if self.cancelled:
                self.finished_ok.emit(True)
                return

            returncode = self.proc.returncode

            if IS_WINDOWS:
                # Robocopy exit codes 0-7 indicate success or
                # success with differences.
                if returncode >= 8:
                    self.error.emit(f"Robocopy exited with error code {returncode}.")
                    return

            else:
                if returncode != 0:
                    self.error.emit(f"rsync exited with error code {returncode}.")
                    return

            if self.move and IS_LINUX:
                self._cleanup_empty_source_dirs()

            self.progress.emit(100)

            self.file_update.emit("Completed.")

            self.speed_update.emit("")

            self.finished_ok.emit(False)

        except Exception as e:
            self.error.emit(str(e))

    def _run_rsync(self):
        """Read rsync's overall progress directly from its output."""
        for raw_line in self.proc.stdout:
            if self.cancelled:
                break

            line = raw_line.strip()

            if not line:
                continue

            progress_match = re.search(
                r"(\d+(?:\.\d+)?)\s+([KMGTPE]?B)?\s+"
                r"(\d+(?:\.\d+)?)%\s+"
                r"(\d+(?:\.\d+)?\s*[KMGTPE]?B/s)",
                line,
            )

            if progress_match:
                percentage = float(progress_match.group(3))

                self.progress.emit(
                    max(
                        0,
                        min(
                            100,
                            int(percentage),
                        ),
                    )
                )

                speed = progress_match.group(4)

                self.speed_update.emit(speed)

                continue

            # rsync --info=progress2 can also emit a line without
            # a speed value depending on terminal/output conditions.
            simple_progress = re.search(
                r"(\d+(?:\.\d+)?)%",
                line,
            )

            if simple_progress:
                percentage = float(simple_progress.group(1))

                self.progress.emit(
                    max(
                        0,
                        min(
                            100,
                            int(percentage),
                        ),
                    )
                )

            if not line.startswith("sent ") and not line.startswith("total size"):
                self.file_update.emit(line[:160])

    def _run_robocopy(self):
        """
        Read robocopy output directly.

        Robocopy does not expose a reliable overall byte percentage
        like rsync, so the progress bar is based on completed files.
        """
        for raw_line in self.proc.stdout:
            if self.cancelled:
                break

            line = raw_line.strip()

            if not line:
                continue

            lower = line.lower()

            # Skip robocopy headers and summary information.
            if lower.startswith(
                (
                    "-------------------------------------------------------------------------------",
                    "total",
                    "dirs",
                    "files",
                    "bytes",
                    "times",
                    "ended",
                    "new dir",
                )
            ):
                continue

            # Robocopy normally reports copied files with:
            # New File / Newer / Older / Extra File / etc.
            if (
                "new file" in lower
                or "newer" in lower
                or "older" in lower
                or "extra file" in lower
                or "modified" in lower
            ):
                self.completed_files += 1

                if self.total_files:
                    percentage = int(self.completed_files / self.total_files * 100)

                    self.progress.emit(
                        min(
                            99,
                            max(
                                0,
                                percentage,
                            ),
                        )
                    )

                self.file_update.emit(line[:160])

                continue

            # Show individual file paths that robocopy outputs.
            if "\\" in line:
                self.file_update.emit(line[:160])

    def _count_files(self, path):
        """Count source files once for Windows progress reporting."""
        count = 0

        try:
            for root, _dirs, files in os.walk(path):
                count += len(files)
        except OSError:
            return 0

        return count

    def _cleanup_empty_source_dirs(self):
        """Remove empty source directories after a Linux move."""
        try:
            for root, dirs, _files in os.walk(
                self.src,
                topdown=False,
            ):
                for directory in dirs:
                    path = os.path.join(
                        root,
                        directory,
                    )

                    try:
                        os.rmdir(path)
                    except OSError:
                        pass

            try:
                os.rmdir(self.src)
            except OSError:
                pass

        except OSError:
            pass

    # ---- Process control -------------------------------------------------- #
    def pause(self):
        if not self.proc:
            return False

        self.paused = True

        if HAS_PSUTIL:
            try:
                psutil.Process(self.proc.pid).suspend()

                return True

            except Exception:
                return False

        if IS_LINUX:
            try:
                os.kill(
                    self.proc.pid,
                    19,
                )

                return True

            except Exception:
                return False

        return False

    def resume(self):
        if not self.proc:
            return

        self.paused = False

        if HAS_PSUTIL:
            try:
                psutil.Process(self.proc.pid).resume()

            except Exception:
                pass

        elif IS_LINUX:
            try:
                os.kill(
                    self.proc.pid,
                    18,
                )

            except Exception:
                pass

    def cancel(self):
        self.cancelled = True

        if self.proc:
            try:
                if HAS_PSUTIL:
                    process = psutil.Process(self.proc.pid)

                    for child in process.children(recursive=True):
                        child.terminate()

                self.proc.terminate()

            except Exception:
                pass


# --------------------------------------------------------------------------- #
# Background worker for Install/Update
# --------------------------------------------------------------------------- #
class ActionWorker(QThread):
    result = Signal(bool, str)

    def __init__(self, func):
        super().__init__()
        self.func = func

    def run(self):
        try:
            ok, message = self.func()

            self.result.emit(
                ok,
                message,
            )

        except Exception as e:
            self.result.emit(
                False,
                str(e),
            )


# --------------------------------------------------------------------------- #
# Stylesheet
# --------------------------------------------------------------------------- #
QSS = """
QWidget {
    background-color: #1e1f26;
    color: #e6e6e6;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QLineEdit {
    background-color: #2a2b35;
    border: 1px solid #3c3d4a;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f0f0f0;
}

QLineEdit:focus {
    border: 1px solid #6c8cff;
}

QPushButton {
    background-color: #2f3140;
    border: 1px solid #3c3d4a;
    border-radius: 6px;
    padding: 7px 16px;
    color: #f0f0f0;
}

QPushButton:hover {
    background-color: #3a3c4d;
}

QPushButton:pressed {
    background-color: #262735;
}

QPushButton:disabled {
    color: #6a6b78;
    background-color: #24252e;
}

QPushButton#primary {
    background-color: #4c6fff;
    border: none;
}

QPushButton#primary:hover {
    background-color: #5d7dff;
}

QPushButton#primary:disabled {
    background-color: #33395c;
    color: #7d84ad;
}

QPushButton#danger {
    background-color: #c94f4f;
    border: none;
}

QPushButton#danger:hover {
    background-color: #d95f5f;
}

QPushButton#danger:disabled {
    background-color: #4a3232;
    color: #a37d7d;
}

QProgressBar {
    background-color: #2a2b35;
    border: 1px solid #3c3d4a;
    border-radius: 6px;
    text-align: center;
    color: #f0f0f0;
    height: 20px;
}

QProgressBar::chunk {
    background-color: #4c6fff;
    border-radius: 6px;
}

QLabel#fileLabel {
    color: #9a9bab;
}

QDialog {
    background-color: #1e1f26;
}
"""


# --------------------------------------------------------------------------- #
# Main window
# --------------------------------------------------------------------------- #
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Fast Copy Tool")

        self.setWindowIcon(
            QIcon(resource_path("assets/icon.png"))
        )

        self.setFixedSize(
            600,
            200,
        )

        self.worker = None

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        root.setSpacing(10)

        root.setContentsMargins(
            14,
            14,
            14,
            10,
        )

        # ---- Top: directory selection ------------------------------------ #
        grid = QGridLayout()

        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        btn_src = QPushButton("Source")

        btn_src.clicked.connect(self.choose_src)

        self.src_edit = QLineEdit()

        self.src_edit.setPlaceholderText("Source directory path...")

        grid.addWidget(
            btn_src,
            0,
            0,
        )

        grid.addWidget(
            self.src_edit,
            0,
            1,
        )

        btn_dst = QPushButton("Destination")

        btn_dst.clicked.connect(self.choose_dst)

        self.dst_edit = QLineEdit()

        self.dst_edit.setPlaceholderText("Destination directory path...")

        grid.addWidget(
            btn_dst,
            1,
            0,
        )

        grid.addWidget(
            self.dst_edit,
            1,
            1,
        )

        grid.setColumnStretch(
            1,
            1,
        )

        root.addLayout(grid)

        # ---- Progress ---------------------------------------------------- #
        self.progress = QProgressBar()

        self.progress.setRange(
            0,
            100,
        )

        self.progress.setValue(0)

        root.addWidget(self.progress)

        self.file_label = QLabel("Ready.")

        self.file_label.setObjectName("fileLabel")

        self.file_label.setWordWrap(True)

        root.addWidget(self.file_label)

        root.addStretch(1)

        # ---- Bottom ------------------------------------------------------ #
        bottom = QHBoxLayout()

        left = QHBoxLayout()

        left.setSpacing(10)

        self.btn_copy = QPushButton("Copy")

        self.btn_copy.setObjectName("primary")

        self.btn_copy.clicked.connect(lambda: self.start(move=False))

        left.addWidget(self.btn_copy)

        self.btn_move = QPushButton("Move")

        self.btn_move.setObjectName("primary")

        self.btn_move.clicked.connect(lambda: self.start(move=True))

        left.addWidget(self.btn_move)

        self.btn_pause = QPushButton("Pause")

        self.btn_pause.setEnabled(False)

        self.btn_pause.clicked.connect(self.toggle_pause)

        left.addWidget(self.btn_pause)

        self.btn_cancel = QPushButton("Cancel")

        self.btn_cancel.setObjectName("danger")

        self.btn_cancel.setEnabled(False)

        self.btn_cancel.clicked.connect(self.cancel)

        left.addWidget(self.btn_cancel)

        bottom.addLayout(left)

        bottom.addStretch(1)

        self.btn_about = QPushButton("About")

        self.btn_about.clicked.connect(self.show_about)

        bottom.addWidget(self.btn_about)

        root.addLayout(bottom)

    # ---- Directory selection -------------------------------------------- #
    def choose_src(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Source Directory",
        )

        if directory:
            self.src_edit.setText(directory)

    def choose_dst(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Destination Directory",
        )

        if directory:
            self.dst_edit.setText(directory)

    # ---- Copy / Move ----------------------------------------------------- #
    def start(self, move):
        src = self.src_edit.text().strip()
        dst = self.dst_edit.text().strip()

        if not src or not dst:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please select a source and destination directory.",
            )
            return

        if not os.path.isdir(src):
            QMessageBox.critical(
                self,
                "Error",
                "The source directory does not exist.",
            )
            return

        if os.path.abspath(src) == os.path.abspath(dst):
            QMessageBox.critical(
                self,
                "Error",
                "The source and destination directories " "cannot be the same.",
            )
            return

        os.makedirs(
            dst,
            exist_ok=True,
        )

        tool = CopyTool()

        if not tool.is_installed():
            QMessageBox.warning(
                self,
                "Missing Tool",
                f"Operating system: "
                f"{'Windows' if IS_WINDOWS else 'Linux'}\n\n"
                f"'{tool.name}' is not installed.\n"
                "Please open [About] and install it first.",
            )
            return

        self.progress.setValue(0)

        self.file_label.setText("Preparing...")

        self.btn_copy.setEnabled(False)
        self.btn_move.setEnabled(False)

        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("Pause")

        self.btn_cancel.setEnabled(True)

        self.worker = CopyWorker(
            src,
            dst,
            move,
        )

        self.worker.progress.connect(self.progress.setValue)

        self.worker.file_update.connect(
            lambda name: self.file_label.setText(name[:160])
        )

        self.worker.speed_update.connect(self._on_speed_update)

        self.worker.finished_ok.connect(self._on_done)

        self.worker.error.connect(self._on_error)

        self.worker.start()

    def _on_speed_update(self, speed):
        if speed:
            self.file_label.setText(f"Transfer speed: {speed}")

    def _on_done(self, cancelled):
        self._reset_buttons()

        if cancelled:
            self.file_label.setText("Operation cancelled.")

        else:
            self.file_label.setText("Completed.")

            QMessageBox.information(
                self,
                "Done",
                "Copy/move operation completed successfully.",
            )

    def _on_error(self, message):
        self._reset_buttons()

        QMessageBox.critical(
            self,
            "Error",
            message,
        )

    def _reset_buttons(self):
        self.btn_copy.setEnabled(True)
        self.btn_move.setEnabled(True)

        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("Pause")

        self.btn_cancel.setEnabled(False)

    # ---- Pause / Cancel -------------------------------------------------- #
    def toggle_pause(self):
        if not self.worker:
            return

        if self.worker.paused:
            self.worker.resume()

            self.btn_pause.setText("Pause")

        else:
            ok = self.worker.pause()

            if ok:
                self.btn_pause.setText("Resume")

            else:
                QMessageBox.warning(
                    self,
                    "Not Supported",
                    "Pausing is not supported on this system.\n\n"
                    "On Windows, install psutil with:\n"
                    "pip install psutil",
                )

    def cancel(self):
        if self.worker:
            self.worker.cancel()

    # ---- About ----------------------------------------------------------- #
    def show_about(self):
        dialog = AboutDialog(self)
        dialog.exec()


# --------------------------------------------------------------------------- #
# About dialog
# --------------------------------------------------------------------------- #
class AboutDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("About")

        self.setFixedSize(
            400,
            160,
        )

        self.tool = CopyTool()
        self._action_worker = None

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            18,
            18,
            18,
            14,
        )

        layout.setSpacing(14)

        self.info_label = QLabel()

        self.info_label.setWordWrap(True)

        layout.addWidget(
            self.info_label,
            1,
        )

        buttons = QHBoxLayout()

        self.btn_install = QPushButton("Install")

        self.btn_install.setObjectName("primary")

        self.btn_install.clicked.connect(self.do_install)

        buttons.addWidget(self.btn_install)

        self.btn_update = QPushButton("Update")

        self.btn_update.clicked.connect(self.do_update)

        buttons.addWidget(self.btn_update)

        btn_close = QPushButton("Close")

        btn_close.clicked.connect(self.close)

        buttons.addWidget(btn_close)

        layout.addLayout(buttons)

        self.refresh()

    def refresh(self):
        installed = self.tool.is_installed()

        version = self.tool.get_version() if installed else None

        package_manager = self.tool.get_package_manager() if IS_LINUX else None

        if IS_WINDOWS:
            os_name = "Windows"
        elif IS_LINUX:
            os_name = "Linux"
        else:
            os_name = platform.system()

        lines = [
            f"Operating System: {os_name}",
            f"Copy Tool: {self.tool.name}",
            f"Status: {'Installed' if installed else 'NOT INSTALLED'}",
        ]

        if IS_LINUX:
            lines.append(f"Package Manager: " f"{package_manager or 'Not detected'}")

        if installed:
            lines.append(f"Version: {version or 'Unknown'}")
        else:
            lines.append(
                f"'{self.tool.name}' is not available "
                "on this system. Click [Install] to install it."
            )

        self.info_label.setText("\n".join(lines))

        self.btn_install.setEnabled(not installed)

        self.btn_update.setEnabled(installed)

    def _run_bg(self, func, title):
        self.btn_install.setEnabled(False)
        self.btn_update.setEnabled(False)

        self.info_label.setText("Processing, please wait...")

        self._action_worker = ActionWorker(func)

        def on_result(ok, message):
            if ok:
                QMessageBox.information(
                    self,
                    title,
                    message,
                )
            else:
                QMessageBox.critical(
                    self,
                    title,
                    message,
                )

            self.refresh()

        self._action_worker.result.connect(on_result)

        self._action_worker.start()

    def do_install(self):
        self._run_bg(
            self.tool.install,
            "Install",
        )

    def do_update(self):
        self._run_bg(
            self.tool.update,
            "Update",
        )


# --------------------------------------------------------------------------- #
# Application entry point
# --------------------------------------------------------------------------- #
def main():
    app = QApplication(sys.argv)

    app.setStyleSheet(QSS)

    window = MainWindow()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
