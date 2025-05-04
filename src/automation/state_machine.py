from enum import Enum, auto
import logging
import time
from src.automation.browser import launch_browser
from src.automation.recognition import find_element, wait_for_visual_change
from src.automation.interaction import click_element, send_text
from src.automation.ocr import extract_text_from_region
from src.models.ui_element import UIElement
from src.utils.logging_utils import log_with_screenshot

class AutomationState(Enum):
    INITIALIZE = auto()
    BROWSER_LAUNCH = auto()
    WAIT_FOR_LOGIN = auto()
    READY_FOR_PROMPT = auto()
    SEND_PROMPT = auto()
    WAIT_FOR_RESPONSE = auto()
    CAPTURE_RESPONSE = auto()
    COMPLETE = auto()
    ERROR = auto()

class AutomationStateMachine:
    def __init__(self, config):
        self.config = config
        self.state = AutomationState.INITIALIZE
        self.prompts = config.get("prompts", [])
        self.current_prompt_index = 0
        self.results = []
        self.max_retries = config.get("max_retries", 3)
        self.retry_count = 0
        self.ui_elements = {}
    
    def run(self):
        """Run the automation state machine until completion or error."""
        while self.state != AutomationState.COMPLETE and self.state != AutomationState.ERROR:
            self._execute_current_state()
    
    def _execute_current_state(self):
        """Execute the current state and transition to the next state."""
        try:
            if self.state == AutomationState.INITIALIZE:
                self._handle_initialize()
            
            elif self.state == AutomationState.BROWSER_LAUNCH:
                self._handle_browser_launch()
            
            elif self.state == AutomationState.WAIT_FOR_LOGIN:
                self._handle_wait_for_login()
            
            elif self.state == AutomationState.READY_FOR_PROMPT:
                self._handle_ready_for_prompt()
            
            elif self.state == AutomationState.SEND_PROMPT:
                self._handle_send_prompt()
            
            elif self.state == AutomationState.WAIT_FOR_RESPONSE:
                self._handle_wait_for_response()
            
            elif self.state == AutomationState.CAPTURE_RESPONSE:
                self._handle_capture_response()
            
            # Reset retry count on successful state execution
            self.retry_count = 0
            
        except Exception as e:
            self._handle_error(e)
    
    def _handle_initialize(self):
        """Initialize the automation process."""
        logging.info("Initializing automation")
        
        # Load UI elements from config
        for element_name, element_config in self.config.get("ui_elements", {}).items():
            self.ui_elements[element_name] = UIElement(
                name=element_name,
                reference_paths=element_config.get("reference_paths", []),
                region=element_config.get("region"),
                confidence=element_config.get("confidence", 0.8)
            )
        
        self.state = AutomationState.BROWSER_LAUNCH
    
    def _handle_browser_launch(self):
        """Launch the browser and navigate to Claude."""
        logging.info("Launching browser")
        launch_browser(self.config.get("claude_url"))
        self.state = AutomationState.WAIT_FOR_LOGIN
    
    def _handle_wait_for_login(self):
        """Wait for the user to complete login."""
        logging.info("Waiting for login completion")
        
        # Check if already logged in
        logged_in_element = find_element(self.ui_elements["prompt_box"])
        
        if logged_in_element:
            logging.info("Already logged in")
            self.state = AutomationState.READY_FOR_PROMPT
        else:
            input("Please complete login/CAPTCHA and press Enter to continue...")
            self.state = AutomationState.READY_FOR_PROMPT
    
    def _handle_ready_for_prompt(self):
        """Prepare to send the next prompt."""
        if self.current_prompt_index >= len(self.prompts):
            logging.info("All prompts processed")
            self.state = AutomationState.COMPLETE
            return
        
        # Find the prompt box
        prompt_box = find_element(self.ui_elements["prompt_box"])
        if not prompt_box:
            raise Exception("Prompt box not found")
        
        log_with_screenshot("Ready to send prompt", region=prompt_box)
        self.state = AutomationState.SEND_PROMPT
    
    def _handle_send_prompt(self):
        """Send the current prompt to Claude."""
        current_prompt = self.prompts[self.current_prompt_index]
        logging.info(f"Sending prompt: {current_prompt}")
        
        # Find and click the prompt box
        prompt_box = find_element(self.ui_elements["prompt_box"])
        click_element(prompt_box)
        
        # Send the prompt text
        send_text(current_prompt)
        
        # Find and click the send button or press Enter
        send_button = find_element(self.ui_elements["send_button"])
        if send_button:
            click_element(send_button)
        else:
            from pyautogui import press
            press("enter")
        
        log_with_screenshot("Prompt sent")
        self.state = AutomationState.WAIT_FOR_RESPONSE
    
    def _handle_wait_for_response(self):
        """Wait for Claude to finish responding."""
        logging.info("Waiting for Claude's response")
        
        # Set a timeout for response
        timeout = self.config.get("response_timeout", 60)
        start_time = time.time()
        
        # Look for visual indicators that Claude is thinking
        thinking_indicator = find_element(self.ui_elements["thinking_indicator"])
        if thinking_indicator:
            # Wait for thinking indicator to disappear
            while find_element(self.ui_elements["thinking_indicator"]):
                if time.time() - start_time > timeout:
                    raise Exception("Response timeout")
                time.sleep(0.5)
            
            # Extra delay to ensure response is complete
            time.sleep(1)
        else:
            # Wait for visual change in response area
            response_area = self.ui_elements["response_area"].region
            if not wait_for_visual_change(response_area, timeout):
                raise Exception("No response detected")
        
        log_with_screenshot("Response received")
        self.state = AutomationState.CAPTURE_RESPONSE
    
    def _handle_capture_response(self):
        """Capture and process Claude's response."""
        logging.info("Capturing response")
        
        # Extract text from response area
        response_area = self.ui_elements["response_area"].region
        response_text = extract_text_from_region(response_area)
        
        # Store the result
        self.results.append({
            "prompt": self.prompts[self.current_prompt_index],
            "response": response_text
        })
        
        logging.info(f"Response captured: {response_text[:100]}...")
        
        # Move to next prompt
        self.current_prompt_index += 1
        self.state = AutomationState.READY_FOR_PROMPT
    
    def _handle_error(self, error):
        """Handle errors in the automation process."""
        logging.error(f"Error in state {self.state}: {error}")
        log_with_screenshot(f"Error: {error}")
        
        self.retry_count += 1
        if self.retry_count >= self.max_retries:
            logging.error(f"Max retries reached, stopping automation")
            self.state = AutomationState.ERROR