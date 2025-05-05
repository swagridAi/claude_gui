#!/usr/bin/env python3
"""
Enhanced UI Calibration Tool for Claude Automation

This tool provides a visual interface to:
1. Capture a screenshot of the Claude interface
2. Highlight/select regions to identify UI elements
3. Capture reference images directly from the main interface
"""

import os
import sys
import time
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageGrab
import pyautogui
import cv2
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append('.')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SimplifiedCalibrationTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Claude UI Calibration Tool")
        self.root.state('zoomed')  # Maximize window
        
        # Initialize variables
        self.screenshot = None
        self.screenshot_image = None
        self.current_element = None
        self.elements = {}  # Dictionary to store element regions
        self.selection_start = None
        self.selection_box = None
        self.capture_mode = False  # Track if we're in region define mode or reference capture mode
        self.reference_count = {}  # Count of reference images per element
        
        # Set up the UI
        self.setup_ui()
        
        # Ensure directories exist
        self.setup_directories()
        
        # Load existing configuration if available
        self.load_configuration()
    
    def setup_directories(self):
        """Create necessary directories for assets."""
        os.makedirs("assets/reference_images", exist_ok=True)
        os.makedirs("config", exist_ok=True)
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main layout with two frames side by side
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel for controls
        control_frame = ttk.Frame(main_pane, padding=10)
        main_pane.add(control_frame, weight=1)
        
        # Right panel for screenshot
        canvas_frame = ttk.LabelFrame(main_pane, text="Screenshot")
        main_pane.add(canvas_frame, weight=3)
        
        # Control panel components
        ttk.Label(control_frame, text="Element Name:").pack(anchor="w", pady=(0, 5))
        
        # Element name entry with Add button
        element_frame = ttk.Frame(control_frame)
        element_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.element_var = tk.StringVar()
        self.element_entry = ttk.Entry(element_frame, textvariable=self.element_var)
        self.element_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(element_frame, text="Add Element", command=self.add_element).pack(side=tk.RIGHT)
        
        # Element list
        ttk.Label(control_frame, text="UI Elements:").pack(anchor="w", pady=(0, 5))
        
        self.element_listbox = tk.Listbox(control_frame, height=10)
        self.element_listbox.pack(fill=tk.X, pady=(0, 10))
        self.element_listbox.bind('<<ListboxSelect>>', self.on_element_select)
        
        # Element actions
        action_frame = ttk.Frame(control_frame)
        action_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(action_frame, text="Delete Element", command=self.delete_element).pack(side=tk.LEFT, padx=(0, 5))
        
        # Mode toggle button - will switch between "Define Region" and "Capture References"
        self.mode_button_var = tk.StringVar(value="Capture References")
        self.mode_button = ttk.Button(
            action_frame, 
            textvariable=self.mode_button_var,
            command=self.toggle_capture_mode
        )
        self.mode_button.pack(side=tk.RIGHT)
        
        # Capture button (only visible in reference capture mode)
        self.capture_button = ttk.Button(
            control_frame,
            text="Capture Selected Area as Reference",
            command=self.capture_current_selection,
            state=tk.DISABLED  # Initially disabled
        )
        self.capture_button.pack(fill=tk.X, pady=5)
        self.capture_button.pack_forget()  # Hide initially
        
        # Separator
        ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Screenshot actions
        ttk.Label(control_frame, text="Screenshot Controls:").pack(anchor="w", pady=(0, 5))
        
        screenshot_frame = ttk.Frame(control_frame)
        screenshot_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(screenshot_frame, text="Take Screenshot", command=self.take_screenshot).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(screenshot_frame, text="Load Image", command=self.load_image).pack(side=tk.LEFT)
        
        # Element info
        self.info_var = tk.StringVar(value="No element selected")
        ttk.Label(control_frame, textvariable=self.info_var, wraplength=200).pack(anchor="w", pady=10)
        
        # Save button
        ttk.Button(control_frame, text="Save Configuration", command=self.save_configuration).pack(anchor="w", pady=10)
        
        # Reference image preview
        ttk.Label(control_frame, text="Reference Images:").pack(anchor="w", pady=(10, 5))
        
        self.reference_frame = ttk.Frame(control_frame)
        self.reference_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for screenshot
        self.canvas = tk.Canvas(canvas_frame, bg="gray90")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Canvas bindings
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Mode indicator
        self.mode_indicator = ttk.Label(
            self.root, 
            text="Mode: Define Regions", 
            font=("Arial", 10, "bold"),
            background="#f0f0f0"
        )
        self.mode_indicator.pack(fill=tk.X, before=main_pane, pady=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM)
        
        # Welcome message
        self.status_var.set("Welcome! Start by taking a screenshot of the Claude interface.")
    
    def take_screenshot(self):
        """Take a screenshot of the screen."""
        self.root.iconify()  # Minimize window
        time.sleep(1)  # Wait for window to minimize
        
        try:
            self.screenshot = pyautogui.screenshot()
            self.update_canvas()
            self.status_var.set("Screenshot taken. Select regions by clicking and dragging.")
        except Exception as e:
            self.status_var.set(f"Error taking screenshot: {e}")
        
        self.root.deiconify()  # Restore window
    
    def load_image(self):
        """Load an image from file."""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg")]
        )
        
        if file_path:
            try:
                self.screenshot = Image.open(file_path)
                self.update_canvas()
                self.status_var.set("Image loaded. Select regions by clicking and dragging.")
            except Exception as e:
                self.status_var.set(f"Error loading image: {e}")
    
    def update_canvas(self):
        """Update the canvas with the current screenshot."""
        if self.screenshot:
            # Get canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # If canvas not yet sized, use defaults
            if canvas_width <= 1:
                canvas_width = 800
                canvas_height = 600
            
            # Keep aspect ratio
            img_width, img_height = self.screenshot.size
            scale = min(canvas_width / img_width, canvas_height / img_height)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # Resize the image
            resized = self.screenshot.copy()
            resized = resized.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.screenshot_image = ImageTk.PhotoImage(resized)
            
            # Clear canvas
            self.canvas.delete("all")
            
            # Draw the image
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.screenshot_image)
            self.canvas.config(scrollregion=(0, 0, new_width, new_height))
            
            # Store the scale factor for coordinate conversion
            self.scale = scale
            
            # Draw existing regions
            self.draw_regions()
    
    def draw_regions(self):
        """Draw all defined regions on the canvas."""
        if not self.screenshot:
            return
        
        # Clear previous regions
        self.canvas.delete("region")
        
        # Draw each element's region
        for name, region in self.elements.items():
            if region is None:
                continue
                
            # Determine color (green for selected, blue for others)
            color = "green" if name == self.current_element else "blue"
            
            # Scale coordinates to canvas size
            x, y, w, h = region
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
            
            # Draw label
            self.canvas.create_text(
                canvas_x + 5, canvas_y + 5,
                text=name, anchor=tk.NW,
                fill=color, tags="region"
            )
    
    def add_element(self):
        """Add a new element."""
        name = self.element_var.get().strip()
        
        if not name:
            messagebox.showwarning("Input Error", "Element name cannot be empty.")
            return
        
        if name in self.elements:
            messagebox.showwarning("Duplicate Element", f"Element '{name}' already exists.")
            return
        
        # Add element with empty region
        self.elements[name] = None
        
        # Add to listbox
        self.element_listbox.insert(tk.END, name)
        
        # Clear entry
        self.element_var.set("")
        
        # Set as current element
        self.current_element = name
        self.element_listbox.selection_clear(0, tk.END)
        index = list(self.elements.keys()).index(name)
        self.element_listbox.selection_set(index)
        
        # Initialize reference count
        self.reference_count[name] = 0
        
        # Create directory for reference images
        os.makedirs(f"assets/reference_images/{name}", exist_ok=True)
        
        self.status_var.set(f"Added element '{name}'. Now select its region on the screenshot.")
    
    def on_element_select(self, event):
        """Handle element selection from listbox."""
        selection = self.element_listbox.curselection()
        if selection:
            index = selection[0]
            name = self.element_listbox.get(index)
            self.current_element = name
            
            # Update info text
            region = self.elements[name]
            if region:
                x, y, w, h = region
                self.info_var.set(f"Element: {name}\nRegion: x={x}, y={y}, w={w}, h={h}\nReferences: {self.reference_count.get(name, 0)}")
            else:
                self.info_var.set(f"Element: {name}\nRegion: Not defined\nReferences: {self.reference_count.get(name, 0)}")
            
            # Redraw regions
            self.draw_regions()
            
            # Update reference image preview
            self.update_reference_preview(name)
    
    def delete_element(self):
        """Delete the selected element."""
        if not self.current_element:
            messagebox.showwarning("No Selection", "Please select an element to delete.")
            return
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Deletion", f"Delete element '{self.current_element}'?"):
            return
        
        # Remove from elements dictionary
        del self.elements[self.current_element]
        
        # Remove from listbox
        selection = self.element_listbox.curselection()
        if selection:
            self.element_listbox.delete(selection[0])
        
        # Reset current element
        self.current_element = None
        self.info_var.set("No element selected")
        
        # Redraw regions
        self.draw_regions()
        
        # Clear reference preview
        for widget in self.reference_frame.winfo_children():
            widget.destroy()
        
        self.status_var.set("Element deleted.")
    
    def toggle_capture_mode(self):
        """Toggle between region definition and reference capture modes."""
        if not self.current_element:
            messagebox.showwarning("No Selection", "Please select an element first.")
            return
        
        # Toggle capture mode
        self.capture_mode = not self.capture_mode
        
        if self.capture_mode:
            # Entering reference capture mode
            self.mode_button_var.set("Switch to Define Region Mode")
            self.mode_indicator.config(text="Mode: Capture References", background="#ffedad")
            self.capture_button.pack(fill=tk.X, pady=5)  # Show capture button
            self.status_var.set(f"Reference capture mode active for '{self.current_element}'. Select area to capture.")
        else:
            # Exiting reference capture mode, back to region definition
            self.mode_button_var.set("Switch to Capture References")
            self.mode_indicator.config(text="Mode: Define Regions", background="#f0f0f0")
            self.capture_button.pack_forget()  # Hide capture button
            self.status_var.set("Region definition mode active. Select areas to define element regions.")
    
    def on_mouse_down(self, event):
        """Handle mouse button press."""
        if not self.screenshot:
            return
            
        if not self.current_element:
            messagebox.showwarning("No Selection", "Please select an element first.")
            return
            
        self.selection_start = (event.x, event.y)
        
        # Clear previous selection box
        if self.selection_box:
            self.canvas.delete(self.selection_box)
            self.selection_box = None
    
    def on_mouse_drag(self, event):
        """Handle mouse drag."""
        if not self.selection_start:
            return
        
        # Clear previous selection box
        if self.selection_box:
            self.canvas.delete(self.selection_box)
        
        # Draw new selection box
        self.selection_box = self.canvas.create_rectangle(
            self.selection_start[0], self.selection_start[1],
            event.x, event.y,
            outline="red" if self.capture_mode else "blue", 
            width=2
        )
        
        # Update status with dimensions
        width = abs(event.x - self.selection_start[0])
        height = abs(event.y - self.selection_start[1])
        
        if self.capture_mode:
            self.status_var.set(f"Selection for reference capture: {width}x{height} pixels")
        else:
            self.status_var.set(f"Element region selection: {width}x{height} pixels")
    
    def on_mouse_up(self, event):
        """Handle mouse button release."""
        if not self.current_element or not self.selection_start:
            return
        
        # Calculate selection rectangle
        x1, y1 = self.selection_start
        x2, y2 = event.x, event.y
        
        # Ensure x1,y1 is top-left and x2,y2 is bottom-right
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        
        # Convert canvas coordinates to original image coordinates
        orig_left = int(left / self.scale)
        orig_top = int(top / self.scale)
        orig_width = int((right - left) / self.scale)
        orig_height = int((bottom - top) / self.scale)
        
        # Selection region in original image coordinates
        selection_region = (orig_left, orig_top, orig_width, orig_height)
        
        if self.capture_mode:
            # In capture mode, capture the selected region as a reference image
            self.capture_reference_image(selection_region)
        else:
            # In region definition mode, save the region for the element
            self.elements[self.current_element] = selection_region
            
            # Update info text
            self.info_var.set(f"Element: {self.current_element}\nRegion: x={orig_left}, y={orig_top}, w={orig_width}, h={orig_height}\nReferences: {self.reference_count.get(self.current_element, 0)}")
            
            self.status_var.set(f"Region defined for {self.current_element}.")
            
            # Redraw regions
            self.draw_regions()
        
        # Reset selection
        self.selection_start = None
    
    def capture_reference_image(self, region=None):
        """Capture a reference image from the current screenshot."""
        if not self.current_element:
            messagebox.showwarning("No Selection", "Please select an element first.")
            return
            
        if not self.screenshot:
            messagebox.showwarning("No Screenshot", "Please take a screenshot first.")
            return
            
        if not region:
            if self.selection_box:
                # Use current selection if available
                coords = self.canvas.coords(self.selection_box)
                x1, y1, x2, y2 = coords
                
                # Convert to original image coordinates
                left = min(x1, x2)
                top = min(y1, y2)
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                
                orig_left = int(left / self.scale)
                orig_top = int(top / self.scale)
                orig_width = int(width / self.scale)
                orig_height = int(height / self.scale)
                
                region = (orig_left, orig_top, orig_width, orig_height)
            else:
                messagebox.showwarning("No Selection", "Please select a region to capture.")
                return
        
        try:
            # Get current count
            count = self.reference_count.get(self.current_element, 0)
            
            # Create directory if it doesn't exist
            reference_dir = f"assets/reference_images/{self.current_element}"
            os.makedirs(reference_dir, exist_ok=True)
            
            # Extract region from screenshot
            x, y, w, h = region
            cropped = self.screenshot.crop((x, y, x + w, y + h))
            
            # Save as reference image
            timestamp = int(time.time())
            filename = f"{reference_dir}/{self.current_element}_{count+1}_{timestamp}.png"
            cropped.save(filename)
            
            # Increment count
            self.reference_count[self.current_element] = count + 1
            
            # Update info text
            element_region = self.elements[self.current_element]
            if element_region:
                rx, ry, rw, rh = element_region
                self.info_var.set(f"Element: {self.current_element}\nRegion: x={rx}, y={ry}, w={rw}, h={rh}\nReferences: {self.reference_count.get(self.current_element, 0)}")
            
            # Update reference image preview
            self.update_reference_preview(self.current_element)
            
            self.status_var.set(f"Captured reference image #{count+1} for {self.current_element}")
            
            # Flash the mode indicator to show success
            orig_bg = self.mode_indicator.cget("background")
            self.mode_indicator.config(background="green")
            self.root.after(200, lambda: self.mode_indicator.config(background=orig_bg))
            
        except Exception as e:
            messagebox.showerror("Capture Error", f"Error capturing reference: {e}")
    
    def capture_current_selection(self):
        """Capture the current selection as a reference image."""
        if self.selection_box:
            # Get the coordinates of the current selection box
            coords = self.canvas.coords(self.selection_box)
            x1, y1, x2, y2 = coords
            
            # Convert to original image coordinates
            left = min(x1, x2)
            top = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            
            orig_left = int(left / self.scale)
            orig_top = int(top / self.scale)
            orig_width = int(width / self.scale)
            orig_height = int(height / self.scale)
            
            region = (orig_left, orig_top, orig_width, orig_height)
            
            # Capture the reference image
            self.capture_reference_image(region)
        else:
            messagebox.showwarning("No Selection", "Please select a region to capture.")
    
    def update_reference_preview(self, element_name):
        """Update the reference image preview panel."""
        # Clear previous preview
        for widget in self.reference_frame.winfo_children():
            widget.destroy()
        
        # Get reference images for this element
        reference_dir = f"assets/reference_images/{element_name}"
        if not os.path.exists(reference_dir):
            os.makedirs(reference_dir, exist_ok=True)
        
        reference_files = sorted([f for f in os.listdir(reference_dir) if f.endswith(('.png', '.jpg', '.jpeg'))])
        
        # Update reference count for this element
        self.reference_count[element_name] = len(reference_files)
        
        if not reference_files:
            ttk.Label(self.reference_frame, text="No reference images").pack(pady=10)
            return
        
        # Create a canvas to show thumbnails
        preview_canvas = tk.Canvas(self.reference_frame, bg="white")
        preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Add a scrollbar if needed
        scrollbar = ttk.Scrollbar(self.reference_frame, orient=tk.VERTICAL, command=preview_canvas.yview)
        preview_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create a frame inside the canvas for the thumbnails
        frame = ttk.Frame(preview_canvas)
        preview_canvas.create_window((0, 0), window=frame, anchor=tk.NW)
        
        # Add thumbnails for each reference image
        self.thumbnail_refs = []  # Keep references to prevent garbage collection
        
        for i, filename in enumerate(reference_files):
            try:
                img = Image.open(os.path.join(reference_dir, filename))
                
                # Create a small thumbnail
                img.thumbnail((100, 100))
                photo = ImageTk.PhotoImage(img)
                self.thumbnail_refs.append(photo)
                
                # Create a frame for this thumbnail
                thumbnail_frame = ttk.Frame(frame)
                thumbnail_frame.grid(row=i//2, column=i%2, padx=5, pady=5)
                
                # Add the thumbnail
                label = ttk.Label(thumbnail_frame, image=photo)
                label.pack()
                
                # Add the filename (shortened)
                short_name = filename[:12] + "..." if len(filename) > 15 else filename
                ttk.Label(thumbnail_frame, text=short_name).pack()
                
                # Add delete button
                ttk.Button(
                    thumbnail_frame, 
                    text="Delete", 
                    command=lambda f=filename: self.delete_reference(element_name, f)
                ).pack(pady=(0, 5))
                
            except Exception as e:
                logging.error(f"Error loading thumbnail: {e}")
        
        # Update canvas scroll region
        frame.update_idletasks()
        preview_canvas.config(scrollregion=preview_canvas.bbox("all"))
    
    def delete_reference(self, element_name, filename):
        """Delete a reference image."""
        if messagebox.askyesno("Confirm Deletion", f"Delete reference image {filename}?"):
            try:
                os.remove(os.path.join(f"assets/reference_images/{element_name}", filename))
                
                # Update reference count
                self.reference_count[element_name] = max(0, self.reference_count.get(element_name, 0) - 1)
                
                # Update preview
                self.update_reference_preview(element_name)
                
                # Update info text
                if self.current_element == element_name:
                    region = self.elements[element_name]
                    if region:
                        x, y, w, h = region
                        self.info_var.set(f"Element: {element_name}\nRegion: x={x}, y={y}, w={w}, h={h}\nReferences: {self.reference_count.get(element_name, 0)}")
                
                self.status_var.set(f"Deleted reference image {filename}")
            except Exception as e:
                messagebox.showerror("Delete Error", f"Error deleting reference: {e}")
    
    def save_configuration(self):
        """Save the configuration to file."""
        if not self.elements:
            messagebox.showwarning("No Elements", "No elements have been defined.")
            return
        
        try:
            # Find elements with no regions
            incomplete = [name for name, region in self.elements.items() if region is None]
            if incomplete:
                messagebox.showwarning("Incomplete Configuration", 
                                      f"The following elements have no regions defined:\n{', '.join(incomplete)}")
                return
            
            # Create configuration
            config = {
                "claude_url": "https://claude.ai",
                "browser_profile": "C:\\Temp\\ClaudeProfile",
                "debug": False,
                "ui_elements": {}
            }
            
            # Add UI elements
            for name, region in self.elements.items():
                reference_dir = f"assets/reference_images/{name}"
                reference_files = sorted([os.path.join(reference_dir, f) for f in os.listdir(reference_dir) 
                                        if f.endswith(('.png', '.jpg', '.jpeg'))])
                
                config["ui_elements"][name] = {
                    "reference_paths": reference_files,
                    "region": region,
                    "confidence": 0.7
                }
            
            # Add default prompts
            config["prompts"] = [
                "Summarize the latest AI trends.",
                "Explain how reinforcement learning works.",
                "Write a Python function that reverses a string."
            ]
            
            # Save to YAML file
            import yaml
            
            # Define custom YAML handler for tuples - match the same format as config_manager.py
            def represent_tuple(dumper, data):
                return dumper.represent_sequence('tag:yaml.org,2002:seq', list(data))
                
            # Register the representer
            yaml.add_representer(tuple, represent_tuple)
            
            with open("config/user_config.yaml", "w") as f:
                yaml.dump(config, f, default_flow_style=False)
            
            messagebox.showinfo("Success", "Configuration saved successfully.")
            self.status_var.set("Configuration saved to config/user_config.yaml")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving configuration: {e}")
            
    def load_configuration(self):
        """Load configuration from file."""
        config_file = "config/user_config.yaml"
        
        if not os.path.exists(config_file):
            self.status_var.set("No existing configuration found. Starting with empty configuration.")
            return
            
        try:
            import yaml
            
            # Add custom YAML constructor for Python tuples - use the same tag as config_manager.py
            def construct_tuple(loader, node):
                return tuple(loader.construct_sequence(node))
            
            # Register the constructor
            yaml.add_constructor('tag:yaml.org,2002:python/tuple', construct_tuple)
            
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                
            if not config or 'ui_elements' not in config:
                self.status_var.set("Invalid configuration file. Starting with empty configuration.")
                return
                
            # Load UI elements
            for name, element_config in config['ui_elements'].items():
                # Add element to our dictionary
                self.elements[name] = element_config.get('region')
                
                # Add to listbox
                self.element_listbox.insert(tk.END, name)
                
                # Count reference images
                reference_paths = element_config.get('reference_paths', [])
                self.reference_count[name] = len(reference_paths)
                
                # Create directory for reference images if it doesn't exist
                os.makedirs(f"assets/reference_images/{name}", exist_ok=True)
            
            # Select the first element if any exist
            if self.elements:
                self.element_listbox.selection_set(0)
                self.current_element = self.element_listbox.get(0)
                self.on_element_select(None)  # Update UI for selected element
                
            self.status_var.set(f"Loaded configuration with {len(self.elements)} elements")
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Error loading configuration: {e}")
            self.status_var.set("Failed to load configuration. Starting with empty configuration.")


def main():
    """Main function to run the calibration tool."""
    root = tk.Tk()
    app = SimplifiedCalibrationTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()