"""Handles reporting and persistence of error data."""
import json
from pathlib import Path

from loguru import logger

class ErrorReporterAndPersister:
    """Manages the reporting and persistence of error data, including raw errors, analysis reports, and text summaries."""

    def __init__(self, base_dir: str = "data/langflow_error_tracker"):
        """Initializes the reporter with base directories for saving data and reports."""
        self.base_dir = Path(base_dir)
        self.raw_errors_filepath = self.base_dir / "data" / "raw_errors.jsonl"
        self.summary_report_filepath = self.base_dir / "logs" / "summary_report.json"
        self.text_report_filepath = self.base_dir / "logs" / "summary_report.txt"
        self._ensure_dirs_exist()

    def _ensure_dirs_exist(self):
        """Ensures that the necessary directories for storing raw errors and reports exist."""
        self.raw_errors_filepath.parent.mkdir(parents=True, exist_ok=True)
        self.summary_report_filepath.parent.mkdir(parents=True, exist_ok=True)

    def save_raw_errors(self, errors: list[dict]):
        """Appends raw error dictionaries to a JSONL file."""
        if not errors:
            logger.debug("No raw errors to save.")
            return
        try:
            with self.raw_errors_filepath.open("a", encoding="utf-8") as f:
                for error in errors:
                    f.write(json.dumps(error) + "\n")
            logger.info(f"Successfully appended {len(errors)} raw errors to {self.raw_errors_filepath}")
        except OSError as e:
            logger.error(f"Failed to save raw errors: {e}")

    def save_analysis_report(self, report: dict):
        """Saves the analyzed error report as a JSON file."""
        try:
            with self.summary_report_filepath.open("w", encoding="utf-8") as f:
                json.dump(report, f, indent=4)
            logger.info(f"Successfully saved analysis report to {self.summary_report_filepath}")
        except OSError as e:
            logger.error(f"Failed to save analysis report: {e}")

    def generate_summary_report_text(self, analysis_report: dict) -> str:
        """Generates a human-readable text summary of the analysis report."""
        report_lines = []
        report_lines.append(f"Error Analysis Report - {analysis_report.get("analysis_timestamp", "N/A")}")
        report_lines.append("=" * 30)
        report_lines.append(f"Total Errors Detected: {analysis_report.get("total_errors", 0)}")
        report_lines.append("\nError Types Summary:")
        if analysis_report.get("error_types_summary"):
            for err_type, count in analysis_report["error_types_summary"].items():
                report_lines.append(f"- {err_type}: {count}")
        else:
            report_lines.append("  No errors by type to summarize.")

        report_lines.append("\nUnique Errors:")
        if analysis_report.get("unique_errors"):
            for i, unique_err in enumerate(analysis_report["unique_errors"]):
                report_lines.append(f"  {i+1}. Type: {unique_err.get("type", "N/A")}")
                report_lines.append(f"     Message: {unique_err.get("message", "N/A")}")
                report_lines.append(f"     Severity: {unique_err.get("severity", "N/A")}")
                report_lines.append(
                    f"     First Occurrence: {unique_err.get("first_occurrence", "N/A")}"
                )
                report_lines.append(
                    f"     Full Log Sample: {unique_err.get("full_log_sample", "N/A")[:200]}..."
                )
        else:
            report_lines.append("  No unique errors to list.")

        return "\n".join(report_lines)

    def save_text_report(self, report_text: str):
        """Saves the human-readable text report to a file."""
        try:
            with self.text_report_filepath.open("w", encoding="utf-8") as f:
                f.write(report_text)
            logger.info(f"Successfully saved text report to {self.text_report_filepath}")
        except OSError as e:
            logger.error(f"Failed to save text report: {e}")

