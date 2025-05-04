import pyautogui
import cv2
import numpy as np
import logging
import glob
import os
from src.models.ui_element import UIElement

def find_element(ui_element, confidence_override=None):
    """
    Find a UI element on screen using reference images.
    
    Args:
        ui_element: UIElement object
        confidence_override: Optional override for confidence threshold
    
    Returns:
        Location object or None if not found
    """
    confidence = confidence_override or ui_element.confidence
    region = ui_element.region
    
    # Try multiple reference images
    for reference_path in ui_element.reference_paths:
        try:
            # Check if file exists
            if not os.path.exists(reference_path):
                logging.warning(f"Reference image not found: {reference_path}")
                continue
                
            location = pyautogui.locateOnScreen(
                reference_path, 
                region=region,
                confidence=confidence
            )
            
            if location:
                logging.debug(f"Found {ui_element.name} using {reference_path}")
                return location
        except Exception as e:
            logging.warning(f"Error finding {ui_element.name} with {reference_path}: {e}")
    
    # If standard method fails, try advanced CV method
    return find_element_cv(ui_element, confidence)

def find_element_cv(ui_element, confidence=0.7):
    """
    Find a UI element using advanced computer vision techniques.
    
    Args:
        ui_element: UIElement object
        confidence: Confidence threshold
        
    Returns:
        Location object or None if not found
    """
    # Take screenshot of region or full screen
    if ui_element.region:
        screenshot = pyautogui.screenshot(region=ui_element.region)
        x_offset, y_offset = ui_element.region[0], ui_element.region[1]
    else:
        screenshot = pyautogui.screenshot()
        x_offset, y_offset = 0, 0
    
    # Convert screenshot to CV2 format
    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    best_match = None
    best_score = 0
    
    # Try all reference images
    for reference_path in ui_element.reference_paths:
        if not os.path.exists(reference_path):
            continue
            
        template = cv2.imread(reference_path)
        if template is None:
            continue
        
        # Try multiple methods
        methods = [cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED]
        for method in methods:
            try:
                result = cv2.matchTemplate(screenshot_cv, template, method)
                _, score, _, location = cv2.minMaxLoc(result)
                
                if score > best_score and score >= confidence:
                    best_score = score
                    h, w = template.shape[:2]
                    best_match = (
                        location[0] + x_offset,
                        location[1] + y_offset,
                        w,
                        h
                    )
            except Exception as e:
                logging.warning(f"CV matching error: {e}")
    
    if best_match and best_score >= confidence:
        logging.debug(f"Found {ui_element.name} using CV (score: {best_score:.2f})")
        return best_match
    
    return None

def wait_for_visual_change(region, timeout=60, check_interval=0.5, threshold=0.1):
    """
    Wait until the visual content in a region changes.
    
    Args:
        region: Screen region to monitor (x, y, width, height)
        timeout: Maximum wait time in seconds
        check_interval: Time between checks
        threshold: Difference threshold to detect change
        
    Returns:
        True if change detected, False on timeout
    """
    # Take initial screenshot
    initial = pyautogui.screenshot(region=region)
    initial_np = np.array(initial)
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Take current screenshot
        current = pyautogui.screenshot(region=region)
        current_np = np.array(current)
        
        # Compare images
        if initial_np.shape == current_np.shape:
            difference = np.sum(np.abs(initial_np - current_np)) / (initial_np.size * 255)
            
            if difference > threshold:
                logging.debug(f"Visual change detected (diff: {difference:.4f})")
                return True
        
        time.sleep(check_interval)
    
    return False