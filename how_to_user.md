# Claude GUI Automation - User Guide

## Introduction

Claude GUI Automation is an advanced screen automation tool designed to interact with Claude AI through its web interface. Unlike API-based approaches, this tool simulates human-like interactions through mouse movements, keyboard input, and visual recognition, allowing it to bypass CAPTCHA and login requirements that might block other automation methods.

This implementation uses an image recognition-based approach rather than fixed coordinates, making it significantly more robust against UI changes and screen resolution differences.

## Project Overview

### Key Features

- **Image Recognition**: Uses template matching to locate UI elements rather than fixed coordinates
- **Self-Calibration**: Automatically detects UI elements and adjusts to different screen sizes
- **State Management**: Robust state machine for reliable automation flow
- **Enhanced OCR**: Advanced text extraction with preprocessing for better accuracy
- **Visual Debugging**: Comprehensive logging with screenshots for troubleshooting
- **Adaptive Timing**: Waits for visual changes rather than fixed delays

### Use Cases

- Batch processing of multiple prompts
- Automated data collection from Claude responses
- Research workflows that require consistent question patterns
- Comparative analysis of responses to similar prompts

## Installation & Setup

### Prerequisites

- Python 3.8+
- Tesseract OCR installed and in your PATH
- Chrome browser
- Active Claude account

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/claude-automation.git
   cd claude-automation
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Tesseract OCR:
   - Windows: `choco install tesseract`
   - macOS: `brew install tesseract`
   - Linux: `sudo apt install tesseract-ocr`

4. Create reference images directory:
   ```bash
   mkdir -p assets/reference_images/{prompt_box,send_button,thinking_indicator,response_complete}
   ```

## Usage Guide

### Quick Start

1. Run the calibration tool to detect UI elements:
   ```bash
   python -m tools.calibrate_ui
   ```

2. Edit the prompts in `config/user_config.yaml`:
   ```yaml
   prompts:
     - "Summarize the latest AI trends."
     - "Explain how reinforcement learning works."
     - "Write a Python function that reverses a string."
   ```

3. Run the automation:
   ```bash
   python src/main.py
   ```

### Capturing Reference Images

To create your own reference images for UI elements:

1. Run the reference image capture tool:
   ```bash
   python -m tools.capture_reference
   ```

2. Follow the prompts to hover over and capture screenshots of:
   - The prompt input box
   - The send button
   - The "thinking" indicator (if visible)
   - A sample response area

### Configuration Options

Edit `config/user_config.yaml` to customize:

- Browser profile location
- Prompt list
- Timeout settings
- OCR configuration
- Debug settings

Example configuration:

```yaml
# Browser settings
claude_url: "https://claude.ai"
browser_profile: "C:\\Temp\\ClaudeProfile"

# Automation settings
prompts:
  - "Summarize the latest AI trends."
  - "Explain how reinforcement learning works."
  - "Write a Python function that reverses a string."

# Runtime settings
max_retries: 3
response_timeout: 60
delay_between_prompts: 3
debug: true
```

## File Structure Explanation

### Core Components

#### `src/main.py`
The entry point to the application that parses command-line arguments, sets up logging, loads configuration, and initializes the state machine. It handles the overall execution flow and graceful shutdown.

#### `src/automation/state_machine.py`
The heart of the application that implements a robust state machine controlling the automation flow. It manages transitions between states like browser launch, login, sending prompts, waiting for responses, and error recovery.

#### `src/automation/recognition.py`
Contains the core image recognition functionality using both PyAutoGUI's built-in functions and advanced OpenCV methods. This module is responsible for finding UI elements on screen using reference images.

#### `src/automation/interaction.py`
Handles all user interface interactions including mouse clicks, keyboard input, and text entry. It abstracts the low-level PyAutoGUI commands into higher-level functions.

#### `src/automation/ocr.py`
Implements enhanced OCR capabilities with image preprocessing to improve text extraction accuracy. It handles adaptive thresholding, contrast enhancement, and noise reduction before passing images to Tesseract.

#### `src/automation/browser.py`
Manages the browser launch process, profile handling, and navigation to Claude's website. It ensures proper startup and environment preparation.

### Utilities

#### `src/utils/calibration.py`
Automatically detects UI elements and saves their positions to the configuration file. This module makes the automation tool resilient to different screen sizes and UI layouts.

#### `src/utils/logging_utils.py`
Provides enhanced logging with screenshot capture to help troubleshoot automation issues. It creates timestamped log directories with both text logs and visual evidence.

#### `src/utils/image_processing.py`
Contains computer vision utilities for preprocessing images before recognition or OCR. This includes contrast enhancement, noise reduction, and edge detection.

#### `src/utils/config_manager.py`
Handles loading, validation, and saving of configuration files. It provides a clean interface for accessing and modifying configuration values.

### Models

#### `src/models/ui_element.py`
Defines the UIElement class that represents a clickable or recognizable element on screen, with properties like reference images, search region, and confidence threshold.

#### `src/models/prompt.py`
Represents a prompt to be sent to Claude, with methods for validation and preprocessing.

#### `src/models/response.py`
Encapsulates Claude's responses with metadata and processing methods.

### Tools

#### `tools/capture_reference.py`
A utility script for capturing reference images of UI elements for use in image recognition.

#### `tools/calibrate_ui.py`
A standalone tool that runs the UI calibration process to detect and save UI element positions.

#### `tools/visual_debugger.py`
An interactive debugging tool that visualizes the detected UI elements and search regions for troubleshooting.

## Troubleshooting

### Common Issues

#### Recognition Failures

If the tool fails to recognize UI elements:

1. Run the visual debugger to see what's being detected:
   ```bash
   python -m tools.visual_debugger
   ```

2. Capture new reference images that better match your current UI:
   ```bash
   python -m tools.capture_reference
   ```

3. Decrease the confidence threshold in your config file:
   ```yaml
   ui_elements:
     prompt_box:
       confidence: 0.6  # Lower value = more lenient matching
   ```

#### OCR Issues

If text extraction produces incorrect results:

1. Enable OCR preprocessing in your config:
   ```yaml
   ocr:
     preprocess: true
     contrast_enhance: true
     denoise: true
   ```

2. Try different Tesseract configuration:
   ```yaml
   ocr:
     engine: "tesseract"
     config: "--psm 6 --oem 1"
   ```

3. Ensure the response area is correctly defined to capture only the text.

#### Browser Launch Failures

If the browser doesn't launch correctly:

1. Verify the Chrome path in `automation/browser.py`
2. Ensure you have a valid Chrome profile directory
3. Try running with debug mode enabled:
   ```bash
   python src/main.py --debug
   ```

## Advanced Usage

### Running Headless Mode

For server environments, you can adapt the tool to use a virtual display:

```python
from pyvirtualdisplay import Display

display = Display(visible=0, size=(1920, 1080))
display.start()

# Run your automation
# ...

display.stop()
```

### Extending with Custom States

To add new functionality, extend the `AutomationState` enum and add corresponding handler methods:

```python
# In state_machine.py
class AutomationState(Enum):
    # Existing states...
    CUSTOM_ACTION = auto()

# Add handler method
def _handle_custom_action(self):
    # Implementation
    self.state = AutomationState.NEXT_STATE
```

### Scheduled Execution

Use cron (Linux/Mac) or Task Scheduler (Windows) to run the tool on a schedule:

```bash
# Example cron entry (runs daily at 9 AM)
0 9 * * * cd /path/to/claude-automation && python src/main.py
```

## Best Practices

1. **Always respect Claude's terms of service** and use this tool responsibly.
2. **Avoid excessive automation** that might trigger anti-bot measures.
3. **Keep reference images up to date** as Claude's UI evolves.
4. **Run in debug mode** when setting up to catch issues early.
5. **Back up your config files** before making changes.

## Contributing Guidelines

Contributions to improve the tool are welcome! Please follow these guidelines:

1. Create a fork of the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.