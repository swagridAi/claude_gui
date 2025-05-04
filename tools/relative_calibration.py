#!/usr/bin/env python3
"""
Interactive calibration tool for relative regions in Claude GUI Automation.
"""

import os
import sys
import time
import logging
import argparse
import pyautogui
import cv2
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append('.')

from src.utils.config_manager import ConfigManager
from src.models.ui_element import UIElement
from src.utils.reference_manager import ReferenceImageManager
from src.utils.region_manager import RegionManager

def setup_logging():
    """Set up logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def interactive_relative_calibration(config):
    """
    Interactive calibration for relative regions.
    
    Args:
        config: ConfigManager instance
    """
    import tkinter as tk
    from tkinter import ttk
    from PIL import Image, ImageTk
    
    class RelativeCalibrationApp:
        def __init__(self, root, config):
            self.root = root
            self.root.title("Relative Region Calibration")
            self.root.geometry("900x700")
            
            self.config = config
            self.reference_manager = ReferenceImageManager()
            self.region_manager = RegionManager()
            
            # Screenshot and region variables
            self.screenshot = None
            self.screenshot_image = None
            self.regions = {}
            self.current_element = None
            self.parent_element = None
            self.selection_start = None
            self.selection_box = None
            self.screen_width, self.screen_height = pyautogui.size()
            
            # UI Setup
            self.setup_ui()
            
            # Take initial screenshot
            self.take_screenshot()
            
        def setup_ui(self):
            """Set up the UI components."""
            main_frame = ttk.Frame(self.root, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Element selection area
            control_frame = ttk.LabelFrame(main_frame, text="Control Panel", padding=5)
            control_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # First row - element selection
            element_frame = ttk.Frame(control_frame)
            element_frame.pack(fill=tk.X, padx=5, pady=5)
            
            ttk.Label(element_frame, text="Element:").pack(side=tk.LEFT, padx=5)
            
            self.element_var = tk.StringVar()
            self.element_combo = ttk.Combobox(element_frame, textvariable=self.element_var, width=20)
            self.element_combo.pack(side=tk.LEFT, padx=5)
            
            ttk.Button(element_frame, text="New Element", command=self.add_new_element).pack(side=tk.LEFT, padx=5)
            
            # New element dialog setup
            self.new_element_dialog = tk.Toplevel(self.root)
            self.new_element_dialog.withdraw()
            self.new_element_dialog.title("New Element")
            
            ttk.Label(self.new_element_dialog, text="Element Name:").pack(padx=10, pady=5)
            self.new_element_name = ttk.Entry(self.new_element_dialog, width=30)
            self.new_element_name.pack(padx=10, pady=5)
            
            dialog_buttons = ttk.Frame(self.new_element_dialog)
            dialog_buttons.pack(padx=10, pady=10)
            ttk.Button(dialog_buttons, text="Create", command=self.create_new_element).pack(side=tk.LEFT, padx=5)
            ttk.Button(dialog_buttons, text="Cancel", command=lambda: self.new_element_dialog.withdraw()).pack(side=tk.LEFT, padx=5)
            
            # Second row - parent selection
            parent_frame = ttk.Frame(control_frame)
            parent_frame.pack(fill=tk.X, padx=5, pady=5)
            
            ttk.Label(parent_frame, text="Parent:").pack(side=tk.LEFT, padx=5)
            
            self.parent_var = tk.StringVar(value="screen")
            self.parent_combo = ttk.Combobox(parent_frame, textvariable=self.parent_var, width=20)
            self.parent_combo.pack(side=tk.LEFT, padx=5)
            
            # Action buttons
            button_frame = ttk.Frame(control_frame)
            button_frame.pack(fill=tk.X, padx=5, pady=5)
            
            ttk.Button(button_frame, text="Take Screenshot", command=self.take_screenshot).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Capture Region", command=self.start_region_capture).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Clear Region", command=self.clear_region).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Save Configuration", command=self.save_configuration).pack(side=tk.LEFT, padx=5)
            
            # Relative region info
            info_frame = ttk.Frame(control_frame)
            info_frame.pack(fill=tk.X, padx=5, pady=5)
            
            self.region_info_var = tk.StringVar(value="No region selected")
            ttk.Label(info_frame, textvariable=self.region_info_var).pack(side=tk.LEFT, padx=5)
            
            # Canvas for screenshot
            canvas_frame = ttk.LabelFrame(main_frame, text="Screenshot")
            canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            self.canvas = tk.Canvas(canvas_frame, bg="gray90")
            self.canvas.pack(fill=tk.BOTH, expand=True)
            
            # Canvas interactions
            self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
            self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
            
            # Status bar
            self.status_var = tk.StringVar(value="Ready")
            status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
            status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
            
            # Load existing elements
            self.refresh_element_lists()
            
        def refresh_element_lists(self):
            """Refresh the element and parent lists."""
            ui_elements = self.config.get("ui_elements", {})
            element_names = list(ui_elements.keys())
            
            self.element_combo['values'] = element_names
            
            parent_options = ["screen"] + element_names
            self.parent_combo['values'] = parent_options
            
            # Set defaults if needed
            if element_names and not self.element_var.get():
                self.element_var.set(element_names[0])
            
        def take_screenshot(self):
            """Take a screenshot of the screen."""
            self.root.withdraw()  # Hide window
            time.sleep(0.5)  # Wait for window to hide
            
            try:
                self.screenshot = pyautogui.screenshot()
                self.update_canvas()
                self.status_var.set("Screenshot taken. Select region by clicking and dragging.")
            except Exception as e:
                self.status_var.set(f"Error taking screenshot: {e}")
                
            self.root.deiconify()  # Show window again
            
        def update_canvas(self):
            """Update the canvas with the current screenshot."""
            if self.screenshot:
                # Resize screenshot to fit canvas
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                
                if canvas_width <= 1:  # Canvas not yet drawn
                    canvas_width = 800
                    canvas_height = 600
                
                # Keep aspect ratio
                img_width, img_height = self.screenshot.size
                scale = min(canvas_width / img_width, canvas_height / img_height)
                
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                resized = self.screenshot.resize((new_width, new_height), Image.LANCZOS)
                self.screenshot_image = ImageTk.PhotoImage(resized)
                
                # Clear canvas
                self.canvas.delete("all")
                
                # Draw image
                self.canvas.create_image(0, 0, anchor=tk.NW, image=self.screenshot_image)
                self.canvas.config(scrollregion=(0, 0, new_width, new_height))
                
                # Save scale factor for coordinate conversion
                self.scale = scale
                
                # Draw existing regions
                self.draw_existing_regions()
                
        def draw_existing_regions(self):
            """Draw existing regions on the canvas."""
            ui_elements = self.config.get("ui_elements", {})
            
            # Clear previous region boxes
            self.canvas.delete("region")
            
            # Draw each element's region
            for name, element_config in ui_elements.items():
                # Skip if no region defined
                if "region" not in element_config and "relative_region" not in element_config:
                    continue
                    
                # Get color based on current selection
                color = "green" if name == self.element_var.get() else "blue"
                
                try:
                    # Create UIElement
                    region = element_config.get("region")
                    relative_region = element_config.get("relative_region")
                    parent = element_config.get("parent")
                    
                    if region:  # Absolute region
                        x, y, w, h = region
                        # Convert to canvas coordinates
                        canvas_x = x * self.scale
                        canvas_y = y * self.scale
                        canvas_w = w * self.scale
                        canvas_h = h * self.scale
                        
                        # Draw rectangle
                        self.canvas.create_rectangle(
                            canvas_x, canvas_y, 
                            canvas_x + canvas_w, canvas_y + canvas_h,
                            outline=color, width=2, tags="region"
                        )
                        
                        # Label
                        self.canvas.create_text(
                            canvas_x + 5, canvas_y + 5,
                            text=name, anchor=tk.NW,
                            fill=color, tags="region"
                        )
                    
                    elif relative_region:  # Relative region
                        # Create temporary UIElement
                        element = UIElement(
                            name=name,
                            relative_region=relative_region,
                            parent=parent
                        )
                        
                        # Load all elements
                        ui_elements_dict = {}
                        for n, cfg in ui_elements.items():
                            ui_elements_dict[n] = UIElement(
                                name=n,
                                region=cfg.get("region"),
                                relative_region=cfg.get("relative_region"),
                                parent=cfg.get("parent")
                            )
                        
                        # Calculate effective region
                        effective_region = element.get_effective_region(ui_elements_dict)
                        
                        if effective_region:
                            x, y, w, h = effective_region
                            # Convert to canvas coordinates
                            canvas_x = x * self.scale
                            canvas_y = y * self.scale
                            canvas_w = w * self.scale
                            canvas_h = h * self.scale
                            
                            # Draw rectangle
                            self.canvas.create_rectangle(
                                canvas_x, canvas_y, 
                                canvas_x + canvas_w, canvas_y + canvas_h,
                                outline=color, width=2, dash=(5, 5), tags="region"
                            )
                            
                            # Label
                            self.canvas.create_text(
                                canvas_x + 5, canvas_y + 5,
                                text=f"{name} (rel to {parent or 'screen'})",
                                anchor=tk.NW, fill=color, tags="region"
                            )
                except Exception as e:
                    logging.warning(f"Error drawing region for {name}: {e}")
                
        def start_region_capture(self):
            """Start the region capture process."""
            element_name = self.element_var.get()
            parent_name = self.parent_var.get()
            
            if not element_name:
                self.status_var.set("Please select an element first")
                return
                
            self.current_element = element_name
            self.parent_element = parent_name if parent_name != "screen" else None
            
            self.clear_region()
            self.status_var.set(f"Capturing region for {element_name}. Click and drag to select.")
            
        def add_new_element(self):
            """Show dialog to add a new element."""
            self.new_element_name.delete(0, tk.END)
            self.new_element_dialog.deiconify()
            self.new_element_dialog.lift()
            self.new_element_name.focus()
            
        def create_new_element(self):
            """Create a new element from dialog input."""
            name = self.new_element_name.get().strip()
            
            if not name:
                self.status_var.set("Element name cannot be empty")
                return
                
            # Get existing UI elements
            ui_elements = self.config.get("ui_elements", {})
            
            # Check if element already exists
            if name in ui_elements:
                self.status_var.set(f"Element {name} already exists")
                self.new_element_dialog.withdraw()
                return
                
            # Create new empty element
            ui_elements[name] = {
                "reference_paths": [],
                "confidence": 0.7
            }
            
            # Update config
            self.config.set("ui_elements", ui_elements)
            
            # Refresh dropdown lists
            self.refresh_element_lists()
            
            # Select the new element
            self.element_var.set(name)
            
            # Hide dialog
            self.new_element_dialog.withdraw()
            
            self.status_var.set(f"Created new element: {name}")
            
        def on_mouse_down(self, event):
            """Handle mouse button press event."""
            if not self.current_element:
                return
                
            self.selection_start = (event.x, event.y)
            
            # Clear previous selection
            if self.selection_box:
                self.canvas.delete(self.selection_box)
                self.selection_box = None
                
        def on_mouse_drag(self, event):
            """Handle mouse drag event."""
            if not self.current_element or not self.selection_start:
                return
                
            x1, y1 = self.selection_start
            x2, y2 = event.x, event.y
            
            # Clear previous selection
            if self.selection_box:
                self.canvas.delete(self.selection_box)
                
            # Draw new selection
            self.selection_box = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline="red", width=2
            )
            
            # Show dimensions
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            
            self.status_var.set(f"Selection: {width}x{height} pixels")
            
        def on_mouse_up(self, event):
            """Handle mouse button release event."""
            if not self.current_element or not self.selection_start:
                return
                
            x1, y1 = self.selection_start
            x2, y2 = event.x, event.y
            
            # Ensure x1,y1 is top-left and x2,y2 is bottom-right
            left = min(x1, x2)
            top = min(y1, y2)
            right = max(x1, x2)
            bottom = max(y1, y2)
            
            # Calculate selection in original coordinates
            orig_left = int(left / self.scale)
            orig_top = int(top / self.scale)
            orig_width = int((right - left) / self.scale)
            orig_height = int((bottom - top) / self.scale)
            
            # Save region
            absolute_region = (orig_left, orig_top, orig_width, orig_height)
            
            # If parent is set, convert to relative
            if self.parent_element:
                # Get parent element config
                ui_elements = self.config.get("ui_elements", {})
                parent_config = ui_elements.get(self.parent_element, {})
                
                # Get parent region
                parent_region = parent_config.get("region")
                
                if parent_region:
                    px, py, pw, ph = parent_region
                    
                    # Calculate relative to parent
                    rel_x = (orig_left - px) / pw
                    rel_y = (orig_top - py) / ph
                    rel_w = orig_width / pw
                    rel_h = orig_height / ph
                    
                    relative_region = (rel_x, rel_y, rel_w, rel_h)
                    
                    self.region_info_var.set(
                        f"Relative to {self.parent_element}: "
                        f"({rel_x:.2f}, {rel_y:.2f}, {rel_w:.2f}, {rel_h:.2f})"
                    )
                    
                    # Update config
                    ui_elements[self.current_element] = ui_elements.get(self.current_element, {})
                    ui_elements[self.current_element]["relative_region"] = relative_region
                    ui_elements[self.current_element]["parent"] = self.parent_element
                    
                    # Remove absolute region if it exists
                    if "region" in ui_elements[self.current_element]:
                        del ui_elements[self.current_element]["region"]
                        
                    self.config.set("ui_elements", ui_elements)
                else:
                    self.status_var.set(f"Parent {self.parent_element} has no region defined")
            else:
                # Screen-relative coordinates
                rel_x = orig_left / self.screen_width
                rel_y = orig_top / self.screen_height
                rel_w = orig_width / self.screen_width
                rel_h = orig_height / self.screen_height
                
                relative_region = (rel_x, rel_y, rel_w, rel_h)
                
                self.region_info_var.set(
                    f"Relative to screen: "
                    f"({rel_x:.2f}, {rel_y:.2f}, {rel_w:.2f}, {rel_h:.2f})"
                )
                
                # Update config
                ui_elements = self.config.get("ui_elements", {})
                ui_elements[self.current_element] = ui_elements.get(self.current_element, {})
                ui_elements[self.current_element]["relative_region"] = relative_region
                
                # Remove parent and absolute region if they exist
                if "parent" in ui_elements[self.current_element]:
                    del ui_elements[self.current_element]["parent"]
                if "region" in ui_elements[self.current_element]:
                    del ui_elements[self.current_element]["region"]
                    
                self.config.set("ui_elements", ui_elements)
                
            self.status_var.set(f"Captured region for {self.current_element}")
            
            # Redraw regions
            self.draw_existing_regions()
            
        def clear_region(self):
            """Clear the current selection."""
            if self.selection_box:
                self.canvas.delete(self.selection_box)
                self.selection_box = None
                
            self.selection_start = None
            self.region_info_var.set("No region selected")
            
        def save_configuration(self):
            """Save the current configuration to file."""
            success = self.config.save()
            
            if success:
                self.status_var.set("Configuration saved successfully")
            else:
                self.status_var.set("Error saving configuration")
    
    # Create and run the application
    root = tk.Tk()
    app = RelativeCalibrationApp(root, config)
    root.mainloop()

def main():
    """Main function to run the relative calibration tool."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Relative region calibration for Claude GUI Automation")
    parser.add_argument("--config", help="Path to config file", default="config/user_config.yaml")
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    
    # Load configuration
    config = ConfigManager(args.config)
    
    # Start interactive calibration
    interactive_relative_calibration(config)

if __name__ == "__main__":
    main()