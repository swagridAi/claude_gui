#!/usr/bin/env python3
from src.automation.state_machine import SimpleAutomationMachine
from src.utils.config_manager import ConfigManager
from src.utils.logging_util import setup_visual_logging
import argparse
import logging
from src.utils.region_manager import RegionManager
from src.models.ui_element import UIElement

def parse_arguments():
    parser = argparse.ArgumentParser(description="Claude GUI Automation")
    parser.add_argument("--config", help="Path to config file", default="config/user_config.yaml")
    parser.add_argument("--debug", help="Enable debug mode", action="store_true")
    parser.add_argument("--calibrate", help="Run calibration before starting", action="store_true")
    parser.add_argument("--max-retries", type=int, help="Maximum retry attempts", default=None)
    parser.add_argument("--retry-delay", type=float, help="Initial delay between retries (seconds)", default=None)
    parser.add_argument("--skip-preprocessing", action="store_true", 
                      help="Skip reference image preprocessing")
    return parser.parse_args()

from src.utils.reference_manager import ReferenceImageManager

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging
    args.debug = True
    log_dir = setup_visual_logging(debug=args.debug)
    logging.info("Starting Claude automation")
    
    # Load configuration
    config = ConfigManager(args.config)
    
    # Initialize reference image manager
    reference_manager = ReferenceImageManager()
    
    # Preprocess existing reference images
    if not args.skip_preprocessing:
        ui_elements_config = config.get("ui_elements", {})
        if reference_manager.ensure_preprocessing(ui_elements_config, config):
            logging.info("Completed automatic preprocessing of reference images")
        else:
            logging.info("Reference images already preprocessed, skipping preprocessing")
        
        # Save configuration with enhanced references
        config.save()
    
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
    
    # Initialize region manager
    region_manager = RegionManager()
    
    # Parse config for UI elements with both absolute and relative regions
    ui_elements = {}
    for element_name, element_config in config.get("ui_elements", {}).items():
        ui_elements[element_name] = UIElement(
            name=element_name,
            reference_paths=element_config.get("reference_paths", []),
            region=element_config.get("region"),
            relative_region=element_config.get("relative_region"),
            parent=element_config.get("parent"),
            confidence=element_config.get("confidence", 0.7)
        )
    
    # Register UI elements with region manager
    region_manager.set_ui_elements(ui_elements)
    
    # Initialize state machine with region manager
    state_machine = SimpleAutomationMachine(config)
    state_machine.region_manager = region_manager
    
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