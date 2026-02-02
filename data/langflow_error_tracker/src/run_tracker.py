import argparse
import signal
import sys
import threading
import time

from loguru import logger

from .error_analyzer import ErrorAnalyzer
from .output_processor import ErrorProcessor
from .reporter_and_persister import ErrorReporterAndPersister
from .server_controller import LangflowServerController

def main():
    """Main function to run the Langflow Error Tracker and Reporter."""
    parser = argparse.ArgumentParser(description="Langflow Error Tracker and Reporter")
    parser.add_argument(
        "--port", type=int, default=7860, help="Port for the Langflow server to run on."
    )
    parser.add_argument(
        "--polling-interval",
        type=int,
        default=5,
        help="Interval in seconds to poll server output.",
    )
    parser.add_argument(
        "--run-duration",
        type=int,
        default=60,
        help="Duration in seconds to run the tracker. Use 0 for infinite run.",
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default="data/langflow_error_tracker",
        help="Base directory for logs and data.",
    )
    args = parser.parse_args()

    controller = LangflowServerController(port=args.port)
    processor = ErrorProcessor()
    analyzer = ErrorAnalyzer()
    reporter = ErrorReporterAndPersister(base_dir=args.base_dir)

    # Signal handler for graceful shutdown
    stop_event = threading.Event() # Use threading.Event for cross-thread signaling

    def signal_handler(signum, frame):
        logger.info("Signal received, attempting graceful shutdown...")
        stop_event.set()

    # Register signal handlers for graceful exit
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Initializing Langflow error tracker...")

    try:
        if not controller.start_server():
            logger.error("Exiting due to server startup failure.")
            sys.exit(1)

        start_time = time.time()
        iteration = 0

        while not stop_event.is_set():
            iteration += 1
            logger.info(
                f"--- Iteration {iteration} (Time: {time.time() - start_time:.2f}s) ---"
            )
            stdout, stderr = controller.get_output()

            if stdout:
                logger.info("-- STDOUT --")
                logger.info(stdout.strip())
            if stderr:
                logger.error("-- STDERR --")
                logger.error(stderr.strip())

            processor.process_output(stdout, stderr)
            detected_errors = processor.get_errors()

            if detected_errors:
                logger.info(f"Detected {len(detected_errors)} errors.")
                reporter.save_raw_errors(detected_errors)

                analysis_report = analyzer.analyze_errors(detected_errors)
                reporter.save_analysis_report(analysis_report)
                text_report = reporter.generate_summary_report_text(analysis_report)
                reporter.save_text_report(text_report)
                logger.info("Errors processed, analyzed, and saved.")
            else:
                logger.info("No new errors detected.")

            if args.run_duration > 0 and (time.time() - start_time) > args.run_duration:
                logger.info(
                    f"Run duration of {args.run_duration} seconds exceeded. Shutting down."
                )
                break

            if not stop_event.is_set():
                logger.info(
                    f"Waiting for {args.polling_interval} seconds before next poll..."
                )
                time.sleep(args.polling_interval)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        if controller.is_running():
            controller.stop_server()
        logger.info("Error tracker stopped.")

