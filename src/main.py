#!/usr/bin/env python3
from src.automation.simplified_state_machine import SimpleAutomationMachine
from src.utils.config_manager import ConfigManager
from src.utils.logging_utils import setup_visual_logging
import argparse
import logging

def parse_arguments():
    parser = argparse.ArgumentParser(description="Claude GUI Automation")
    parser.add_argument("--config", help="Path to config file", default="config/user_config.yaml")
    parser.add_argument("--debug", help="Enable debug mode", action="store_true")
    parser.add_argument("--calibrate", help="Run calibration before starting", action="store_true")
    parser.add_argument("--max-retries", type=int, help="Maximum retry attempts", default=None)
    parser.add_argument("--retry-delay", type=float, help="Initial delay between retries (seconds)", default=None)
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging
    log_dir = setup_visual_logging(debug=args.debug)
    logging.info("Starting Claude automation")
    
    # Load configuration
    config = ConfigManager(args.config)
    
    # Override config with command line arguments if provided
    if args.max_retries is not None:
        config.set("max_retries", args.max_retries)
        logging.info(f"Setting max retries to {args.max_retries} from command line")
        
    if args.retry_delay is not None:
        config.set("retry_delay", args.retry_delay)
        logging.info(f"Setting retry delay to {args.retry_delay} from command line")
    
    # Run calibration if requested
    if args.calibrate:
        from src.utils.calibration import run_calibration
        run_calibration(config)
        config.save()
    
    # Initialize state machine
    state_machine = SimpleAutomationMachine(config)
    
    # Start automation
    try:
        state_machine.run()
    except KeyboardInterrupt:
        logging.info("Automation stopped by user")
    except Exception as e:
        logging.error(f"Automation failed: {e}", exc_info=True)
    finally:
        # Ensure cleanup even if exceptions occur
        state_machine.cleanup()
        logging.info("Automation complete")

if __name__ == "__main__":
    main()