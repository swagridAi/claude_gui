import pyautogui
import time
import logging
import glob
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw
from src.models.ui_element import UIElement
from src.automation.recognition import find_element
from src.utils.logging_util import log_with_screenshot

def run_calibration(config, preserve_sessions=False):
    """
    Auto-calibrate UI elements for Claude automation.
    
    Args:
        config: Configuration manager object
        preserve_sessions: Whether to preserve sessions when saving
        
    Returns:
        bool: True if calibration successful, False otherwise
    """
    logging.info("Starting UI calibration")
    
    # Get screen dimensions
    screen_width, screen_height = pyautogui.size()
    logging.info(f"Screen dimensions: {screen_width}x{screen_height}")
    
    # Dictionary to store calibrated elements
    calibrated_elements = {}
    
    # Define search regions
    full_screen = (0, 0, screen_width, screen_height)
    
    # Create calibration directory if it doesn't exist
    os.makedirs("assets/reference_images", exist_ok=True)
    for dir_name in ['prompt_box', 'send_button', 'thinking_indicator', 'response_area']:
        os.makedirs(f"assets/reference_images/{dir_name}", exist_ok=True)
    
    # 1. Find the prompt box (usually at the bottom)
    logging.info("Calibrating prompt box")
    prompt_references = glob.glob("assets/reference_images/prompt_box/*.png")
    
    if not prompt_references:
        logging.warning("No prompt box reference images found")
        capture_reference_images(config)
        prompt_references = glob.glob("assets/reference_images/prompt_box/*.png")
        if not prompt_references:
            logging.error("Still no prompt box reference images after capture attempt")
            return False
    
    # Create initial UI element with full screen search
    prompt_element = UIElement(
        name="prompt_box",
        reference_paths=prompt_references,
        region=full_screen,
        confidence=0.6
    )
    
    # Try to find the prompt box
    prompt_location = find_element(prompt_element)
    
    if prompt_location:
        x, y, w, h = prompt_location
        prompt_center = (x + w//2, y + h//2)
        
        logging.info(f"Found prompt box at {prompt_center}")
        log_with_screenshot("Prompt box detected", region=prompt_location)
        
        # Save calibrated prompt box
        calibrated_elements["prompt_box"] = {
            "reference_paths": prompt_references,
            "region": (x - 20, y - 20, w + 40, h + 40),
            "confidence": 0.7
        }
        
        # 2. Define regions for other elements based on prompt location
        bottom_region = (0, y - 100, screen_width, screen_height - y + 100)
        response_region = (0, 0, screen_width, y - 50)
        
        # 3. Find send button near prompt box
        logging.info("Calibrating send button")
        send_references = glob.glob("assets/reference_images/send_button/*.png")
        
        if not send_references:
            logging.warning("No send button reference images found")
            capture_reference_images(config, element_type="send_button", region=bottom_region)
            send_references = glob.glob("assets/reference_images/send_button/*.png")
        
        send_element = UIElement(
            name="send_button",
            reference_paths=send_references,
            region=bottom_region,
            confidence=0.6
        )
        
        send_location = find_element(send_element)
        
        if send_location:
            sx, sy, sw, sh = send_location
            log_with_screenshot("Send button detected", region=send_location)
            
            calibrated_elements["send_button"] = {
                "reference_paths": send_references,
                "region": (sx - 10, sy - 10, sw + 20, sh + 20),
                "confidence": 0.7
            }
        else:
            logging.warning("Send button not found, using Enter key instead")
            calibrated_elements["send_button"] = {
                "reference_paths": send_references,
                "region": bottom_region,
                "confidence": 0.6
            }
        
        # 4. Define response area
        logging.info("Calibrating response area")
        response_references = glob.glob("assets/reference_images/response_area/*.png")
        
        # The response area is a large region above the prompt box
        calibrated_elements["response_area"] = {
            "reference_paths": response_references,
            "region": response_region,
            "confidence": 0.7
        }
        
        log_with_screenshot("Response area defined", region=response_region)
        
        # 5. Find thinking indicator
        logging.info("Calibrating thinking indicator")
        thinking_references = glob.glob("assets/reference_images/thinking_indicator/*.png")
        
        if not thinking_references:
            logging.warning("No thinking indicator reference images found")
            capture_reference_images(config, element_type="thinking_indicator", region=response_region)
            thinking_references = glob.glob("assets/reference_images/thinking_indicator/*.png")
        
        thinking_element = UIElement(
            name="thinking_indicator",
            reference_paths=thinking_references,
            region=response_region,
            confidence=0.6
        )
        
        thinking_location = find_element(thinking_element)
        
        if thinking_location:
            tx, ty, tw, th = thinking_location
            log_with_screenshot("Thinking indicator detected", region=thinking_location)
            
            calibrated_elements["thinking_indicator"] = {
                "reference_paths": thinking_references,
                "region": (tx - 50, ty - 50, tw + 100, th + 100),
                "confidence": 0.6
            }
        else:
            logging.warning("Thinking indicator not found, using default region")
            # Use a reasonable default in the middle of the response area
            middle_x = response_region[0] + response_region[2] // 2
            middle_y = response_region[1] + response_region[3] // 2
            default_region = (middle_x - 100, middle_y - 100, 200, 200)
            
            calibrated_elements["thinking_indicator"] = {
                "reference_paths": thinking_references,
                "region": default_region,
                "confidence": 0.5  # Lower confidence since we're guessing
            }
        
        # Update config with calibrated elements
        config.set("ui_elements", calibrated_elements)
        
        # Save with session preservation if requested
        if preserve_sessions and not config.is_in_session_mode():
            config.enter_session_mode()
            config.save()
            config.exit_session_mode()
        else:
            # Use standard save method (respects session mode if active)
            config.save()
            
        logging.info("Calibration complete and configuration updated")
        show_calibration_results(calibrated_elements)
        
        return True
    else:
        logging.error("Prompt box not found, calibration failed")
        if prompt_references:
            logging.info("Attempting to capture new reference images...")
            capture_reference_images(config)
            # Use recursive call with preserve_sessions flag
            return run_calibration(config, preserve_sessions)
        
        return False

def capture_reference_images(config, element_type=None, region=None):
    """
    Capture reference images for UI elements.
    
    Args:
        config: Configuration manager object
        element_type: Specific element type to capture (or None for all)
        region: Region to focus on for capture
    """
    logging.info(f"Starting reference image capture{'for ' + element_type if element_type else ''}")
    
    if element_type is None or element_type == "prompt_box":
        # Capture prompt box
        print("\n===== CAPTURE PROMPT BOX =====")
        print("1. Position your mouse over Claude's prompt box in the Chrome window")
        print("2. Switch back to this command window and press Enter")
        print("3. You will have 3 seconds to switch back to Chrome and position your mouse over the prompt box")
        print("4. Stay still until the capture is complete\n")
        
        input("Position mouse over prompt box, then come back here and press Enter...")
        print("Switching windows - GO BACK TO CHROME NOW! (3 seconds)")
        time.sleep(3)  # Give user time to switch windows and position mouse
        
        # Capture a region around the mouse position
        mouse_pos = pyautogui.position()
        region = (mouse_pos.x - 150, mouse_pos.y - 30, 300, 60)
        screenshot = pyautogui.screenshot(region=region)
        
        # Save the image
        os.makedirs("assets/reference_images/prompt_box", exist_ok=True)
        timestamp = int(time.time())
        screenshot.save(f"assets/reference_images/prompt_box/prompt_box_{timestamp}.png")
        logging.info(f"Saved prompt box reference image")
        print("\n✓ Prompt box captured successfully!")
    
    if element_type is None or element_type == "send_button":
        # Capture send button
        print("\n===== CAPTURE SEND BUTTON =====")
        print("1. Position your mouse over the send button in the Chrome window")
        print("2. Switch back to this command window and press Enter")
        print("3. You will have 3 seconds to switch back to Chrome and position your mouse over the send button")
        print("4. Stay still until the capture is complete\n")
        
        input("Position mouse over send button, then come back here and press Enter...")
        print("Switching windows - GO BACK TO CHROME NOW! (3 seconds)")
        time.sleep(3)  # Give user time to switch windows and position mouse
        
        # Capture a region around the mouse position
        mouse_pos = pyautogui.position()
        region = (mouse_pos.x - 30, mouse_pos.y - 30, 60, 60)
        screenshot = pyautogui.screenshot(region=region)
        
        # Save the image
        os.makedirs("assets/reference_images/send_button", exist_ok=True)
        timestamp = int(time.time())
        screenshot.save(f"assets/reference_images/send_button/send_button_{timestamp}.png")
        logging.info(f"Saved send button reference image")
        print("\n✓ Send button captured successfully!")
    
    if element_type is None or element_type == "thinking_indicator":
        # Capture thinking indicator
        print("\n===== CAPTURE THINKING INDICATOR =====")
        print("1. Send a message to Claude in the Chrome window to see the thinking indicator")
        print("2. When the thinking indicator appears, position your mouse over it")
        print("3. Switch back to this command window and press Enter")
        print("4. You will have 3 seconds to switch back to Chrome and position your mouse again")
        print("5. Stay still until the capture is complete\n")
        
        input("Position mouse over thinking indicator, then come back here and press Enter...")
        print("Switching windows - GO BACK TO CHROME NOW! (3 seconds)")
        time.sleep(3)  # Give user time to switch windows and position mouse
        
        # Capture a region around the mouse position
        mouse_pos = pyautogui.position()
        region = (mouse_pos.x - 50, mouse_pos.y - 30, 100, 60)
        screenshot = pyautogui.screenshot(region=region)
        
        # Save the image
        os.makedirs("assets/reference_images/thinking_indicator", exist_ok=True)
        timestamp = int(time.time())
        screenshot.save(f"assets/reference_images/thinking_indicator/thinking_{timestamp}.png")
        logging.info(f"Saved thinking indicator reference image")
        print("\n✓ Thinking indicator captured successfully!")
    
    print("\n===== CALIBRATION IMAGE CAPTURE COMPLETE =====")
    print("All reference images have been captured successfully.")
    print("You can now return to the main calibration process.")

def show_calibration_results(calibrated_elements):
    """
    Display visual feedback of calibration results.
    
    Args:
        calibrated_elements: Dictionary of calibrated UI elements
    """
    try:
        # Take a screenshot of the full screen
        screenshot = pyautogui.screenshot()
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # Draw rectangles for each calibrated element
        colors = {
            "prompt_box": (0, 255, 0),  # Green
            "send_button": (0, 0, 255),  # Red
            "thinking_indicator": (255, 0, 0),  # Blue
            "response_area": (255, 255, 0)  # Cyan
        }
        
        for element_name, element_config in calibrated_elements.items():
            if "region" in element_config:
                x, y, w, h = element_config["region"]
                cv2.rectangle(img, (x, y), (x + w, y + h), colors.get(element_name, (255, 255, 255)), 2)
                cv2.putText(img, element_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors.get(element_name, (255, 255, 255)), 1)
        
        # Save the image with rectangles
        timestamp = int(time.time())
        calibration_image_path = f"logs/calibration_results_{timestamp}.png"
        os.makedirs("logs", exist_ok=True)
        cv2.imwrite(calibration_image_path, img)
        
        logging.info(f"Calibration results saved to {calibration_image_path}")
        
        # Show the image to the user
        logging.info(f"Calibration complete. Check {calibration_image_path} to verify results")
        
    except Exception as e:
        logging.error(f"Error showing calibration results: {e}")

def verify_calibration(config):
    """
    Verify that calibrated elements can be found.
    
    Args:
        config: Configuration manager object
        
    Returns:
        bool: True if verification passed, False otherwise
    """
    logging.info("Verifying calibration")
    
    ui_elements = {}
    for element_name, element_config in config.get("ui_elements", {}).items():
        ui_elements[element_name] = UIElement(
            name=element_name,
            reference_paths=element_config.get("reference_paths", []),
            region=element_config.get("region"),
            confidence=element_config.get("confidence", 0.7)
        )
    
    # Verify each element
    results = {}
    for name, element in ui_elements.items():
        location = find_element(element)
        results[name] = location is not None
        logging.info(f"Element {name}: {'Found' if location else 'Not found'}")
    
    # Overall result
    verification_passed = all(results.values())
    logging.info(f"Calibration verification: {'Passed' if verification_passed else 'Failed'}")
    
    return verification_passed

    def interactive_calibration(config, preserve_sessions=False):
        """
        Interactive calibration mode with user guidance.
        
        Args:
            config: Configuration manager object
            preserve_sessions: Whether to preserve sessions when saving
            
        Returns:
            bool: True if calibration successful, False otherwise
        """
        print("\n===== Claude GUI Automation - Interactive Calibration =====\n")
        print("This wizard will help you calibrate the automation for Claude's interface.")
        print("Please make sure Claude is open in your browser before continuing.\n")
        
        input("Press Enter to start calibration...")
        
        # First, capture reference images
        capture_reference_images(config)
        
        # Run the main calibration with session preservation
        success = run_calibration(config, preserve_sessions)
        
        if success:
            print("\nCalibration successful!")
            print("The automation is now configured for your screen layout.")
        else:
            print("\nCalibration failed.")
            print("Please check the logs for more information.")
        
        return success

# Additional helper functions
def get_element_screenshot(element_name, config):
    """
    Get a screenshot of a calibrated element.
    
    Args:
        element_name: Name of UI element
        config: Configuration manager object
        
    Returns:
        PIL Image or None if element not found
    """
    try:
        element_config = config.get("ui_elements", {}).get(element_name)
        if not element_config or "region" not in element_config:
            logging.error(f"Element {element_name} not configured")
            return None
        
        region = element_config["region"]
        screenshot = pyautogui.screenshot(region=region)
        return screenshot
    
    except Exception as e:
        logging.error(f"Error capturing element screenshot: {e}")
        return None