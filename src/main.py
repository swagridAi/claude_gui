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
    # Add new argument for session selection
    parser.add_argument("--session", help="Session name to run", default="default")
    parser.add_argument("--list-sessions", action="store_true", help="List available sessions and exit")
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
    
    # List available sessions if requested
    if args.list_sessions:
        sessions = config.get("sessions", {})
        if not sessions:
            print("No sessions defined in configuration. Add sessions to your config file.")
            return
        
        print("\nAvailable sessions:")
        for session_id, session_data in sessions.items():
            name = session_data.get("name", session_id)
            prompt_count = len(session_data.get("prompts", []))
            print(f"  - {session_id}: {name} ({prompt_count} prompts)")
        return
    
    # Get session configuration
    sessions = config.get("sessions", {})
    
    if args.session not in sessions and args.session != "default":
        logging.error(f"Session '{args.session}' not found in configuration")
        print(f"Error: Session '{args.session}' not found. Use --list-sessions to see available sessions.")
        return
    
    # If using default session and no sessions are defined, use legacy config structure
    if args.session == "default" and not sessions:
        session_config = config.get_all()
    else:
        # Get the selected session configuration
        session_config = sessions.get(args.session, {})
        
        # Merge session config with global settings
        global_config = config.get_all()
        # Remove sessions from global config to avoid confusion
        if "sessions" in global_config:
            del global_config["sessions"]
        
        # Create a full config for this session
        full_config = {**global_config, **session_config}
        
        # Update the config manager with the merged configuration
        for key, value in full_config.items():
            config.set(key, value)
    
    # Get session-specific URL if provided
    if "url" in session_config:
        config.set("claude_url", session_config["url"])
    
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
    
    # Display session information
    if args.session != "default" or sessions:
        session_name = session_config.get("name", args.session)
        prompts = session_config.get("prompts", config.get("prompts", []))
        prompt_count = len(prompts)
        logging.info(f"Running session: {session_name} with {prompt_count} prompts")
        logging.info(f"Claude URL: {config.get('claude_url')}")
    
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