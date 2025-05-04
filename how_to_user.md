# Claude GUI Automation - User Guide

## Introduction

Claude GUI Automation is an advanced screen automation tool designed to interact with Claude AI through its web interface. Unlike API-based approaches, this tool simulates human-like interactions through mouse movements, keyboard input, and visual recognition, allowing it to bypass CAPTCHA and login requirements that might block other automation methods.

This implementation uses an image recognition-based approach rather than fixed coordinates, making it significantly more robust against UI changes and screen resolution differences.

## Project Overview

### Key Features

- **Image Recognition**: Uses template matching to locate UI elements rather than fixed coordinates
- **Self-Calibration**: Automatically detects UI elements and adjusts to different screen sizes
- **Simplified State Machine**: Streamlined automation flow focused on reliable prompt delivery
- **Smart Retry Mechanism**: Intelligent error recovery with exponential backoff, jitter, and failure-specific strategies
- **Visual Debugging**: Comprehensive logging with screenshots for troubleshooting
- **Reliable Browser Management**: Ensures proper browser startup and shutdown

### Use Cases

- Batch processing of multiple prompts
- Automated testing of Claude's responses
- Research workflows that require consistent question patterns
- Data collection tasks requiring repeated inputs

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
   mkdir -p assets/reference_images/{prompt_box,send_button,thinking_indicator}
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

The system will:
- Launch Chrome and navigate to Claude
- Wait for you to complete login if needed
- Automatically send your prompts with configured delays between them
- Handle any errors encountered and retry as needed
- Close the browser when complete

### Command-Line Arguments

The following command-line arguments are available:

```bash
python src/main.py [OPTIONS]

Options:
  --config PATH         Path to config file (default: config/user_config.yaml)
  --debug               Enable debug mode with verbose logging
  --calibrate           Run calibration before starting
  --max-retries NUMBER  Override maximum retry attempts
  --retry-delay NUMBER  Override initial delay between retries (seconds)
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

### Configuration Options

Edit `config/user_config.yaml` to customize:

- Browser profile location
- Prompt list
- Timeout settings
- Retry mechanism settings
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
delay_between_prompts: 3
debug: false

# Retry settings
retry_delay: 2          # Initial delay between retries in seconds
max_retry_delay: 30     # Maximum delay between retries in seconds
retry_jitter: 0.5       # Random jitter factor (0.5 means ±50%)
retry_backoff: 1.5      # Exponential backoff multiplier
```

## Retry Mechanism

The system includes a sophisticated retry mechanism that improves reliability when sending prompts:

### Failure Types

The system detects and handles different types of failures:

- **UI Not Found**: When elements like prompt box can't be located
- **Network Error**: Connection issues with Claude's website
- **Browser Error**: Chrome crashes or freezes
- **Unknown Error**: Fallback category for other issues

### Recovery Strategies

Each failure type triggers a specific recovery approach:

- **UI issues**: Refreshes the page and checks login status
- **Network issues**: Waits longer before refreshing
- **Browser crashes**: Completely restarts the browser
- **Unknown issues**: Starts with simple fixes, escalates to restart if needed

### Exponential Backoff with Jitter

The system uses smart timing between retries:
- Each retry waits progressively longer (exponential backoff)
- Random variation in timing prevents synchronization issues
- Maximum delay cap prevents excessive waits

### Recommended Settings

- **For stable connections**: Default settings (3 retries, 2-second initial delay)
- **For unreliable networks**: Increase max_retries to 5 and retry_delay to 5
- **For complex prompts**: Increase delay_between_prompts to 5 or higher

## File Structure Explanation

### Core Components

#### `src/main.py`
The entry point that parses command-line arguments, sets up logging, loads configuration, and initializes the state machine.

#### `src/automation/simplified_state_machine.py`
The streamlined state machine controlling the automation flow. It focuses specifically on sending prompts reliably with enhanced error recovery.

#### `src/automation/recognition.py`
Contains the core image recognition functionality using both PyAutoGUI's built-in functions and advanced OpenCV methods.

#### `src/automation/interaction.py`
Handles all user interface interactions including mouse clicks, keyboard input, and text entry.

#### `src/automation/browser.py`
Manages the browser launch process, profile handling, navigation, and ensures proper browser closure.

### Utilities

#### `src/utils/calibration.py`
Automatically detects UI elements and saves their positions to the configuration file.

#### `src/utils/logging_utils.py`
Provides enhanced logging with screenshot capture to help troubleshoot automation issues.

#### `src/utils/image_processing.py`
Contains computer vision utilities for preprocessing images before recognition.

#### `src/utils/config_manager.py`
Handles loading, validation, and saving of configuration files.

### Models

#### `src/models/ui_element.py`
Defines the UIElement class that represents a clickable or recognizable element on screen.

### Tools

#### `tools/capture_reference.py`
A utility script for capturing reference images of UI elements for use in image recognition.

#### `tools/calibrate_ui.py`
A standalone tool that runs the UI calibration process to detect and save UI element positions.

#### `tools/visual_debugger.py`
An interactive debugging tool that visualizes the detected UI elements and search regions.

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

#### Retry Loop Issues

If the system gets stuck in a retry loop:

1. Enable debug mode to see detailed logs:
   ```bash
   python src/main.py --debug
   ```

2. Check the screenshots in logs/screenshots to see what's happening during retries

3. Adjust retry settings for your specific environment:
   ```bash
   python src/main.py --max-retries 5 --retry-delay 5
   ```

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
# In simplified_state_machine.py
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
5. **Use reasonable delays between prompts** (3-5 seconds minimum recommended).
6. **Adjust retry settings** based on your network stability and use case.
7. **Back up your config files** before making changes.

## Contributing Guidelines

Contributions to improve the tool are welcome! Please follow these guidelines:

1. Create a fork of the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
