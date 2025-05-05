import pyautogui
import cv2
import numpy as np
import logging
import glob
import os
from src.models.ui_element import UIElement
def adaptive_confidence(ui_element, min_confidence=0.5, max_confidence=0.95, step=0.05, ui_elements=None, region_manager=None):
    """
    Adaptively adjust confidence threshold to find UI elements.
    
    Args:
        ui_element: UIElement object
        min_confidence: Minimum confidence threshold to try
        max_confidence: Maximum confidence threshold to use
        step: Step size for adjusting confidence
        ui_elements: Dictionary of all UI elements
        region_manager: RegionManager for handling relative regions
        
    Returns:
        Location object or None if not found
    """
    if region_manager and ui_element.relative_region:
        region = ui_element.get_effective_region(ui_elements, region_manager.screen_size)
    else:
        region = ui_element.region 

    # Try with configured confidence first
    location = find_element(ui_element)
    if location:
        return location
        
    # If not found, try with gradually reduced confidence
    current_confidence = ui_element.confidence - step
    while current_confidence >= min_confidence:
        logging.debug(f"Trying adaptive confidence: {current_confidence:.2f} for {ui_element.name}")
        location = find_element(ui_element, confidence_override=current_confidence)
        if location:
            logging.info(f"Found {ui_element.name} with adaptive confidence: {current_confidence:.2f}")
            # Update UI element's confidence for future searches
            ui_element.adaptive_confidence = current_confidence
            return location
        current_confidence -= step
        
    logging.warning(f"Element {ui_element.name} not found even with adaptive confidence")
    return None



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

import pyautogui
import cv2
import numpy as np
import logging
import glob
import os
import time
import psutil
from src.utils.logging_util import log_with_screenshot
from src.models.ui_element import UIElement

# Global debugging flag
DEBUG_SAVE_IMAGES = True  # Set to False in production

def find_element(ui_element, confidence_override=None, use_advanced=True, timeout=60):
    """
    Enhanced version of find_element with improved logging and timeout support.
    
    Args:
        ui_element: UIElement object
        confidence_override: Optional override for confidence threshold
        use_advanced: Whether to use advanced recognition techniques
        timeout: Maximum time in seconds to spend searching
        
    Returns:
        Location object or None if not found or timed out
    """
    # Timer for overall process
    overall_start = time.time()
    
    # Log memory usage at start
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    logging.info(f"Memory usage at start: {memory_info.rss / 1024 / 1024:.2f} MB")
    
    # Log beginning of search
    log_with_screenshot(
        f"Searching for element: {ui_element.name}", 
        stage_name=f"SEARCH_{ui_element.name}_START"
    )
    
    confidence = confidence_override or ui_element.confidence
    min_confidence = max(0.4, confidence - 0.2)  # Set a minimum confidence threshold
    region = ui_element.region
    
    # Log search parameters
    logging.info(f"Search parameters for {ui_element.name}: confidence={confidence}, min_confidence={min_confidence}")
    logging.info(f"Search region: {region}")
    
    # Count reference images
    total_refs = len(ui_element.reference_paths)
    logging.info(f"Starting search for {ui_element.name} with {total_refs} reference images")
    
    # Limit number of reference images for performance
    if total_refs > 10:
        logging.warning(f"Too many reference images for {ui_element.name}, using only first 10 for performance")
        reference_paths = ui_element.reference_paths[:10]
    else:
        reference_paths = ui_element.reference_paths
    
    # Get a screenshot for analysis
    screenshot_start = time.time()
    if region:
        logging.info(f"Taking screenshot of region {region}")
        screenshot = pyautogui.screenshot(region=region)
        x_offset, y_offset = region[0], region[1]
    else:
        logging.info("Taking full screen screenshot")
        screenshot = pyautogui.screenshot()
        x_offset, y_offset = 0, 0
    
    screenshot_end = time.time()
    logging.info(f"Screenshot taken in {screenshot_end - screenshot_start:.2f} seconds")
    
    # Convert screenshot to CV2 format
    convert_start = time.time()
    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    screenshot_gray = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)
    convert_end = time.time()
    logging.info(f"Screenshot conversion completed in {convert_end - convert_start:.2f} seconds")
    
    # Log screenshot dimensions
    screenshot_h, screenshot_w = screenshot_cv.shape[:2]
    logging.info(f"Screenshot dimensions: {screenshot_w}x{screenshot_h} pixels")
    
    # Save debug screenshot if enabled
    if DEBUG_SAVE_IMAGES:
        debug_dir = "logs/debug_images"
        os.makedirs(debug_dir, exist_ok=True)
        timestamp = int(time.time())
        cv2.imwrite(f"{debug_dir}/search_{ui_element.name}_{timestamp}_screenshot.png", screenshot_cv)
    
    # Store all potential matches
    all_matches = []
    
    # Helper function to check if template is larger than screenshot
    def template_fits(template, img):
        h, w = template.shape[:2]
        img_h, img_w = img.shape[:2]
        return h <= img_h and w <= img_w
    
    # Process each reference image
    for i, reference_path in enumerate(reference_paths):
        # Check timeout
        if time.time() - overall_start > timeout:
            logging.warning(f"Search for {ui_element.name} timed out after {timeout} seconds")
            if all_matches:
                logging.info(f"Returning best match found before timeout ({len(all_matches)} matches)")
                all_matches.sort(key=lambda x: x['score'], reverse=True)
                best_match = all_matches[0]
                return best_match['location']
            return None
        
        # Periodic memory and time logging
        if i % 3 == 0 and i > 0:
            elapsed = time.time() - overall_start
            memory_info = process.memory_info()
            logging.info(f"Progress: {i}/{len(reference_paths)} references processed in {elapsed:.2f} seconds")
            logging.info(f"Current memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
        
        ref_start = time.time()
        logging.info(f"Processing reference image {i+1}/{len(reference_paths)}: {os.path.basename(reference_path)}")
        
        if not os.path.exists(reference_path):
            logging.warning(f"Reference image not found: {reference_path}")
            continue
        
        try:
            template = cv2.imread(reference_path)
            if template is None:
                logging.warning(f"Failed to load reference image: {reference_path}")
                continue
            
            # Log template dimensions
            h, w = template.shape[:2]
            logging.info(f"Reference image dimensions: {w}x{h} pixels")
            
            # Skip if template is larger than screenshot
            if not template_fits(template, screenshot_cv):
                logging.warning(f"Template too large for region: {reference_path} - {w}x{h} > {screenshot_w}x{screenshot_h}")
                continue
            
            # Save template if debugging enabled
            if DEBUG_SAVE_IMAGES:
                timestamp = int(time.time())
                cv2.imwrite(f"{debug_dir}/search_{ui_element.name}_{timestamp}_template_{i}.png", template)
            
            # Try standard PyAutoGUI method first - often fastest
            pyautogui_start = time.time()
            try:
                logging.debug(f"Trying PyAutoGUI locate with min_confidence={min_confidence}")
                location = pyautogui.locate(
                    reference_path,
                    screenshot,
                    confidence=min_confidence
                )
                
                pyautogui_end = time.time()
                
                if location:
                    logging.info(f"PyAutoGUI found match in {pyautogui_end - pyautogui_start:.2f} seconds")
                    
                    # Create a match_info without trying to access .confidence
                    match_info = {
                        'location': (
                            location.left + x_offset,
                            location.top + y_offset,
                            location.width,
                            location.height
                        ),
                        'score': min_confidence,  # Use the minimum confidence as fallback
                        'method': 'pyautogui',
                        'template': reference_path
                    }
                    all_matches.append(match_info)
                    logging.debug(f"Added match: {match_info}")
                else:
                    logging.debug(f"PyAutoGUI locate found no matches in {pyautogui_end - pyautogui_start:.2f} seconds")
            except Exception as e:
                pyautogui_end = time.time()
                logging.debug(f"PyAutoGUI locate failed in {pyautogui_end - pyautogui_start:.2f} seconds: {e}")
            
            # If advanced methods enabled, try them too
            if use_advanced:
                # Convert template to grayscale
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                
                # Try multiple template matching methods
                methods = [
                    cv2.TM_CCOEFF_NORMED,
                    cv2.TM_CCORR_NORMED,
                    cv2.TM_SQDIFF_NORMED
                ]
                
                for method in methods:
                    # Check timeout
                    if time.time() - overall_start > timeout:
                        logging.warning(f"Method loop timed out after {timeout} seconds")
                        break
                    
                    method_start = time.time()
                    method_name = method.__str__().split('.')[-1]
                    logging.debug(f"Trying CV2 method {method_name}")
                    
                    try:
                        # Try original images
                        result = cv2.matchTemplate(screenshot_gray, template_gray, method)
                        
                        # Save match results visualization if debugging enabled
                        if DEBUG_SAVE_IMAGES:
                            timestamp = int(time.time())
                            # Normalize result for visualization
                            norm_result = cv2.normalize(result, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
                            # Apply color map for better visualization
                            heatmap = cv2.applyColorMap(norm_result, cv2.COLORMAP_JET)
                            cv2.imwrite(f"{debug_dir}/search_{ui_element.name}_{timestamp}_heatmap_{i}_{method_name}.png", heatmap)
                        
                        # Different handling based on method
                        if method == cv2.TM_SQDIFF_NORMED:
                            # For SQDIFF, smaller values are better matches
                            # Find all matches above threshold (below 1-threshold for SQDIFF)
                            threshold = 1.0 - min_confidence
                            loc = np.where(result <= threshold)
                            
                            match_count = len(loc[0]) if len(loc) > 0 and len(loc[0]) > 0 else 0
                            method_end = time.time()
                            logging.debug(f"Method {method_name} found {match_count} potential matches in {method_end - method_start:.2f} seconds")
                            
                            # Convert similarity score (smaller is better for SQDIFF)
                            for pt in zip(*loc[::-1]):
                                score = 1.0 - result[pt[1], pt[0]]
                                if score >= min_confidence:
                                    h, w = template_gray.shape
                                    match_info = {
                                        'location': (
                                            pt[0] + x_offset,
                                            pt[1] + y_offset,
                                            w,
                                            h
                                        ),
                                        'score': score,
                                        'method': f'cv2.{method_name}',
                                        'template': reference_path
                                    }
                                    all_matches.append(match_info)
                        else:
                            # For other methods, larger values are better matches
                            threshold = min_confidence
                            loc = np.where(result >= threshold)
                            
                            match_count = len(loc[0]) if len(loc) > 0 and len(loc[0]) > 0 else 0
                            method_end = time.time()
                            logging.debug(f"Method {method_name} found {match_count} potential matches in {method_end - method_start:.2f} seconds")
                            
                            for pt in zip(*loc[::-1]):
                                score = result[pt[1], pt[0]]
                                if score >= min_confidence:
                                    h, w = template_gray.shape
                                    match_info = {
                                        'location': (
                                            pt[0] + x_offset,
                                            pt[1] + y_offset,
                                            w,
                                            h
                                        ),
                                        'score': score,
                                        'method': f'cv2.{method_name}',
                                        'template': reference_path
                                    }
                                    all_matches.append(match_info)
                                    
                    except Exception as e:
                        method_end = time.time()
                        logging.warning(f"Method {method_name} failed in {method_end - method_start:.2f} seconds: {e}")
        
        except Exception as e:
            logging.warning(f"Error processing reference {reference_path}: {e}")
            
        # Log completion of this reference image
        ref_end = time.time()
        logging.info(f"Finished processing reference {i+1}/{len(reference_paths)} in {ref_end - ref_start:.2f} seconds")
    
    # Log final memory usage
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    logging.info(f"Final memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
    
    # Total elapsed time
    total_time = time.time() - overall_start
    logging.info(f"Total search time for {ui_element.name}: {total_time:.2f} seconds")
    
    # If we found any matches, return the best one
    if all_matches:
        # Sort by score, highest first
        all_matches.sort(key=lambda x: x['score'], reverse=True)
        best_match = all_matches[0]
        
        # Log all potential matches for debugging
        if len(all_matches) > 1:
            logging.debug(f"Found {len(all_matches)} potential matches for {ui_element.name}")
            for i, match in enumerate(all_matches[:min(5, len(all_matches))]):
                logging.debug(f"Match #{i+1}: score={match['score']:.2f}, method={match['method']}, location={match['location']}")
        
        # Debug visualization - save image showing what was found
        debug_dir = "logs/recognition_debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        try:
            # Take a screenshot and mark all potential matches
            full_screenshot = pyautogui.screenshot()
            debug_img = cv2.cvtColor(np.array(full_screenshot), cv2.COLOR_RGB2BGR)
            
            # Draw rectangle for each potential match (up to 5)
            for i, match in enumerate(all_matches[:min(5, len(all_matches))]):
                x, y, w, h = match['location']
                
                # Use different colors based on rank
                colors = [(0, 255, 0), (0, 255, 255), (0, 165, 255), (0, 0, 255), (128, 0, 255)]
                color = colors[i] if i < len(colors) else (200, 200, 200)
                
                # Draw rectangle
                cv2.rectangle(debug_img, (x, y), (x + w, y + h), color, 2)
                
                # Add text with score
                cv2.putText(
                    debug_img,
                    f"#{i+1}: {match['score']:.2f}",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1
                )
            
            # Save the debug image
            timestamp = int(time.time())
            debug_path = f"{debug_dir}/{ui_element.name}_matches_{timestamp}.png"
            cv2.imwrite(debug_path, debug_img)
            logging.debug(f"Saved matches debug image to {debug_path}")
        except Exception as e:
            logging.error(f"Error saving debug image: {e}")
        
        # Log best match
        logging.info(f"Best match for {ui_element.name}: score={best_match['score']:.2f}, "
                     f"method={best_match['method']}, location={best_match['location']}")
        
        # Log success with screenshot
        log_with_screenshot(
            f"Found {ui_element.name} with score {best_match['score']:.2f}", 
            stage_name=f"FOUND_{ui_element.name}",
            region=best_match['location']
        )
        
        return best_match['location']
    
    # If no match was found, log failure
    log_with_screenshot(
        f"Element {ui_element.name} not found", 
        level=logging.WARNING,
        stage_name=f"NOT_FOUND_{ui_element.name}"
    )
    
    logging.warning(f"No matches found for {ui_element.name} after {total_time:.2f} seconds")
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