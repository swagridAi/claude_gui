import logging
import os
import time
from datetime import datetime
import pyautogui
import cv2
import numpy as np

def setup_visual_logging(debug=False):
    """
    Set up logging with screenshot capability.
    
    Args:
        debug: Enable debug mode for more verbose logging
    
    Returns:
        Path to log directory
    """
    debug = True
    # Create timestamped log directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join("logs", f"run_{timestamp}")
    os.makedirs(log_dir, exist_ok=True)
    
    # Set up file and console logging
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "automation.log")),
            logging.StreamHandler()
        ]
    )
    
    logging.info(f"Logging initialized in {log_dir}")
    return log_dir

def log_with_screenshot(message, level=logging.INFO, region=None):
    """
    Log a message and capture a screenshot.
    
    Args:
        message: Log message
        level: Logging level (default: INFO)
        region: Optional region to capture (x, y, width, height)
    """
    # Log the message
    logging.log(level, message)
    
    try:
        # Create screenshots directory if it doesn't exist
        screenshot_dir = os.path.join("logs", "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(screenshot_dir, f"screenshot_{timestamp}.png")
        
        # Capture screenshot (full screen or region)
        screenshot = pyautogui.screenshot(region=region)
        
        # Save the screenshot
        screenshot.save(filename)
        
        # If region is specified, add visual indicator
        if region:
            # Capture full screen for reference
            full_screenshot = pyautogui.screenshot()
            full_img = np.array(full_screenshot)
            full_img = cv2.cvtColor(full_img, cv2.COLOR_RGB2BGR)
            
            # Draw rectangle around the region
            x, y, w, h = region
            cv2.rectangle(full_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Add text label with message
            cv2.putText(
                full_img, 
                message[:50] + "..." if len(message) > 50 else message,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )
            
            # Save the annotated screenshot
            annotated_filename = os.path.join(screenshot_dir, f"annotated_{timestamp}.png")
            cv2.imwrite(annotated_filename, full_img)
        
        logging.debug(f"Screenshot saved to {filename}")
        
    except Exception as e:
        logging.error(f"Failed to capture screenshot: {e}")