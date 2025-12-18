"""
UbShot - A Shottr-like Screenshot & Annotation Tool for Ubuntu.

This is the main entry point for the application.
Run with: python -m src.app
"""

import sys
import os
import fcntl
import signal
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.core.app_core import AppCore
from src.services.logging_service import get_logger, setup_logging


# Lock file for single-instance enforcement
LOCK_FILE = Path.home() / ".cache" / "ubshot" / "ubshot.lock"

# Global app reference for signal handlers
_app: QApplication = None
_app_core: AppCore = None
_should_quit = False


def acquire_single_instance_lock() -> bool:
    """
    Acquire a file lock to ensure only one instance runs.
    
    Returns:
        True if lock acquired (first instance), False if another instance exists.
    """
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Open lock file (create if doesn't exist)
        lock_fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_RDWR)
        
        # Try to acquire exclusive lock (non-blocking)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        
        # Write our PID to the lock file
        os.ftruncate(lock_fd, 0)
        os.write(lock_fd, str(os.getpid()).encode())
        
        # Keep the file descriptor open to maintain the lock
        # Store it as a module-level variable to prevent garbage collection
        global _lock_fd
        _lock_fd = lock_fd
        
        return True
    except (OSError, IOError):
        # Lock already held by another process
        return False


def cleanup_and_quit(signum, frame):
    """Handle termination signals to properly clean up tray icon."""
    global _should_quit
    _should_quit = True


def check_for_quit():
    """Timer callback to check if we should quit."""
    global _should_quit, _app, _app_core
    
    if _should_quit:
        logger = get_logger(__name__)
        logger.info("Signal received, cleaning up tray and quitting...")
        
        # Hide tray icon before quitting
        if _app_core and hasattr(_app_core, '_tray_service') and _app_core._tray_service:
            _app_core._tray_service.hide()
        
        # Quit the application
        if _app:
            _app.quit()


def main() -> int:
    """
    Main entry point for UbShot application.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    global _app, _app_core
    
    # Initialize basic logging first to catch early errors
    setup_logging()
    logger = get_logger(__name__)

    try:
        logger.info("Starting UbShot application...")
        
        # Single-instance check
        if not acquire_single_instance_lock():
            logger.warning("Another instance of UbShot is already running. Exiting.")
            print("UbShot is already running. Check your system tray.")
            return 1

        # Create the Qt application
        _app = QApplication(sys.argv)
        _app.setApplicationName("UbShot")
        _app.setOrganizationName("UbShot")
        _app.setApplicationVersion("0.1.0")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, cleanup_and_quit)
        signal.signal(signal.SIGTERM, cleanup_and_quit)
        
        # Timer to poll for quit signal (Qt event loop blocks Python signals)
        quit_timer = QTimer()
        quit_timer.timeout.connect(check_for_quit)
        quit_timer.start(100)  # Check every 100ms

        # Initialize the application core (this sets up everything)
        _app_core = AppCore(_app)

        logger.info("UbShot initialization complete. Entering event loop...")

        # Run the application event loop
        exit_code = _app.exec()

        logger.info(f"UbShot exiting with code {exit_code}")
        return exit_code

    except Exception as e:
        # Log any unhandled exceptions
        logger.critical(f"Fatal error during startup: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

