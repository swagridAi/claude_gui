#!/usr/bin/env python3
"""
Debug-Based Calibration Tool for Claude GUI Automation

This tool analyzes debugging logs and images to help calibrate UI elements
based on actual runtime behavior.
"""

import os
import sys
import time
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import cv2
import numpy as np
import glob
import re
from pathlib import Path
import yaml

# Add project root to path
sys.path.append('.')

# Import configuration manager
from src.utils.config_manager import ConfigManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DebugBasedCalibrationTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Debug-Based UI Calibration Tool")
        self.root.state('zoomed')  # Maximize window
        
        # Initialize variables
        self.debug_images = {}  # Dictionary to store debug images by element
        self.selected_element = None
        self.elements_config = {}
        self.current_image = None
        self.selected_region = None
        
        # Load configuration
        self.config = ConfigManager()
        
        # Set up the UI
        self.setup_ui()
        
        # Scan for debug images
        self.scan_debug_images()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main layout with two frames side by side
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel for controls
        control_frame = ttk.Frame(main_pane, padding=10, width=300)
        main_pane.add(control_frame, weight=1)
        
        # Right panel for image display
        display_frame = ttk.LabelFrame(main_pane, text="Debug Image Viewer")
        main_pane.add(display_frame, weight=3)
        
        # Control panel components
        ttk.Label(control_frame, text="Debug Logs Analysis", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        # Scan button
        ttk.Button(control_frame, text="Scan Debug Logs", command=self.scan_debug_images).pack(fill=tk.X, pady=(0, 10))
        
        # Element selector
        ttk.Label(control_frame, text="Select UI Element:").pack(anchor="w", pady=(10, 5))
        
        self.element_listbox = tk.Listbox(control_frame, height=8)
        self.element_listbox.pack(fill=tk.X, pady=(0, 5))
        self.element_listbox.bind('<<ListboxSelect>>', self.on_element_select)
        
        # Image selector 
        ttk.Label(control_frame, text="Select Debug Image:").pack(anchor="w", pady=(10, 5))
        
        self.image_listbox = tk.Listbox(control_frame, height=10)
        self.image_listbox.pack(fill=tk.X, pady=(0, 10))
        self.image_listbox.bind('<<ListboxSelect>>', self.on_image_select)
        
        # Element information
        self.info_frame = ttk.LabelFrame(control_frame, text="Element Information")
        self.info_frame.pack(fill=tk.X, pady=10)
        
        self.info_text = tk.Text(self.info_frame, height=10, width=40, wrap=tk.WORD)
        self.info_text.pack(fill=tk.X, pady=5)
        
        # Calibration actions
        ttk.Label(control_frame, text="Calibration Actions:").pack(anchor="w", pady=(10, 5))
        
        ttk.Button(control_frame, text="Use Selected Region", command=self.use_selected_region).pack(fill=tk.X, pady=2)
        ttk.Button(control_frame, text="Use Best Match Region", command=self.use_best_match_region).pack(fill=tk.X, pady=2)
        ttk.Button(control_frame, text="Adjust Click Offset", command=self.adjust_click_offset).pack(fill=tk.X, pady=2)
        ttk.Button(control_frame, text="Save Configuration", command=self.save_configuration).pack(fill=tk.X, pady=(10, 2))
        
        # Image display area
        self.canvas = tk.Canvas(display_frame, bg="gray90")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Canvas bindings for region selection
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM)
        
        # Welcome message
        self.status_var.set("Welcome! Start by scanning debug logs.")
    
    def scan_debug_images(self):
        """Scan for debug images in the logs directory."""
        self.debug_images = {}
        
        # Scan recognition debug images
        recognition_dir = "logs/recognition_debug"
        if os.path.exists(recognition_dir):
            for image_path in glob.glob(os.path.join(recognition_dir, "*.png")):
                # Extract element name from filename (pattern: element_name_matches_timestamp.png)
                filename = os.path.basename(image_path)
                match = re.match(r"(\w+)_matches_\d+\.png", filename)
                if match:
                    element_name = match.group(1)
                    if element_name not in self.debug_images:
                        self.debug_images[element_name] = {"recognition": [], "click": []}
                    self.debug_images[element_name]["recognition"].append(image_path)
        
        # Scan click debug images
        click_dir = "logs/click_debug"
        if os.path.exists(click_dir):
            for image_path in glob.glob(os.path.join(click_dir, "*.png")):
                # Extract element name from filename (pattern: click_element_name_timestamp.png)
                filename = os.path.basename(image_path)
                match = re.match(r"click_(\w+)_\d+_\d+\.png", filename)
                if match:
                    element_name = match.group(1)
                    if element_name not in self.debug_images:
                        self.debug_images[element_name] = {"recognition": [], "click": []}
                    self.debug_images[element_name]["click"].append(image_path)
        
        # Update element listbox
        self.element_listbox.delete(0, tk.END)
        for element_name in sorted(self.debug_images.keys()):
            rec_count = len(self.debug_images[element_name]["recognition"])
            click_count = len(self.debug_images[element_name]["click"])
            self.element_listbox.insert(tk.END, f"{element_name} (R:{rec_count}, C:{click_count})")
        
        # Get current configuration
        self.elements_config = self.config.get("ui_elements", {})
        
        # Update status
        element_count = len(self.debug_images)
        self.status_var.set(f"Found debug images for {element_count} UI elements")
    
    def on_element_select(self, event):
        """Handle selection of an element from the listbox."""
        selection = self.element_listbox.curselection()
        if not selection:
            return
            
        # Get selected element name
        element_entry = self.element_listbox.get(selection[0])
        element_name = element_entry.split(" ")[0]
        self.selected_element = element_name
        
        # Update image listbox
        self.image_listbox.delete(0, tk.END)
        
        if element_name in self.debug_images:
            # Add recognition images
            for i, path in enumerate(self.debug_images[element_name]["recognition"]):
                filename = os.path.basename(path)
                self.image_listbox.insert(tk.END, f"R{i+1}: {filename}")
            
            # Add click images
            for i, path in enumerate(self.debug_images[element_name]["click"]):
                filename = os.path.basename(path)
                self.image_listbox.insert(tk.END, f"C{i+1}: {filename}")
        
        # Update element info display
        self.update_element_info(element_name)
        
        self.status_var.set(f"Selected element: {element_name}")
    
    def on_image_select(self, event):
        """Handle selection of an image from the listbox."""
        if not self.selected_element:
            return
            
        selection = self.image_listbox.curselection()
        if not selection:
            return
            
        # Get selected image path
        image_entry = self.image_listbox.get(selection[0])
        image_type = image_entry[0]  # R for recognition, C for click
        image_index = int(image_entry[1]) - 1
        
        if image_type == "R":
            image_path = self.debug_images[self.selected_element]["recognition"][image_index]
        else:
            image_path = self.debug_images[self.selected_element]["click"][image_index]
        
        # Display the selected image
        self.display_image(image_path)
        
        self.status_var.set(f"Displaying {os.path.basename(image_path)}")
    
    def display_image(self, image_path):
        """Display an image on the canvas."""
        try:
            # Load the image
            self.current_image_path = image_path
            img = Image.open(image_path)
            
            # Get canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # If canvas not yet sized, use defaults
            if canvas_width <= 1:
                canvas_width = 800
                canvas_height = 600
            
            # Keep aspect ratio
            img_width, img_height = img.size
            scale = min(canvas_width / img_width, canvas_height / img_height)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # Resize the image
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.current_image = ImageTk.PhotoImage(resized)
            
            # Clear canvas
            self.canvas.delete("all")
            
            # Draw the image
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image)
            self.canvas.config(scrollregion=(0, 0, new_width, new_height))
            
            # Store the scale factor for coordinate conversion
            self.scale = scale
            
            # Reset selection
            self.selected_region = None
            
            # Parse image type to extract embedded information
            self.analyze_debug_image(image_path)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error displaying image: {e}")
    
    def analyze_debug_image(self, image_path):
        """Extract and display embedded information from debug images."""
        filename = os.path.basename(image_path)
        
        # Different analysis based on image type
        if "click_" in filename:
            self.analyze_click_debug(image_path)
        elif "matches_" in filename:
            self.analyze_recognition_debug(image_path)
    
    def analyze_click_debug(self, image_path):
        """Analyze a click debug image to extract click location."""
        try:
            # Load the image using OpenCV to detect the click marker
            img = cv2.imread(image_path)
            
            if img is None:
                logging.error(f"Could not load image: {image_path}")
                return
                
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Look for the red circle marking the click point
            # Using a simple template matching approach here
            red_channel = img[:,:,2]
            _, thresh = cv2.threshold(red_channel, 200, 255, cv2.THRESH_BINARY)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Look for circular contours
            click_points = []
            for contour in contours:
                # Calculate properties that can help identify the click marker
                area = cv2.contourArea(contour)
                perimeter = cv2.arcLength(contour, True)
                
                # A circle has the maximum area for a given perimeter
                if perimeter > 0:
                    circularity = 4 * np.pi * (area / (perimeter * perimeter))
                    
                    # Circles have circularity close to 1.0
                    if 0.5 < circularity < 1.2 and 500 < area < 5000:
                        # Get the center of the contour
                        M = cv2.moments(contour)
                        if M["m00"] > 0:
                            cx = int(M["m10"] / M["m00"])
                            cy = int(M["m01"] / M["m00"])
                            click_points.append((cx, cy))
            
            # If click points found, mark them on the canvas
            if click_points:
                for i, (cx, cy) in enumerate(click_points):
                    # Convert to canvas coordinates
                    canvas_x = cx * self.scale
                    canvas_y = cy * self.scale
                    
                    # Draw a marker
                    self.canvas.create_oval(
                        canvas_x - 5, canvas_y - 5, 
                        canvas_x + 5, canvas_y + 5,
                        outline="red", fill="red", tags="click_point"
                    )
                    
                    # Add label
                    self.canvas.create_text(
                        canvas_x + 10, canvas_y,
                        text=f"Click Point {i+1}: ({cx}, {cy})",
                        fill="red", anchor=tk.W, tags="click_point"
                    )
                
                # Update status
                self.status_var.set(f"Found {len(click_points)} click points")
            else:
                self.status_var.set("No click points detected in image")
        
        except Exception as e:
            logging.error(f"Error analyzing click debug: {e}")
            self.status_var.set(f"Error analyzing image: {str(e)}")
    
    def analyze_recognition_debug(self, image_path):
        """Analyze a recognition debug image to extract match regions."""
        try:
            # Load the image using OpenCV to detect marked regions
            img = cv2.imread(image_path)
            
            if img is None:
                logging.error(f"Could not load image: {image_path}")
                return
                
            # Convert to OpenCV format
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Find green rectangles (match regions)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # Green mask (for found regions)
            lower_green = np.array([40, 50, 50])
            upper_green = np.array([80, 255, 255])
            green_mask = cv2.inRange(hsv, lower_green, upper_green)
            
            # Find contours in the mask
            green_contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Draw rectangles on the canvas
            match_regions = []
            for i, contour in enumerate(green_contours):
                # Get the bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                match_regions.append((x, y, w, h))
                
                # Convert to canvas coordinates
                canvas_x = x * self.scale
                canvas_y = y * self.scale
                canvas_w = w * self.scale
                canvas_h = h * self.scale
                
                # Draw rectangle
                self.canvas.create_rectangle(
                    canvas_x, canvas_y, 
                    canvas_x + canvas_w, canvas_y + canvas_h,
                    outline="green", width=2, tags="match_region"
                )
                
                # Add label
                self.canvas.create_text(
                    canvas_x, canvas_y - 10,
                    text=f"Match {i+1}: ({x}, {y}, {w}, {h})",
                    fill="green", anchor=tk.W, tags="match_region"
                )
            
            # Store the match regions
            self.match_regions = match_regions
            
            # Update status
            if match_regions:
                self.status_var.set(f"Found {len(match_regions)} match regions")
            else:
                self.status_var.set("No match regions detected in image")
                
        except Exception as e:
            logging.error(f"Error analyzing recognition debug: {e}")
            self.status_var.set(f"Error analyzing image: {str(e)}")
    
    def update_element_info(self, element_name):
        """Update the element information display."""
        self.info_text.delete(1.0, tk.END)
        
        if element_name in self.elements_config:
            element_config = self.elements_config[element_name]
            
            # Format region information
            region_str = "None"
            if "region" in element_config and element_config["region"]:
                region = element_config["region"]
                region_str = f"({region[0]}, {region[1]}, {region[2]}, {region[3]})"
            
            # Format reference image counts
            ref_count = len(element_config.get("reference_paths", []))
            
            # Format confidence information
            confidence = element_config.get("confidence", 0.7)
            
            # Build the info text
            info = f"Element Name: {element_name}\n\n"
            info += f"Current Region: {region_str}\n\n"
            info += f"Reference Images: {ref_count}\n\n"
            info += f"Confidence: {confidence}\n\n"
            
            # Add debug image counts
            if element_name in self.debug_images:
                rec_count = len(self.debug_images[element_name]["recognition"])
                click_count = len(self.debug_images[element_name]["click"])
                info += f"Debug Images:\n"
                info += f"  Recognition: {rec_count}\n"
                info += f"  Click: {click_count}\n"
            
            self.info_text.insert(tk.END, info)
        else:
            self.info_text.insert(tk.END, f"No configuration found for {element_name}")
    
    def on_mouse_down(self, event):
        """Handle mouse button press for region selection."""
        # Reset any existing selection
        self.canvas.delete("selection")
        self.selection_start = (event.x, event.y)
    
    def on_mouse_drag(self, event):
        """Handle mouse drag for region selection."""
        if not hasattr(self, 'selection_start'):
            return
            
        # Delete previous rectangle
        self.canvas.delete("selection")
        
        # Draw new rectangle
        self.canvas.create_rectangle(
            self.selection_start[0], self.selection_start[1],
            event.x, event.y,
            outline="blue", width=2, tags="selection"
        )
        
        # Update status with dimensions
        width = abs(event.x - self.selection_start[0])
        height = abs(event.y - self.selection_start[1])
        
        self.status_var.set(f"Selection: {width}x{height} pixels")
    
    def on_mouse_up(self, event):
        """Handle mouse release for region selection."""
        if not hasattr(self, 'selection_start'):
            return
            
        # Calculate selected region
        x1, y1 = self.selection_start
        x2, y2 = event.x, event.y
        
        # Ensure x1,y1 is top-left and x2,y2 is bottom-right
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        
        width = right - left
        height = bottom - top
        
        # Convert to original image coordinates
        orig_left = int(left / self.scale)
        orig_top = int(top / self.scale)
        orig_width = int(width / self.scale)
        orig_height = int(height / self.scale)
        
        # Store the selected region
        self.selected_region = (orig_left, orig_top, orig_width, orig_height)
        
        # Update status
        self.status_var.set(f"Selected region: ({orig_left}, {orig_top}, {orig_width}, {orig_height})")
    
    def use_selected_region(self):
        """Use the manually selected region for the current element."""
        if not self.selected_element:
            messagebox.showwarning("No Selection", "Please select an element first.")
            return
            
        if not self.selected_region:
            messagebox.showwarning("No Region", "Please select a region on the image first.")
            return
            
        # Update configuration
        if self.selected_element not in self.elements_config:
            self.elements_config[self.selected_element] = {}
            
        self.elements_config[self.selected_element]["region"] = self.selected_region
        
        # Update info display
        self.update_element_info(self.selected_element)
        
        self.status_var.set(f"Updated region for {self.selected_element}")
    
    def use_best_match_region(self):
        """Use the best match region from the debug image."""
        if not self.selected_element:
            messagebox.showwarning("No Selection", "Please select an element first.")
            return
            
        if not hasattr(self, 'match_regions') or not self.match_regions:
            messagebox.showwarning("No Matches", "No match regions found in the current image.")
            return
            
        # Use the first (best) match region
        best_match = self.match_regions[0]
        
        # Update configuration
        if self.selected_element not in self.elements_config:
            self.elements_config[self.selected_element] = {}
            
        self.elements_config[self.selected_element]["region"] = best_match
        
        # Update info display
        self.update_element_info(self.selected_element)
        
        self.status_var.set(f"Updated region to best match for {self.selected_element}")
    
    def adjust_click_offset(self):
        """Adjust the click offset for the current element."""
        if not self.selected_element:
            messagebox.showwarning("No Selection", "Please select an element first.")
            return
            
        # Create a dialog to input offset values
        dialog = tk.Toplevel(self.root)
        dialog.title("Adjust Click Offset")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Enter X offset (pixels):").pack(pady=(20, 5))
        x_offset = ttk.Entry(dialog)
        x_offset.pack(pady=5)
        x_offset.insert(0, "0")
        
        ttk.Label(dialog, text="Enter Y offset (pixels):").pack(pady=(10, 5))
        y_offset = ttk.Entry(dialog)
        y_offset.pack(pady=5)
        y_offset.insert(0, "0")
        
        def save_offset():
            try:
                x_val = int(x_offset.get())
                y_val = int(y_offset.get())
                
                # Update configuration
                if self.selected_element not in self.elements_config:
                    self.elements_config[self.selected_element] = {}
                    
                self.elements_config[self.selected_element]["click_offset"] = (x_val, y_val)
                
                # Update info display
                self.update_element_info(self.selected_element)
                
                self.status_var.set(f"Updated click offset for {self.selected_element} to ({x_val}, {y_val})")
                dialog.destroy()
                
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid integer values for offsets.")
        
        ttk.Button(dialog, text="Save Offset", command=save_offset).pack(pady=20)
    
    def save_configuration(self):
        """Save the updated configuration."""
        # Update the configuration
        self.config.set("ui_elements", self.elements_config)
        
        # Save to file
        if self.config.save():
            messagebox.showinfo("Success", "Configuration saved successfully.")
            self.status_var.set("Configuration saved.")
        else:
            messagebox.showerror("Error", "Failed to save configuration.")
            self.status_var.set("Failed to save configuration.")

def main():
    """Main function to run the calibration tool."""
    root = tk.Tk()
    app = DebugBasedCalibrationTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()