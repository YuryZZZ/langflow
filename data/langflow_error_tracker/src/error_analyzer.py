"""Analyzes and summarizes error data."""
import datetime
from collections import Counter



class ErrorAnalyzer:
    """Analyzes and summarizes error data from detected errors."""

    def __init__(self):
        """Initializes the ErrorAnalyzer with a severity map for error types."""
        # Define a simple severity mapping for error types
        self._severity_map = {
            "Python Traceback": "High",
            "Unclassified Traceback": "High",
            "Runtime Error": "High",
            "Connection Error": "High",
            "Assertion Error": "Medium",
            "Validation Error": "Medium",
            "General Error": "Medium",
            "Warning": "Low",
        }

    def analyze_errors(self, errors: list[dict]):
        """Analyzes a list of raw error dictionaries and generates a summary report."""
        if not errors:
            return {
                "total_errors": 0,
                "error_types_summary": {},
                "unique_errors": [],
                "analysis_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }

        total_errors = len(errors)
        error_types = Counter([error["type"] for error in errors])

        unique_errors_list = []
        unique_messages = set()

        for error in errors:
            error_message = error.get("message", "N/A")
            if error_message not in unique_messages:
                unique_messages.add(error_message)
                severity = self._severity_map.get(error["type"], "Unknown")
                unique_errors_list.append({
                    "type": error["type"],
                    "message": error_message,
                    "severity": severity,
                    "first_occurrence": error["timestamp"],
                    "full_log_sample": error.get("full_log", "N/A")
                })

        return {
            "total_errors": total_errors,
            "error_types_summary": dict(error_types),
            "unique_errors": unique_errors_list,
            "analysis_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

