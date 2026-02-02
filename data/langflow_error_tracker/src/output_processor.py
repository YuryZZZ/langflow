"""Processes raw output to detect and classify errors."""
import re
import datetime

class ErrorProcessor:
    """Processes raw output (stdout and stderr) to detect and classify errors based on predefined patterns."""

    def __init__(self):
        """Initializes the ErrorProcessor with regex patterns for error detection."""
        # Define regex patterns for various error types
        self._error_patterns = {
            "Python Traceback": r"Traceback \(most recent call last\):\\n.*?\\n([a-zA-Z_]+\w*Error|Exception): .*",
            "Runtime Error": r"(?:RuntimeError|ValueError|TypeError|KeyError|AttributeError|ImportError|NameError): ",
            "Connection Error": (
                r"(?:ConnectionRefusedError|TimeoutError|HTTPConnectionPool|Max retries exceeded with url): "
            ),
            "Assertion Error": r"AssertionError: ",
            "Validation Error": r"(?:ValidationError|Invalid|bad|failed): ",
            "General Error": r"[Ee]rror: |ERROR: |ERR: ",
            "Warning": r"[Ww]arning: |WARNING: ",
        }
        self._compiled_patterns = {
            name: re.compile(pattern, re.DOTALL)
            if name == "Python Traceback"
            else re.compile(pattern)
            for name, pattern in self._error_patterns.items()
        }
        self.detected_errors = []
        self._current_traceback = []
        self._in_traceback = False

    def process_output(self, stdout: str, stderr: str):
        """Processes the given stdout and stderr, detecting and storing any errors."""
        self.detected_errors.clear() # Clear previous detections
        self._current_traceback = []
        self._in_traceback = False

        combined_output = (stdout.splitlines() + stderr.splitlines())

        for line in combined_output:
            self._process_line(line)

    def _process_line(self, line):
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Check for start/continuation of a traceback
        if "Traceback (most recent call last):" in line:
            self._in_traceback = True
            self._current_traceback = [line]
            return
        
        if self._in_traceback:
            self._current_traceback.append(line)
            # Check if traceback ends (e.g., empty line or another error/non-traceback line)
            if not line.strip() or any(
                re.match(p, line)
                for p in self._compiled_patterns.values()
                if p.pattern != self._error_patterns["Python Traceback"]
            ):
                full_traceback = "\\n".join(self._current_traceback)
                match = self._compiled_patterns["Python Traceback"].search(full_traceback)
                if match:
                    error_message = match.group(0).splitlines()[-1] # Last line of the traceback
                    self.detected_errors.append({
                        "timestamp": timestamp,
                        "type": "Python Traceback",
                        "message": error_message.strip(),
                        "full_log": full_traceback.strip()
                    })
                else:
                    # If it's a traceback but doesn't match the full pattern, log as general error
                    self.detected_errors.append({
                        "timestamp": timestamp,
                        "type": "Unclassified Traceback",
                        "message": "Unclassified traceback detected",
                        "full_log": full_traceback.strip()
                    })
                self._in_traceback = False
                self._current_traceback = []
                return # Avoid double processing the line that ended the traceback

        # If not in a traceback, check for other error patterns
        if not self._in_traceback:
            for error_type, pattern in self._compiled_patterns.items():
                if error_type == "Python Traceback": # Skip full traceback pattern here
                    continue
                if pattern.search(line):
                    self.detected_errors.append({
                        "timestamp": timestamp,
                        "type": error_type,
                        "message": line.strip(),
                        "full_log": line.strip()
                    })
                    break # Only classify one error type per line

    def get_errors(self):
        """Returns the list of detected errors."""
        return self.detected_errors

    def has_errors(self):
        """Checks if any errors have been detected."""
        return len(self.detected_errors) > 0

