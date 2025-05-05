#!/usr/bin/env python3
from src.automation.state_machine import SimpleAutomationMachine
from src.utils.config_manager import ConfigManager
from src.utils.logging_util import setup_visual_logging
import argparse
import logging
import os
import time
import copy
from src.utils.region_manager import RegionManager
from src.models.ui_element import UIElement
from src.utils.reference_manager import ReferenceImageManager

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
    # Add new argument to preserve config
    parser.add_argument("--preserve-config", action="store_true", 
                      help="Preserve original configuration (don't overwrite)")
    parser.add_argument("--temp-config", help="Path to write temporary config", default=None)
    # Add option to restore original config if something goes wrong
    parser.add_argument("--restore-original-config", action="store_true",
                      help="Restore original configuration before running")
    # Add option to show config changes
    parser.add_argument("--show-config-diff", action="store_true",
                      help="Show differences between original and current config")
    # Add option to cleanup temporary configs
    parser.add_argument("--cleanup-temp-configs", type=int, metavar="DAYS",
                      help="Remove temporary config files older than specified days")
    return parser.parse_args()

def cleanup_temp_configs(days_old=7):
    """Remove temporary config files older than specified days."""
    temp_dir = "config/temp"
    if not os.path.exists(temp_dir):
        return
        
    current_time = time.time()
    max_age = days_old * 24 * 60 * 60  # Convert days to seconds
    
    logging.info(f"Cleaning up temporary config files older than {days_old} days")
    
    count = 0
    for filename in os.listdir(temp_dir):
        if filename.endswith(".yaml") and "temp" in filename:
            filepath = os.path.join(temp_dir, filename)
            file_age = current_time - os.path.getmtime(filepath)
            
            if file_age > max_age:
                try:
                    os.remove(filepath)
                    count += 1
                except Exception as e:
                    logging.error(f"Error removing temp file {filepath}: {e}")
    
    logging.info(f"Removed {count} temporary config files")

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging
    args.debug = True
    log_dir = setup_visual_logging(debug=args.debug)
    logging.info("Starting Claude automation")
    
    # Clean up temporary configs if requested
    if args.cleanup_temp_configs:
        cleanup_temp_configs(args.cleanup_temp_configs)
        if not any([args.list_sessions, args.session != "default", args.calibrate]):
            logging.info("Cleanup completed. Exiting.")
            return
    
    # Load configuration
    config = ConfigManager(args.config)
    
    # Restore original configuration if requested
    if args.restore_original_config:
        if config.restore_original_config():
            logging.info("Restored original configuration")
            # Save the restored config
            if config.save():
                logging.info("Saved restored configuration")
            else:
                logging.error("Failed to save restored configuration")
        else:
            logging.warning("Failed to restore original configuration")
    
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
        
        # Display config difference if requested
        if args.show_config_diff and hasattr(config, 'show_changes') and callable(config.show_changes):
            print("\nConfiguration differences:")
            config.show_changes()
            
        return
    
    # Check if we're using a specific session
    preserve_config = args.preserve_config
    if args.session != "default":
        # We're using a specific session, enter session mode automatically
        preserve_config = True
        config.enter_session_mode(args.session)
        logging.info(f"Entering session mode for '{args.session}'")
    
    # Create a working copy of config for temporary use if needed
    if preserve_config and args.temp_config:
        # Create directory if needed
        temp_dir = os.path.dirname(args.temp_config)
        if temp_dir and not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            
        # Save a temporary copy for this run
        logging.info(f"Creating temporary config at {args.temp_config}")
        config.save(args.temp_config)
        
        # Use this temporary config for the rest of the run
        working_config = ConfigManager(args.temp_config)
    else:
        # Use the original config, but in session mode if needed
        working_config = config
    
    # Get session configuration
    sessions = working_config.get("sessions", {})
    
    if args.session not in sessions and args.session != "default":
        logging.error(f"Session '{args.session}' not found in configuration")
        print(f"Error: Session '{args.session}' not found. Use --list-sessions to see available sessions.")
        return
    
    # If using default session and no sessions are defined, use legacy config structure
    if args.session == "default" and not sessions:
        session_config = working_config.get_all()
    else:
        # Use the merge_session_config method from ConfigManager
        if not working_config.merge_session_config(args.session):
            logging.error(f"Failed to merge configuration for session '{args.session}'")
            return
            
        # Get the merged configuration
        session_config = working_config.get_all()
        
        logging.info(f"Successfully merged configuration for session '{args.session}'")
    
    # Initialize reference image manager
    reference_manager = ReferenceImageManager()
    
    # Preprocess existing reference images
    if not args.skip_preprocessing:
        ui_elements_config = working_config.get("ui_elements", {})
        try:
            if reference_manager.ensure_preprocessing(ui_elements_config, working_config, preserve_config):
                logging.info("Completed automatic preprocessing of reference images")
            else:
                logging.info("Reference images already preprocessed, skipping preprocessing")
        except Exception as e:
            logging.error(f"Error during reference preprocessing: {e}")
            logging.warning("Continuing without preprocessing references")
    
    # Override config with command line arguments if provided
    if args.max_retries is not None:
        working_config.set("max_retries", args.max_retries)
        logging.info(f"Setting max retries to {args.max_retries} from command line")
        
    if args.retry_delay is not None:
        working_config.set("retry_delay", args.retry_delay)
        logging.info(f"Setting retry delay to {args.retry_delay} from command line")
    
    # Run calibration if requested
    if args.calibrate:
        from src.utils.calibration import run_calibration
        try:
            # Pass preserve_config flag to calibration
            if run_calibration(working_config, preserve_config):
                logging.info("Calibration completed successfully")
            else:
                logging.warning("Calibration failed or was incomplete")
        except Exception as e:
            logging.error(f"Error during calibration: {e}")
            logging.warning("Continuing with previous calibration settings")
    
    # Initialize region manager
    region_manager = RegionManager()
    
    # Parse config for UI elements with both absolute and relative regions
    ui_elements = {}
    for element_name, element_config in working_config.get("ui_elements", {}).items():
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
        session_data = sessions.get(args.session, {})
        session_name = session_data.get("name", args.session)
        prompts = working_config.get("prompts", [])
        prompt_count = len(prompts)
        logging.info(f"Running session: {session_name} with {prompt_count} prompts")
        logging.info(f"Claude URL: {working_config.get('claude_url')}")
    
    # Show config differences if requested
    if args.show_config_diff and hasattr(config, 'show_changes') and callable(config.show_changes):
        logging.info("Showing configuration differences:")
        config.show_changes()
    
    # Initialize state machine with region manager and preservation flag
    state_machine = SimpleAutomationMachine(working_config)
    state_machine.region_manager = region_manager
    # Set preservation flag if the state machine supports it
    if hasattr(state_machine, 'set_preserve_config') and callable(getattr(state_machine, 'set_preserve_config')):
        state_machine.set_preserve_config(preserve_config)
    
    # Start automation
    try:
        state_machine.run()
    except KeyboardInterrupt:
        logging.info("Automation stopped by user")
    except Exception as e:
        logging.error(f"Automation failed: {e}", exc_info=True)
    finally:
        # Ensure cleanup even if exceptions occur
        try:
            state_machine.cleanup()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
        
        # If we're preserving config and using the original file, save with preservation
        if preserve_config and not args.temp_config:
            try:
                logging.info("Saving configuration with session preservation")
                config.save_preserving_sessions()
                # Exit session mode
                config.exit_session_mode()
            except Exception as e:
                logging.error(f"Error saving preserved configuration: {e}")
        
        logging.info("Automation complete")

if __name__ == "__main__":
    main()