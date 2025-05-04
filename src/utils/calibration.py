import pyautogui
import time
import logging
from src.models.ui_element import UIElement
from src.automation.recognition import find_element
import numpy as np

def run_calibration(config):
    """
    Auto-calibrate UI elements for Claude automation.
    
    Args:
        config: Configuration manager object
    """
    logging.info("Starting UI calibration")
    
    # Get screen dimensions
    screen_width, screen_height = pyautogui.size()
    logging.info(f"Screen dimensions: {screen_width}x{screen_height}")
    
    # Dictionary to store calibrated elements
    calibrated_elements = {}
    
    # Define search regions
    full_screen = (0, 0, screen_width, screen_height)
    
    # 1. Find the prompt box (usually at the bottom)
    logging.info("Calibrating prompt box")
    prompt_references = glob.glob("assets/reference_images/prompt_box/*.png")
    
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
        
        send_element = UIElement(
            name="send_button",
            reference_paths=send_references,
            region=bottom_region,
            confidence=0.6
        )
        
        send_location = find_element(send_element)
        
        if send_location:
            sx, sy, sw, sh = send_location
            calibrated_elements["send_button"] = {
                "reference_paths": send_references,
                "region": (sx - 10, sy - 10, sw + 20, sh + 20),
                "confidence": 0.7
            }
        else:
            logging.warning("Send button not found, using Enter key instead")
        
        # 4. Define response area
        logging.info("Calibrating response area")
        calibrated_elements["response_area"] = {
            "reference_paths": [],
            "region": response_region,
            "confidence": 0.7
        }
        
        # 5. Find thinking indicator
        logging.info("Calibrating thinking indicator")
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
            calibrated_elements["thinking_indicator"] = {
                "reference_paths": thinking_references,
                "region": (tx - 50, ty - 50, tw + 100, th + G100),
                "confidence": 0.6
            }
        else:
            logging.warning("Thinking indicator not found")
    else:
        logging.error("Prompt box not found, calibration failed")
        return False
    
    # Update config with calibrated elements
    config.set("ui_elements", calibrated_elements)
    logging.info("Calibration complete")
    
    return True