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
    size = float(size)

    if size < 1024:
        return f"{size:.0f} B"

    if size < 1024**2:
        return f"{size / 1024:.1f} KB"

    if size < 1024**3:
        return f"{size / 1024 ** 2:.1f} MB"

    if size < 1024**4:
        return f"{size / 1024 ** 3:.2f} GB"

    return f"{size / 1024 ** 4:.2f} TB"


def format_duration(seconds):
    seconds = float(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours >= 1:
        return f"{hours:.0f}h {minutes:.0f}m {seconds:.2f}s"

    if minutes >= 1:
        return f"{minutes:.0f}m {seconds:.2f}s"

    return f"{seconds:.2f}s"


def get_process_write_bytes(pid):
    """
    Return the total number of bytes a process (and all of its live
    descendants) has actually caused to be written to the storage
    layer, as reported by the kernel — the same figure exposed via
    /proc/<pid>/io's 'write_bytes' field on Linux, or
    GetProcessIoCounters() on Windows.

    This is used instead of re-scanning the destination directory: it's
    a single cheap counter read per process rather than an O(number of
    files) directory walk, and it comes straight from the kernel rather
    than from parsing a tool's stdout.

    rsync (for local transfers) forks itself into a sender and a
    generator/receiver, so the byte-writing work happens in a child
    process, not necessarily the one we launched — hence summing over
    descendants too. robocopy on Windows is single-process (it just
    uses multiple threads internally), so there normally are no
    descendants to add.

    Returns None if psutil isn't available or the counters can't be
    read (e.g. the process already exited, or the platform/kernel
    doesn't expose them).
    """

    if not HAS_PSUTIL:
        return None

    try:
        root_process = psutil.Process(pid)
    except Exception:
        return None

    processes = [root_process]

    try:
        processes.extend(root_process.children(recursive=True))
    except Exception:
        pass

    total = 0
    got_any = False

    for process in processes:
        try:
            total += process.io_counters().write_bytes
            got_any = True
        except Exception:
            continue

    return total if got_any else None


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
                f"rsync was installed successfully using {package_manager}.",
            )

        return (
            False,
            f"Failed to install rsync using {package_manager}.\n\n{message}",
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
                f"rsync was updated successfully using {package_manager}.\n\n"
                "The package was already up to date if no changes were needed.",
            )

        return (
            False,
            f"Failed to update rsync using {package_manager}.\n\n{message}",
        )

    def build_command(self, src, dst, move):
        if IS_WINDOWS:
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

        command = [
            "rsync",
            "-a",
            # name1 prints each transferred file's relative path as it
            # goes, which --info=progress2 alone does NOT do. Progress
            # itself is measured separately by reading the kernel's own
            # I/O accounting for the rsync process (see
            # CopyWorker._io_poll_loop), not by parsing rsync's output.
            "--info=name1",
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
    stats_update = Signal(str, str, str)
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
        self.total_files = 0

        self.transferred_size = 0
        self.elapsed_seconds = 0
        self.status = "Preparing"

        self.last_progress = 0

        self.transfer_started_at = 0
        self.last_speed_time = 0
        self.last_speed_bytes = 0
        self.current_speed = 0

        # Progress is driven by reading the kernel's own I/O accounting
        # for the copy process (bytes actually written to storage), not
        # by parsing rsync/robocopy's own self-reported counters and not
        # by re-scanning the destination directory. See _io_poll_loop.
        self.write_bytes_baseline = 0
        self.io_tracking_available = HAS_PSUTIL
        self._stop_poll = threading.Event()
        self._io_poll_thread = None

    def run(self):
        started_at = time.monotonic()

        self.transfer_started_at = started_at
        self.last_speed_time = started_at
        self.last_speed_bytes = 0
        self.current_speed = 0

        self.status = "Running"

        try:
            if not self.tool.is_installed():
                self.status = "Error"
                self.elapsed_seconds = time.monotonic() - started_at

                self.error.emit(
                    f"'{self.tool.name}' is not installed. "
                    "Open [About] to install it."
                )

                return

            # Scan source once before starting the transfer.
            self.file_update.emit("Scanning source...")

            self.total_size = get_dir_size(self.src)
            self.total_files = self._count_files(self.src)

            self.transferred_size = 0

            self.last_progress = 0

            self.progress.emit(0)

            self._update_stats(force=True)

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
                popen_kwargs["creationflags"] = (
                    subprocess.CREATE_NO_WINDOW
                )

            self.proc = subprocess.Popen(
                command,
                **popen_kwargs,
            )

            self._start_io_poller()

            if IS_LINUX:
                self._run_rsync()
            else:
                self._run_robocopy()

            if self.proc.poll() is None:
                # The line-reading loop above has exited (pipe closed) but
                # the process itself may still be finishing up on disk
                # (e.g. flushing writes to a slower external drive). Let
                # the user know we're still working instead of leaving the
                # UI looking frozen at "99%". The I/O poller keeps running
                # through this, so the progress bar keeps moving too as
                # long as bytes are still being written.
                self.file_update.emit(
                    "Finishing up — waiting for the copy process to complete..."
                )

                self.proc.wait()

            self._stop_io_poller()

            # ----------------------------------------------------------- #
            # Process has actually terminated here.
            # Do NOT consider 100% complete before this point.
            # ----------------------------------------------------------- #

            if self.cancelled:
                self.status = "Cancelled"
                self.elapsed_seconds = (
                    time.monotonic() - started_at
                )

                self._update_stats(
                    speed=0,
                    force=True,
                )

                self.finished_ok.emit(True)
                return

            returncode = self.proc.returncode

            if IS_WINDOWS:
                # Robocopy exit codes 0-7 indicate success or
                # success with differences.
                if returncode >= 8:
                    self.status = "Error"

                    self.elapsed_seconds = (
                        time.monotonic() - started_at
                    )

                    self._update_stats(
                        speed=0,
                        force=True,
                    )

                    self.error.emit(
                        f"Robocopy exited with error code "
                        f"{returncode}."
                    )

                    return

            else:
                if returncode != 0:
                    self.status = "Error"

                    self.elapsed_seconds = (
                        time.monotonic() - started_at
                    )

                    self._update_stats(
                        speed=0,
                        force=True,
                    )

                    self.error.emit(
                        f"rsync exited with error code "
                        f"{returncode}."
                    )

                    return

            # Linux move cleanup happens only after rsync succeeds.
            if self.move and IS_LINUX:
                self.file_update.emit("Cleaning up empty source folders...")

                self._cleanup_empty_source_dirs()

            # ----------------------------------------------------------- #
            # ONLY NOW is the operation actually complete.
            # ----------------------------------------------------------- #

            self.transferred_size = self.total_size

            self.elapsed_seconds = (
                time.monotonic() - started_at
            )

            self.status = "Success"

            self._emit_progress(100)

            self._update_stats(
                speed=0,
                force=True,
            )

            self.file_update.emit("Completed.")

            self.finished_ok.emit(False)

        except Exception as e:
            self._stop_io_poller()

            self.status = "Error"

            self.elapsed_seconds = (
                time.monotonic() - started_at
            )

            self._update_stats(
                speed=0,
                force=True,
            )

            self.error.emit(str(e))

    def _update_stats(self, speed=None, force=False):
        """
        Update transfer speed, transferred size and total size.

        Speed is calculated from the amount transferred between
        updates instead of average bytes / total elapsed time.
        """

        now = time.monotonic()

        if speed is None:
            elapsed = now - self.last_speed_time

            if elapsed >= 0.25:
                byte_delta = (
                    self.transferred_size
                    - self.last_speed_bytes
                )

                self.current_speed = (
                    max(0, byte_delta) / elapsed
                )

                self.last_speed_bytes = (
                    self.transferred_size
                )

                self.last_speed_time = now

        else:
            self.current_speed = max(0, speed)

            if force:
                self.last_speed_bytes = (
                    self.transferred_size
                )

                self.last_speed_time = now

        self.stats_update.emit(
            format_size(self.current_speed) + "/s",
            format_size(self.transferred_size),
            format_size(self.total_size),
        )

    def _emit_progress(self, percentage):
        """
        Emit progress.

        100% is reserved for the moment after the external
        copy process has actually terminated successfully.
        """

        percentage = max(
            0,
            min(
                100,
                int(percentage),
            ),
        )

        # Never allow the transfer parser to report 100%.
        # 100% is emitted manually after proc.wait().
        if self.status == "Running":
            percentage = min(percentage, 99)

        if percentage < self.last_progress:
            return

        self.last_progress = percentage

        self.progress.emit(percentage)

    def _update_progress_from_bytes(self, transferred_bytes):
        """
        Update progress using transferred bytes against
        the pre-scanned total size.
        """

        if self.total_size <= 0:
            return

        transferred_bytes = max(
            0,
            min(
                self.total_size,
                int(transferred_bytes),
            ),
        )

        if transferred_bytes < self.transferred_size:
            return

        self.transferred_size = transferred_bytes

        self._update_stats()

        percentage = (
            self.transferred_size
            / self.total_size
            * 100
        )

        self._emit_progress(percentage)

    # ---- I/O-counter polling (source of truth for progress) ----------- #
    def _start_io_poller(self):
        """
        Start a background thread that periodically reads how many
        bytes the copy process (and any children it forked, e.g.
        rsync's sender/receiver) have actually written to the storage
        layer, according to the kernel. This drives the progress bar
        instead of parsing rsync/robocopy's own stdout, and instead of
        re-scanning the destination directory (too expensive for large
        trees).

        Requires psutil. If it isn't installed, progress falls back to
        just the filenames streaming by, plus the final jump to 100%
        when the process exits — no live percentage in between.
        """

        if not self.io_tracking_available:
            return

        baseline = get_process_write_bytes(self.proc.pid)

        self.write_bytes_baseline = baseline if baseline is not None else 0

        self._stop_poll.clear()

        self._io_poll_thread = threading.Thread(
            target=self._io_poll_loop,
            daemon=True,
        )

        self._io_poll_thread.start()

    def _stop_io_poller(self):
        self._stop_poll.set()

        if self._io_poll_thread is not None:
            self._io_poll_thread.join(timeout=2)
            self._io_poll_thread = None

    def _io_poll_loop(self):
        poll_interval = 0.5

        while not self._stop_poll.is_set():
            self._poll_io_once()

            if self._stop_poll.wait(poll_interval):
                break

        # One last read in case the process finished in between the
        # previous tick and the stop signal.
        self._poll_io_once()

    def _poll_io_once(self):
        written_total = get_process_write_bytes(self.proc.pid)

        if written_total is None:
            # The process (and its children) may have already exited
            # and been reaped between polls — nothing to read anymore.
            # transferred_size simply stops advancing here; it gets
            # snapped to total_size once the operation is confirmed
            # complete.
            return

        written = max(0, written_total - self.write_bytes_baseline)

        self._update_progress_from_bytes(written)

    # ---- Output readers (filenames only — see poller above for progress) #
    def _run_rsync(self):
        """
        Read rsync's output for the name of each file as it's
        transferred (via --info=name1). Progress itself comes from
        _io_poll_loop, not from anything parsed here.
        """

        for raw_line in self.proc.stdout:
            if self.cancelled:
                break

            line = raw_line.strip()

            if not line:
                continue

            self.file_update.emit(line[:160])

    def _run_robocopy(self):
        """
        Read robocopy's output for the name of each file as it's
        transferred. Progress itself comes from _io_poll_loop, not
        from robocopy's own per-file percentages.
        """
        for raw_line in self.proc.stdout:
            if self.cancelled:
                break

            line = raw_line.strip()

            if not line:
                continue

            lower = line.lower()

            display_line = re.sub(
                r"\s+",
                " ",
                line,
            ).strip()

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

            file_progress = re.search(
                r"^\s*(\d+(?:\.\d+)?)%\s+" r"(.+?)\s+" r"(\d+)\s+" r"(.+)$",
                line,
            )

            if file_progress:
                filename = file_progress.group(4).strip()

                self.file_update.emit(filename[:160])

                continue

            if (
                "new file" in lower
                or "newer" in lower
                or "older" in lower
                or "extra file" in lower
                or "modified" in lower
            ):
                self.file_update.emit(display_line[:160])

                continue

            if "\\" in line:
                self.file_update.emit(display_line[:160])

    def _count_files(self, path):
        """Count source files once during the pre-scan."""
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

        self.setWindowIcon(QIcon(resource_path("assets/icon.png")))

        self.setFixedSize(
            600,
            220,
        )

        self.worker = None
        self.current_operation = None

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

        # Current file being copied/moved.
        self.file_label = QLabel("Ready.")

        self.file_label.setObjectName("fileLabel")

        self.file_label.setWordWrap(True)

        self.file_label.setOpenExternalLinks(False)

        self.file_label.linkActivated.connect(self._show_details)

        root.addWidget(self.file_label)

        # Transferred size / total size + speed, e.g.:
        # "512.0 MB of 4.20 GB (speed: 85.3 MB/s)"
        self.stats_label = QLabel("0 B of 0 B (speed: 0 B/s)")

        self.stats_label.setObjectName("fileLabel")

        root.addWidget(self.stats_label)

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
                "The source and destination directories cannot be the same.",
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
                f"'{tool.name}' is not installed.\n"
                "Please open [About] and install it first.",
            )

            return

        self.current_operation = "Move" if move else "Copy"

        self.progress.setValue(0)

        self.stats_label.setText("0 B of 0 B (speed: 0 B/s)")

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
            lambda name: self.file_label.setText(name[:150])
        )

        self.worker.stats_update.connect(self._on_stats_update)

        self.worker.finished_ok.connect(self._on_done)

        self.worker.error.connect(self._on_error)

        self.worker.start()

    def _on_stats_update(
        self,
        speed,
        transferred,
        total,
    ):
        self.stats_label.setText(
            f"{transferred} of {total} (speed: {speed})"
        )

    def _on_done(self, cancelled):
        operation = self.current_operation or "Operation"

        self._reset_buttons()

        if cancelled:
            self.file_label.setText("Cancelled.")

            return

        # Make absolutely sure the UI ends in:
        # total of total (speed: 0 B/s)
        if self.worker:
            total_text = format_size(self.worker.total_size)

            self.stats_label.setText(
                f"{total_text} of {total_text} (speed: 0 B/s)"
            )

        details = self._details_text("Success")

        self.file_label.setText(
            "Completed&nbsp;&nbsp;" '<a href="details">[Detail]</a>'
        )

        QMessageBox.information(
            self,
            f"{operation} completed",
            f"{operation} operation completed successfully.\n\n" f"{details}",
        )

    def _on_error(self, message):
        operation = self.current_operation or "Operation"

        self._reset_buttons()

        details = self._details_text("Error")

        self.file_label.setText("Failed&nbsp;&nbsp;" '<a href="details">[Detail]</a>')

        QMessageBox.critical(
            self,
            f"{operation} error",
            f"{message}\n\n{details}",
        )

    def _details_text(self, status):
        if not self.worker:
            return f"Status: {status}"

        return (
            f"Status: {status}\n"
            f"Files: {self.worker.total_files}\n"
            f"Size: {format_size(self.worker.transferred_size)} / "
            f"{format_size(self.worker.total_size)}\n"
            f"Time: {format_duration(self.worker.elapsed_seconds)}"
        )

    def _show_details(self, _link):
        operation = self.current_operation or "Operation"

        status = self.worker.status if self.worker else "Unknown"

        QMessageBox.information(
            self,
            f"{operation} details",
            self._details_text(status),
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
            f"Status: " f"{'Installed' if installed else 'NOT INSTALLED'}",
        ]

        if IS_LINUX:
            lines.append(f"Package Manager: " f"{package_manager or 'Not detected'}")

        if installed:
            lines.append(f"Version: " f"{version or 'Unknown'}")

        else:
            lines.append(
                f"'{self.tool.name}' is not available "
                "on this system. Click [Install] to install it."
            )

        lines.append(
            "Live Progress: "
            + (
                "Enabled (via psutil)"
                if HAS_PSUTIL
                else "Disabled — install psutil for a live progress "
                "bar (pip install psutil). Without it, progress "
                "only jumps to 100% once the operation finishes."
            )
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