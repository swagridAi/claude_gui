#!/usr/bin/env python3
from src.automation.state_machine import AutomationStateMachine
from src.utils.config_manager import ConfigManager
from src.utils.logging_utils import setup_visual_logging
import argparse
import logging

def parse_arguments():
    parser = argparse.ArgumentParser(description="Claude GUI Automation")
    parser.add_argument("--config", help="Path to config file", default="config/user_config.yaml")
    parser.add_argument("--debug", help="Enable debug mode", action="store_true")
    parser.add_argument("--calibrate", help="Run calibration before starting", action="store_true")
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging
    log_dir = setup_visual_logging(debug=args.debug)
    logging.info("Starting Claude automation")
    
    # Load configuration
    config = ConfigManager(args.config)
    
    # Initialize state machine
    state_machine = AutomationStateMachine(config)
    
    # Run calibration if requested
    if args.calibrate:
        from src.utils.calibration import run_calibration
        run_calibration(config)
        config.save()
    
    # Start automation
    try:
        state_machine.run()
    except KeyboardInterrupt:
        logging.info("Automation stopped by user")
    except Exception as e:
        logging.error(f"Automation failed: {e}", exc_info=True)
    finally:
        logging.info("Automation complete")

if __name__ == "__main__":
    main()