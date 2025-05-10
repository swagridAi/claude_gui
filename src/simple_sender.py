#!/usr/bin/env python3
"""
Simple Claude Prompt Sender

A minimal script that sends prompts to Claude without image recognition.
Launches the browser, waits, types prompts and presses Enter.
Now iterates through all sessions by default.
"""

import subprocess
import time
import argparse
import os
import logging
import yaml
import pyautogui

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_config(config_path="config/user_config.yaml"):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logging.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return {}

def get_chrome_path():
    """Find Chrome browser path based on OS."""
    import platform
    
    system = platform.system()
    
    if system == "Windows":
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe")
        ]
    elif system == "Darwin":  # macOS
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        ]
    else:  # Linux and others
        paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium"
        ]
    
    # Return the first path that exists
    for path in paths:
        if os.path.exists(path):
            return path
    
    return None

def launch_browser(url, profile_dir=None):
    """Launch Chrome browser with specified URL and profile."""
    chrome_path = get_chrome_path()
    if not chrome_path:
        logging.error("Chrome browser not found.")
        return False
    
    if not profile_dir:
        profile_dir = os.path.join(os.path.expanduser("~"), "ClaudeProfile")
    
    # Ensure profile directory exists
    os.makedirs(profile_dir, exist_ok=True)
    
    cmd = [
        chrome_path,
        f"--user-data-dir={profile_dir}",
        "--start-maximized",
        "--disable-extensions",
        url
    ]
    
    try:
        logging.info(f"Launching Chrome: {chrome_path}")
        logging.info(f"Using profile: {profile_dir}")
        logging.info(f"Navigating to: {url}")
        
        process = subprocess.Popen(cmd)
        
        # Check if process started successfully
        if process.poll() is not None:
            logging.error(f"Browser process exited with code {process.returncode}")
            return False
        
        # Wait for browser to initialize
        logging.info("Waiting for browser to initialize (10 seconds)")
        time.sleep(10)
        
        return True
    except Exception as e:
        logging.error(f"Failed to launch browser: {e}")
        return False

def send_prompts(prompts, session_id=None, delay_between_prompts=180):
    """Send each prompt and press Enter."""
    if not prompts:
        logging.error("No prompts to send.")
        return
    
    # Log session information
    if session_id:
        logging.info(f"Running session: {session_id}")
        
    # Wait for page to fully load and for user to handle any login/captcha
    logging.info("Waiting 15 seconds for page to load and for user to handle any login...")
    time.sleep(15)
    
    # Process each prompt
    for i, prompt in enumerate(prompts):
        prompt_num = i + 1
        logging.info(f"Processing prompt {prompt_num}/{len(prompts)}")
        
        try:
            # Clear any current content with Ctrl+A and Delete
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.5)
            pyautogui.press('delete')
            time.sleep(0.5)
            
            # Type the prompt text
            logging.info(f"Typing prompt: {prompt[:50]}..." if len(prompt) > 50 else f"Typing prompt: {prompt}")
            pyautogui.write(prompt)
            time.sleep(1)
            
            # Press Enter to send
            logging.info("Pressing Enter to send prompt")
            pyautogui.press('enter')
            
            # Wait for response (fixed time)
            wait_time = delay_between_prompts
            logging.info(f"Waiting {wait_time} seconds for response...")
            
            # Log progress during the wait
            start_time = time.time()
            while time.time() - start_time < wait_time:
                time.sleep(30)  # Check every 30 seconds
                elapsed = time.time() - start_time
                remaining = wait_time - elapsed
                if remaining > 0:
                    logging.info(f"Still waiting: {int(remaining)} seconds remaining...")
            
            logging.info(f"Completed prompt {prompt_num}/{len(prompts)}")
            
        except Exception as e:
            logging.error(f"Error sending prompt {prompt_num}: {e}")
    
    logging.info("All prompts processed.")

def close_browser():
    """Close Chrome browser."""
    try:
        logging.info("Closing browser...")
        import platform
        
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["pkill", "-f", "chrome"], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
        
        # Wait for browser to close
        time.sleep(2)
        logging.info("Browser closed.")
        
    except Exception as e:
        logging.error(f"Error closing browser: {e}")

def get_all_sessions(config):
    """Get all available sessions from the config."""
    sessions = config.get("sessions", {})
    return list(sessions.keys())

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Simple Claude Prompt Sender")
    parser.add_argument("--config", help="Path to config file", default="config/user_config.yaml")
    parser.add_argument("--session", help="Specific session to run (default: run all)", default=None)
    parser.add_argument("--run-one", action="store_true", help="Run only the specified session, not all")
    parser.add_argument("--delay", type=int, help="Delay between prompts in seconds", default=180)
    parser.add_argument("--session-delay", type=int, help="Delay between sessions in seconds", default=5)
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Determine which sessions to run
    sessions_to_run = []
    
    if args.session and args.run_one:
        # Run only the specified session
        sessions_to_run.append(args.session)
    elif args.session:
        # Use specified session as the first one, then run all others
        sessions = get_all_sessions(config)
        if args.session in sessions:
            # Move the specified session to the front
            sessions.remove(args.session)
            sessions_to_run = [args.session] + sessions
        else:
            # If specified session doesn't exist, run all
            sessions_to_run = sessions
    else:
        # Run all sessions by default
        sessions_to_run = get_all_sessions(config)
    
    if not sessions_to_run:
        # If no sessions defined, use default global prompts
        logging.info("No sessions defined in config. Using global prompts.")
        url = config.get("claude_url", "https://claude.ai")
        prompts = config.get("prompts", [])
        profile_dir = config.get("browser_profile")
        
        # Launch browser
        if not launch_browser(url, profile_dir):
            logging.error("Failed to launch browser. Exiting.")
            return
        
        try:
            # Send prompts
            send_prompts(prompts, "default", args.delay)
        finally:
            # Close browser
            close_browser()
        
        return
    
    # Run each session
    for i, session_id in enumerate(sessions_to_run):
        logging.info(f"Starting session {i+1}/{len(sessions_to_run)}: {session_id}")
        
        # Get session config
        session_config = config.get("sessions", {}).get(session_id, {})
        session_url = session_config.get("claude_url", config.get("claude_url", "https://claude.ai"))
        session_prompts = session_config.get("prompts", [])
        profile_dir = config.get("browser_profile")
        
        if not session_prompts:
            logging.warning(f"No prompts found for session '{session_id}'. Skipping.")
            continue
        
        # Launch browser
        if not launch_browser(session_url, profile_dir):
            logging.error(f"Failed to launch browser for session '{session_id}'. Skipping.")
            continue
        
        try:
            # Send prompts
            send_prompts(session_prompts, session_id, args.delay)
        except Exception as e:
            logging.error(f"Error in session '{session_id}': {e}")
        finally:
            # Close browser
            close_browser()
        
        # Wait between sessions if there are more to process
        if i < len(sessions_to_run) - 1:
            delay = args.session_delay
            logging.info(f"Waiting {delay} seconds before next session...")
            time.sleep(delay)
    
    logging.info(f"All {len(sessions_to_run)} sessions completed.")

if __name__ == "__main__":
    main()