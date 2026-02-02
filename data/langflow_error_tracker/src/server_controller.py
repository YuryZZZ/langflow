"""Manages the Langflow server process, capturing its output."""
import io
import subprocess
import threading
import time

from loguru import logger

class LangflowServerController:
    """Controls the Langflow server process, including starting, stopping, and capturing its output."""

    def __init__(self, langflow_command: str = "python -m langflow", port: int = 7860):
        """Initializes the LangflowServerController.

        Args:
            langflow_command: The command used to start Langflow.
            port: The port on which Langflow server runs.
        """
        self.langflow_command = langflow_command
        self.port = port
        self.process = None
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()
        self.stdout_reader_thread = None
        self.stderr_reader_thread = None
        self._running = False

    def _read_stream(self, stream, buffer):
        while self._running:
            line = stream.readline()
            if line:
                buffer.write(line)
            else:
                # Small sleep to prevent busy-waiting when stream is empty
                time.sleep(0.01)
        # Read any remaining content after the loop exits
        remaining = stream.read()
        if remaining:
            buffer.write(remaining)

    def start_server(self) -> bool:
        """Starts the Langflow server as a subprocess."""
        if self.process and self.process.poll() is None:
            logger.debug("Langflow server is already running.")
            return False

        logger.info(f"Starting Langflow server on port {self.port}...")
        try:
            # It's generally safer to avoid shell=True for security reasons.
            # Instead, pass the command as a list of arguments.
            # However, if the command itself contains shell-specific syntax,
            # it might be necessary. For now, we'll keep it as is but note the warning.
            command_parts = self.langflow_command.split()
            command_parts.extend(["--port", str(self.port)])

            self.process = subprocess.Popen(
                command_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,  # Decode stdout/stderr as text
                bufsize=1,  # Line-buffered output
                universal_newlines=True,  # Ensure cross-platform newline handling
            )
            self._running = True

            # Start threads to read stdout and stderr asynchronously
            self.stdout_reader_thread = threading.Thread(
                target=self._read_stream, args=(self.process.stdout, self.stdout_buffer)
            )
            self.stderr_reader_thread = threading.Thread(
                target=self._read_stream, args=(self.process.stderr, self.stderr_buffer)
            )
            self.stdout_reader_thread.daemon = (
                True  # Allow program to exit even if thread is running
            )
            self.stderr_reader_thread.daemon = True
            self.stdout_reader_thread.start()
            self.stderr_reader_thread.start()

            logger.info("Langflow server process started.")
            return True
        except Exception as e:
            logger.error(f"Failed to start Langflow server: {e}")
            return False

    def stop_server(self) -> bool:
        """Stops the Langflow server process gracefully."""
        if self.process and self.process.poll() is None:
            logger.info("Stopping Langflow server...")
            try:
                self._running = False  # Signal threads to stop
                # Give threads a moment to finish reading
                if self.stdout_reader_thread:
                    self.stdout_reader_thread.join(timeout=1)
                if self.stderr_reader_thread:
                    self.stderr_reader_thread.join(timeout=1)

                self.process.terminate()  # or .kill()
                self.process.wait(timeout=10)  # Wait for process to terminate
                logger.info("Langflow server stopped.")
                return True
            except subprocess.TimeoutExpired:
                logger.warning("Server did not terminate in time, forcing kill.")
                self.process.kill()
                self.process.wait()
                logger.info("Langflow server forcefully killed.")
                return True
            except Exception as e:
                logger.error(f"Failed to stop Langflow server: {e}")
                return False
        else:
            logger.debug("Langflow server is not running.")
            return False

    def get_output(self) -> tuple[str, str]:
        """Returns the current content of stdout and stderr buffers, and clears them."""
        stdout_content = self.stdout_buffer.getvalue()
        stderr_content = self.stderr_buffer.getvalue()
        self.stdout_buffer.truncate(0)
        self.stdout_buffer.seek(0)
        self.stderr_buffer.truncate(0)
        self.stderr_buffer.seek(0)
        return stdout_content, stderr_content

    def is_running(self) -> bool:
        """Checks if the Langflow server process is currently running."""
        return self.process is not None and self.process.poll() is None