#!/usr/bin/env python3
"""
SRM Academia Scraper with Session Management
Based on the working standalone code
"""

import os
import sys
import json
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException


def is_serverless_env():
    """Detect if running in serverless environment"""
    # Check for serverless indicators
    return (
        os.environ.get('RENDER') is not None or  # Render.com
        os.environ.get('VERCEL') is not None or  # Vercel
        os.environ.get('LAMBDA_TASK_ROOT') is not None or  # AWS Lambda
        os.environ.get('DYNO') is not None  # Heroku
    )


class SRMAcademiaScraperSelenium:
    def __init__(self, headless=False, use_session=True, user_email=None):
        """
        Initialize the scraper with Selenium and per-user session management
        
        Args:
            headless: Run Chrome in headless mode
            use_session: Enable session persistence
            user_email: User email for per-user session management (required if use_session=True)
        """
        self.headless = headless
        self.user_email = user_email
        self.session_timeout = 30 * 24 * 60 * 60  # 30 days in seconds
        
        # Detect serverless environment
        self.is_serverless = is_serverless_env()
        
        if self.is_serverless:
            # In serverless, disable session persistence (it causes conflicts)
            use_session = False
            print("[SERVERLESS] Detected serverless environment - disabling session persistence", file=sys.stderr)
        
        self.use_session = use_session
        
        # Create per-user session files if user_email is provided
        if use_session and user_email:
            # Create a safe filename from email using hash
            email_hash = hashlib.md5(user_email.encode()).hexdigest()[:16]
            
            # Add unique request ID to avoid conflicts in serverless
            request_id = str(uuid.uuid4())[:8]  # Short UUID for uniqueness
            self.request_id = request_id  # Save for cleanup later
            
            self.user_session_id = f"{user_email.split('@')[0]}_{email_hash}_{request_id}"
            self.session_file = f"session_data_{self.user_session_id}.json"
            print(f"[SESSION] Using unique session for: {user_email} (ID: {request_id})", file=sys.stderr)
        else:
            # Fallback to global session (backward compatibility)
            self.user_session_id = "global"
            self.session_file = "session_data.json"
            self.request_id = None
            if use_session:
                print("[SESSION] Warning: No user_email provided, using global session", file=sys.stderr)
        
        # Setup Chrome options
        chrome_options = Options()
        # Use more stable headless mode for serverless
        if self.is_serverless:
            chrome_options.add_argument("--headless=new")  # More stable in serverless
        elif headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Performance optimizations
        chrome_options.add_argument("--disable-images")  # Don't load images
        chrome_options.add_argument("--disable-plugins")  # Disable plugins
        chrome_options.add_argument("--disable-extensions")  # Disable extensions
        chrome_options.add_argument("--disable-gpu")  # Disable GPU
        chrome_options.add_argument("--disable-web-security")  # Disable web security checks
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")  # Disable compositor
        chrome_options.add_argument("--disable-background-timer-throttling")  # Disable timer throttling
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")  # Disable backgrounding
        chrome_options.add_argument("--disable-renderer-backgrounding")  # Disable renderer backgrounding
        
        # Additional safe performance optimizations
        chrome_options.add_argument("--disable-default-apps")  # Disable default apps
        chrome_options.add_argument("--disable-sync")  # Disable sync
        chrome_options.add_argument("--disable-translate")  # Disable translate
        chrome_options.add_argument("--disable-logging")  # Disable logging
        chrome_options.add_argument("--disable-notifications")  # Disable notifications
        chrome_options.add_argument("--disable-popup-blocking")  # Disable popup blocking
        chrome_options.add_argument("--disable-prompt-on-repost")  # Disable repost prompts
        chrome_options.add_argument("--disable-hang-monitor")  # Disable hang monitor
        chrome_options.add_argument("--disable-client-side-phishing-detection")  # Disable phishing detection
        chrome_options.add_argument("--disable-component-update")  # Disable component updates
        chrome_options.add_argument("--disable-domain-reliability")  # Disable domain reliability
        chrome_options.add_argument("--disable-features=TranslateUI")  # Disable translate UI
        chrome_options.add_argument("--disable-ipc-flooding-protection")  # Disable IPC flooding protection
        chrome_options.add_argument("--aggressive-cache-discard")  # Aggressive cache discard
        chrome_options.add_argument("--memory-pressure-off")  # Turn off memory pressure
        
        # Add session persistence if enabled (per-user profiles)
        if use_session:
            # Create a per-user persistent Chrome profile directory
            if user_email:
                # Add timestamp to ensure uniqueness per request
                profile_dir = os.path.join(os.getcwd(), "chrome_sessions", f"{self.user_session_id}_{int(time.time())}")
            else:
                # Fallback to global profile
                profile_dir = os.path.join(os.getcwd(), "chrome_session_profile")
            
            if not os.path.exists(profile_dir):
                os.makedirs(profile_dir, exist_ok=True)
                print(f"[SESSION] Created profile directory: {profile_dir}", file=sys.stderr)
            
            chrome_options.add_argument(f"--user-data-dir={profile_dir}")
            self.profile_dir = profile_dir  # Save for cleanup
            print(f"[SESSION] Using Chrome profile: {profile_dir}", file=sys.stderr)
        else:
            self.profile_dir = None
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)
            print("[OK] Selenium WebDriver initialized with session management", file=sys.stderr)
        except Exception as e:
            print(f"[FAIL] Could not initialize WebDriver: {e}", file=sys.stderr)
            print("[INFO] Make sure you have Chrome and chromedriver installed", file=sys.stderr)
            raise
    
    def is_session_valid(self):
        """Check if the current session is still valid by actually testing it"""
        print(f"[SESSION VALID CHECK] Starting - use_session: {self.use_session}, session_file: {self.session_file}", file=sys.stderr)
        if not self.use_session:
            print("[SESSION VALID CHECK] Session disabled (serverless mode) - returning False", file=sys.stderr)
            return False
        
        if not os.path.exists(self.session_file):
            print(f"[SESSION VALID CHECK] No session file found: {self.session_file}", file=sys.stderr)
            return False
        
        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check if session has expired (use timestamp field)
            if 'timestamp' in session_data:
                session_time = datetime.fromisoformat(session_data['timestamp'])
                if datetime.now() - session_time > timedelta(seconds=self.session_timeout):
                    print("[SESSION] Session expired (30 days)", file=sys.stderr)
                    return False
            
            # Actually test the session by trying to access a protected page
            try:
                print("[SESSION] Testing session validity...", file=sys.stderr)
                # ✅ FIX: Use a valid page that actually exists (Dashboard doesn't exist)
                # Use Attendance page as it's a valid protected page
                self.driver.get("https://academia.srmist.edu.in/#Page:My_Attendance")
                time.sleep(1)  # Optimized - reduced from 3s to 1s
                
                # Check if we're redirected to login page
                if "Login" in self.driver.title or "signinFrame" in self.driver.page_source[:1000]:
                    print("[SESSION] Session invalid - redirected to login page", file=sys.stderr)
                    return False
                else:
                    # Additional check: verify we're on a valid internal page
                    current_url = self.driver.current_url
                    if "#Page:" in current_url:
                        print("[SESSION] Session valid - can access protected pages", file=sys.stderr)
                        return True
                    else:
                        print("[SESSION] Session invalid - not on a valid portal page", file=sys.stderr)
                        return False
                    
            except Exception as e:
                print(f"[SESSION] Error testing session: {e}", file=sys.stderr)
                return False
                
        except Exception as e:
            print(f"[SESSION] Error reading session file: {e}", file=sys.stderr)
            return False
    
    def save_session(self, email):
        """Save session data to file"""
        if not self.use_session:
            return
        
        try:
            session_data = {
                'email': email,
                'timestamp': datetime.now().isoformat(),
                'status': 'logged_in'
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f)
            
            print(f"[SESSION] Session saved for {email}", file=sys.stderr)
        except Exception as e:
            print(f"[SESSION] Error saving session: {e}", file=sys.stderr)
    
    def is_logged_in(self):
        """Check if browser is currently on a logged-in page (real-time state check)"""
        try:
            current_url = self.driver.current_url
            title = self.driver.title
            
            # Check if we're on welcome or any internal page
            if "WELCOME" in title:
                print("[BROWSER STATE] Already logged in - on WELCOME page", file=sys.stderr)
                return True
            
            # Check if URL shows we're inside the portal (any internal page)
            if "academia.srmist.edu.in/#Page:" in current_url:
                print(f"[BROWSER STATE] Already logged in - on internal page: {current_url}", file=sys.stderr)
                return True
            
            # Check if title explicitly says Login
            if "Login" in title:
                print("[BROWSER STATE] On login page - title contains 'Login'", file=sys.stderr)
                return False
            
            # If on base academia URL without "Login" in title, check for login iframe
            if "academia.srmist.edu.in" in current_url:
                try:
                    # Try to find login iframe - if it exists, we're on login page
                    self.driver.find_element(By.ID, "signinFrame")
                    print("[BROWSER STATE] Found login iframe - on login page", file=sys.stderr)
                    return False  # Found iframe = login page
                except:
                    # No login iframe found = already logged in
                    print("[BROWSER STATE] No login iframe found - already logged in", file=sys.stderr)
                    return True
            
            print(f"[BROWSER STATE] Unknown state - URL: {current_url}, Title: {title}", file=sys.stderr)
            return False
            
        except Exception as e:
            print(f"[BROWSER STATE] Error checking login state: {e}", file=sys.stderr)
            return False
    
    def login(self, email, password):
        """Login to the academia portal using Selenium with session management"""
        try:
            print(f"\n=== LOGIN WITH SELENIUM (Session: {self.use_session}) ===", file=sys.stderr)
            print(f"[LOGIN DEBUG] Email: {email}", file=sys.stderr)
            print(f"[LOGIN DEBUG] Password provided: {password is not None}", file=sys.stderr)
            print(f"[LOGIN DEBUG] Password length: {len(password) if password else 0}", file=sys.stderr)
            
            # Don't skip login - always attempt it when this method is called
            # The session validation should be done before calling this method
            
            print(f"[STEP 1] Loading portal page...", file=sys.stderr)
            self.driver.get("https://academia.srmist.edu.in/")
            time.sleep(0.5)  # Optimized for speed
            
            # Verify window is still open after page load
            try:
                _ = self.driver.current_url
                print(f"[OK] Page loaded: {self.driver.title}", file=sys.stderr)
            except Exception as e:
                print(f"[ERROR] Browser window closed unexpectedly: {e}", file=sys.stderr)
                return False
            
            # Switch to the iframe - simplified approach for stability
            print("[STEP 2] Switching to login iframe...", file=sys.stderr)
            
            try:
                # Verify window is still open before finding iframe
                try:
                    _ = self.driver.current_url
                except WebDriverException as e:
                    print(f"[ERROR] Browser window detached before iframe detection: {e}", file=sys.stderr)
                    return False
                
                # Find iframe using ID (simplest and most reliable)
                try:
                    iframe = self.wait.until(
                        EC.presence_of_element_located((By.ID, "signinFrame"))
                    )
                    self.driver.switch_to.frame(iframe)
                    print("[OK] Switched to iframe", file=sys.stderr)
                except TimeoutException:
                    # Fallback to any iframe
                    print("[RETRY] Trying alternative iframe selector...", file=sys.stderr)
                    try:
                        iframe = self.driver.find_element(By.TAG_NAME, "iframe")
                        self.driver.switch_to.frame(iframe)
                        print("[OK] Switched to iframe (fallback)", file=sys.stderr)
                    except WebDriverException as e:
                        print(f"[ERROR] Browser crashed in fallback: {e}", file=sys.stderr)
                        return False
                except WebDriverException as e:
                    # Check if browser crashed
                    if "target frame detached" in str(e).lower() or "disconnected" in str(e).lower():
                        print("[ERROR] Browser window closed/crashed during iframe detection", file=sys.stderr)
                        return False
                    raise  # Re-raise other WebDriverExceptions
                    
            except WebDriverException as e:
                # Handle browser crash errors
                if "target frame detached" in str(e).lower() or "disconnected" in str(e).lower():
                    print("[ERROR] Browser crashed or was closed unexpectedly", file=sys.stderr)
                    return False
                print(f"[ERROR] WebDriver error: {e}", file=sys.stderr)
                return False
            except Exception as e:
                print(f"[ERROR] Could not find or switch to iframe: {e}", file=sys.stderr)
                return False
            
            # Find and fill email field
            print("[STEP 3] Entering email...", file=sys.stderr)
            try:
                email_field = self.wait.until(
                    EC.presence_of_element_located((By.ID, "login_id"))
                )
                email_field.clear()
                email_field.send_keys(email)
                print(f"[OK] Email entered: {email}", file=sys.stderr)
            except (TimeoutException, WebDriverException) as e:
                if "target frame detached" in str(e).lower() or "disconnected" in str(e).lower():
                    print("[ERROR] Browser crashed during email entry", file=sys.stderr)
                    return False
                print(f"[ERROR] Could not find email field - Exception: {type(e).__name__}: {str(e)}", file=sys.stderr)
                try:
                    current_url = self.driver.current_url
                    current_title = self.driver.title
                    print(f"[ERROR] Page state when email field failed - URL: {current_url}, Title: {current_title}", file=sys.stderr)
                except:
                    pass
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                return False
            
            # Click Next button to reveal password field
            print("[STEP 4] Clicking Next button...", file=sys.stderr)
            try:
                next_button = self.driver.find_element(By.ID, "nextbtn")
                next_button.click()
                print("[OK] Next button clicked", file=sys.stderr)
                # ✅ OPTIMIZED: No fixed sleep - smart wait below will return as soon as password field is ready
            except (NoSuchElementException, WebDriverException) as e:
                if "target frame detached" in str(e).lower() or "disconnected" in str(e).lower():
                    print("[ERROR] Browser crashed during next button click", file=sys.stderr)
                    return False
                print(f"[ERROR] Could not find Next button - Exception: {type(e).__name__}: {str(e)}", file=sys.stderr)
                try:
                    current_url = self.driver.current_url
                    current_title = self.driver.title
                    print(f"[ERROR] Page state when next button failed - URL: {current_url}, Title: {current_title}", file=sys.stderr)
                except:
                    pass
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                return False
            
            # ✅ OPTIMIZED: Find and fill password field (smart wait - returns as soon as ready, often faster than fixed sleep)
            print("[STEP 5] Entering password...", file=sys.stderr)
            try:
                # Use element_to_be_clickable - ensures field is ready and interactable, often faster than fixed sleep
                password_field = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "password"))
                )
                password_field.clear()
                password_field.send_keys(password)
                print("[OK] Password entered", file=sys.stderr)
            except (TimeoutException, WebDriverException) as e:
                if "target frame detached" in str(e).lower() or "disconnected" in str(e).lower():
                    print("[ERROR] Browser crashed during password entry", file=sys.stderr)
                    return False
                print(f"[ERROR] Could not find password field - Exception: {type(e).__name__}: {str(e)}", file=sys.stderr)
                try:
                    current_url = self.driver.current_url
                    current_title = self.driver.title
                    print(f"[ERROR] Page state when password field failed - URL: {current_url}, Title: {current_title}", file=sys.stderr)
                except:
                    pass
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                return False
            
            # Click login button (same as next button)
            print("[STEP 6] Clicking login button...", file=sys.stderr)
            try:
                login_button = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "nextbtn"))
                )
                login_button.click()
                print("[OK] Login button clicked", file=sys.stderr)
            except (TimeoutException, WebDriverException) as e:
                if "target frame detached" in str(e).lower() or "disconnected" in str(e).lower():
                    print("[ERROR] Browser crashed during login button click", file=sys.stderr)
                    return False
                print(f"[ERROR] Could not find login button - Exception: {type(e).__name__}: {str(e)}", file=sys.stderr)
                try:
                    current_url = self.driver.current_url
                    current_title = self.driver.title
                    print(f"[ERROR] Page state when login button failed - URL: {current_url}, Title: {current_title}", file=sys.stderr)
                except:
                    pass
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                return False
            
            # ✅ HYBRID METHOD: Wait for login to complete (smart wait - returns as soon as done)
            print("[STEP 7] Waiting for login to complete (smart wait)...", file=sys.stderr)
            
            try:
                # STRATEGY 1: Wait for iframe to become stale/closed = login processed
                # This is faster than fixed sleep and more reliable
                
                def login_iframe_disappeared(driver):
                    """Check if login iframe has disappeared (login processed)"""
                    try:
                        driver.switch_to.default_content()  # Switch to main frame
                        # Try to find iframe - if it's gone, login processed
                        iframe_elements = driver.find_elements(By.ID, "signinFrame")
                        if len(iframe_elements) == 0:
                            return True  # Iframe gone = login completed
                        return False
                    except Exception:
                        # Iframe detached/stale = login processed
                        return True
                
                # Wait up to 10 seconds for login to complete (typically 1-3 seconds)
                try:
                    WebDriverWait(self.driver, 10).until(login_iframe_disappeared)
                    print("[OK] Login iframe disappeared - login processing complete", file=sys.stderr)
                except TimeoutException:
                    # Backup: Check if we're still in iframe after timeout
                    try:
                        self.driver.switch_to.default_content()
                        # Give it one more chance - check page state
                        time.sleep(0.5)
                    except:
                        pass
                    print("[WARN] Iframe check timeout - proceeding with verification", file=sys.stderr)
                
                # Ensure we're in default content
                self.driver.switch_to.default_content()
                
                # ✅ STEP 7.1: Quick verification - check page state WITHOUT navigating (saves time)
                print("[STEP 7.1] Verifying login state (current page check)...", file=sys.stderr)
                time.sleep(0.5)  # Brief wait for page state to settle
                
                current_url = self.driver.current_url
                current_title = self.driver.title
                page_source_sample = self.driver.page_source[:1000] if len(self.driver.page_source) > 0 else ""
                
                print(f"[LOGIN VERIFY] Current URL: {current_url}", file=sys.stderr)
                print(f"[LOGIN VERIFY] Current title: {current_title}", file=sys.stderr)
                print(f"[LOGIN VERIFY] Contains 'Login' in title: {'Login' in current_title}", file=sys.stderr)
                print(f"[LOGIN VERIFY] Contains 'signinFrame' in source: {'signinFrame' in page_source_sample}", file=sys.stderr)
                
                # ✅ CRITICAL: Must NOT be on login page
                if "Login" in current_title:
                    print("[ERROR] Login failed - still on login page", file=sys.stderr)
                    # ✅ FIX: Instead of Dashboard (which doesn't exist), verify by checking if we can access any valid page
                    # Try accessing a known valid page as fallback verification
                    print("[RETRY] Attempting to verify login by accessing Attendance page...", file=sys.stderr)
                    attendance_url = "https://academia.srmist.edu.in/#Page:My_Attendance"
                    self.driver.get(attendance_url)
                    time.sleep(2)
                    final_url = self.driver.current_url
                    final_title = self.driver.title
                    final_source_check = self.driver.page_source[:1000] if len(self.driver.page_source) > 0 else ""
                    
                    print(f"[LOGIN VERIFY] After Attendance page navigation - URL: {final_url}", file=sys.stderr)
                    print(f"[LOGIN VERIFY] After Attendance page navigation - Title: {final_title}", file=sys.stderr)
                    
                    # Check if we're still on login page or redirected to login
                    if "Login" in final_title or "signinFrame" in final_source_check:
                        print("[ERROR] Login failed - redirected to login page when accessing protected page", file=sys.stderr)
                        print(f"[ERROR] Title: {final_title}, URL: {final_url}", file=sys.stderr)
                        return False
                    
                    # Verify we're actually on a valid portal page
                    if "#Page:" not in final_url:
                        print("[ERROR] Login failed - not on a valid portal page", file=sys.stderr)
                        print(f"[ERROR] Title: {final_title}, URL: {final_url}", file=sys.stderr)
                        return False
                    
                    print("[OK] Login verified - successfully accessed protected page", file=sys.stderr)
                
                if "signinFrame" in page_source_sample:
                    print("[ERROR] Login failed - login frame still present", file=sys.stderr)
                    return False
                
                print(f"[OK] Login verified! Current page: {current_title}", file=sys.stderr)
                
                # Save session if enabled
                if self.use_session:
                    self.save_session(email)
                
                return True
                
            
            except (TimeoutException, WebDriverException) as e:
                # Detailed error logging
                try:
                    error_url = self.driver.current_url
                    error_title = self.driver.title
                    error_source_snippet = self.driver.page_source[:1000] if len(self.driver.page_source) > 0 else ""
                    print(f"[ERROR] Login timeout/error - Current URL: {error_url}", file=sys.stderr)
                    print(f"[ERROR] Login timeout/error - Current Title: {error_title}", file=sys.stderr)
                    print(f"[ERROR] Login timeout/error - Page contains 'signinFrame': {'signinFrame' in error_source_snippet}", file=sys.stderr)
                    print(f"[ERROR] Login timeout/error - Page contains 'Dashboard': {'Dashboard' in error_source_snippet}", file=sys.stderr)
                    print(f"[ERROR] Login timeout/error - Page source snippet (first 500 chars): {error_source_snippet[:500]}", file=sys.stderr)
                except Exception as debug_e:
                    print(f"[ERROR] Could not get error state: {debug_e}", file=sys.stderr)
                
                if "target frame detached" in str(e).lower() or "disconnected" in str(e).lower():
                    print("[ERROR] Browser crashed while waiting for login completion", file=sys.stderr)
                    return False
                print(f"[ERROR] Login failed - timeout/error during verification. Exception: {type(e).__name__}: {str(e)}", file=sys.stderr)
                return False
                
        except Exception as e:
            print(f"[ERROR] Login failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return False
    
    def get_calendar_data(self):
        """Get calendar data from the academic planner page"""
        try:
            print("\n=== GETTING CALENDAR DATA ===", file=sys.stderr)
            
            # Navigate to academic planner
            planner_url = "https://academia.srmist.edu.in/#Page:Academic_Planner_2025_26_ODD"
            print(f"[STEP 1] Navigating to: {planner_url}", file=sys.stderr)
            
            self.driver.get(planner_url)
            
            # ✅ CRITICAL: Early login page detection (before waiting for content)
            print("[STEP 2] Checking for login page (early exit optimization)...", file=sys.stderr)
            time.sleep(0.5)  # Small wait for page to start loading
            
            current_title = self.driver.title
            current_url = self.driver.current_url
            page_source_snippet = self.driver.page_source[:500]  # Small sample for quick check
            
            if "Login" in current_title or "signinFrame" in page_source_snippet:
                print("[ERROR] Redirected to login page - session expired", file=sys.stderr)
                print(f"[ERROR] Current title: {current_title}", file=sys.stderr)
                print(f"[ERROR] Current URL: {current_url}", file=sys.stderr)
                return None
            
            print("[OK] Not on login page, proceeding with calendar extraction", file=sys.stderr)
            
            # ✅ CRITICAL: Wait for calendar table WITH ROWS (not just table presence)
            print("[STEP 3] Waiting for calendar table with rows to load...", file=sys.stderr)
            
            def calendar_table_has_rows(driver):
                """Custom condition: Check if table exists AND has rows"""
                try:
                    tables = driver.find_elements(By.TAG_NAME, 'table')
                    print(f"[DEBUG] Found {len(tables)} table elements on page", file=sys.stderr)
                    
                    if len(tables) == 0:
                        return False
                    
                    # Check if any table has rows (tr elements)
                    for idx, table in enumerate(tables):
                        rows = table.find_elements(By.TAG_NAME, 'tr')
                        print(f"[DEBUG] Table {idx+1}: Found {len(rows)} rows", file=sys.stderr)
                        
                        if len(rows) > 0:
                            # Check if rows have cells
                            cells_count = 0
                            for row in rows[:3]:  # Check first 3 rows
                                cells = row.find_elements(By.TAG_NAME, 'td') + row.find_elements(By.TAG_NAME, 'th')
                                cells_count += len(cells)
                            
                            print(f"[DEBUG] Table {idx+1}: First 3 rows have {cells_count} cells total", file=sys.stderr)
                            
                            if cells_count > 0:
                                print(f"[OK] Calendar table {idx+1} has {len(rows)} rows with data", file=sys.stderr)
                                return True
                    
                    return False
                except Exception as e:
                    print(f"[DEBUG] Error checking table rows: {e}", file=sys.stderr)
                    return False
            
            table_with_rows_found = False
            try:
                print("[DEBUG] Waiting up to 15 seconds for calendar table with rows...", file=sys.stderr)
                WebDriverWait(self.driver, 15).until(calendar_table_has_rows)
                table_with_rows_found = True
                print("[OK] Calendar table with rows found!", file=sys.stderr)
            except TimeoutException:
                print("[WARN] Timeout waiting for table with rows after 15s", file=sys.stderr)
                # Debug: Check what we actually have
                try:
                    tables = self.driver.find_elements(By.TAG_NAME, 'table')
                    print(f"[DEBUG] After timeout: Found {len(tables)} tables", file=sys.stderr)
                    for idx, table in enumerate(tables):
                        rows = table.find_elements(By.TAG_NAME, 'tr')
                        print(f"[DEBUG] Table {idx+1} has {len(rows)} rows", file=sys.stderr)
                        if len(rows) > 0:
                            row_text_sample = rows[0].text[:100]
                            print(f"[DEBUG] Table {idx+1} first row text sample: {row_text_sample}", file=sys.stderr)
                except Exception as e:
                    print(f"[DEBUG] Error inspecting tables after timeout: {e}", file=sys.stderr)
            
            # Re-check for login page
            if not table_with_rows_found:
                if "Login" in self.driver.title or "signinFrame" in self.driver.page_source[:500]:
                    print("[ERROR] Login page detected after wait - session expired during navigation", file=sys.stderr)
                    return None
                print("[WARN] Table with rows not found, but continuing...", file=sys.stderr)
            
            # ✅ CRITICAL: Extra wait for JavaScript rendering (calendar needs time to fully render all content)
            print("[STEP 4] Waiting for JavaScript to fully render calendar content...", file=sys.stderr)
            time.sleep(3)  # Give additional time for full calendar rendering
            print("[OK] Finished waiting for JS rendering", file=sys.stderr)
            
            # Final login page check before returning
            final_title = self.driver.title
            if "Login" in final_title:
                print("[ERROR] Login page detected at final check - session expired", file=sys.stderr)
                return None
            
            # Double-check for login page in page source
            page_source_sample = self.driver.page_source[:1000]  # Check first 1000 chars for speed
            if "signinFrame" in page_source_sample:
                print("[WARNING] Login iframe detected in page source - session expired", file=sys.stderr)
                return None
            
            print(f"[OK] Current URL: {self.driver.current_url}", file=sys.stderr)
            print(f"[OK] Page title: {final_title}", file=sys.stderr)
            print("[OK] Calendar page loaded successfully", file=sys.stderr)
            
            # Get page source AFTER dynamic content loads
            page_source = self.driver.page_source
            
            if not page_source:
                print("[ERROR] No page source received", file=sys.stderr)
                return None
            
            print(f"[OK] Page source received ({len(page_source)} characters)", file=sys.stderr)
            
            # Final validation - check if page source is too small (likely login page)
            if len(page_source) < 10000:  # Real calendar pages should be much larger
                print(f"[WARN] Page source is very small ({len(page_source)} chars) - might be login page", file=sys.stderr)
                if "Login" in page_source or "signinFrame" in page_source:
                    print("[ERROR] Confirmed: This is a login page, not calendar", file=sys.stderr)
                    return None
            
            # ✅ COMPREHENSIVE DEBUG: Check HTML structure before returning
            print("[DEBUG] === CALENDAR HTML STRUCTURE ANALYSIS ===", file=sys.stderr)
            print(f"[DEBUG] Total HTML length: {len(page_source)} characters", file=sys.stderr)
            
            # Count tables in HTML
            table_count = page_source.lower().count('<table')
            print(f"[DEBUG] Number of '<table' tags found: {table_count}", file=sys.stderr)
            
            # Count rows in HTML
            tr_count = page_source.lower().count('<tr')
            print(f"[DEBUG] Number of '<tr' tags found: {tr_count}", file=sys.stderr)
            
            # Count cells in HTML
            td_count = page_source.lower().count('<td')
            th_count = page_source.lower().count('<th')
            print(f"[DEBUG] Number of '<td' tags: {td_count}, '<th' tags: {th_count}", file=sys.stderr)
            
            # Check for expected calendar markers
            has_jul = "Jul" in page_source or "Jul '25" in page_source
            has_aug = "Aug" in page_source or "Aug '25" in page_source
            has_2025 = "2025" in page_source or "'25" in page_source
            print(f"[DEBUG] Contains 'Jul': {has_jul}, 'Aug': {has_aug}, '2025/'25': {has_2025}", file=sys.stderr)
            
            # Sample HTML structure (first 500 chars)
            print(f"[DEBUG] First 500 characters of HTML: {page_source[:500]}", file=sys.stderr)
            
            # Sample table structure if found
            if '<table' in page_source.lower():
                table_start = page_source.lower().find('<table')
                table_sample = page_source[table_start:table_start+1000]
                print(f"[DEBUG] Sample table HTML (first 1000 chars): {table_sample}", file=sys.stderr)
            
            # Check if we got the right content
            if "Jul '25" in page_source and "Aug '25" in page_source:
                print("[OK] Calendar content markers detected in page source", file=sys.stderr)
                print("[DEBUG] === CALENDAR HTML STRUCTURE ANALYSIS COMPLETE ===", file=sys.stderr)
                return page_source
            else:
                print("[WARNING] Calendar content markers not detected in page source", file=sys.stderr)
                print(f"[DEBUG] Page source contains 'Jul': {has_jul}", file=sys.stderr)
                print(f"[DEBUG] Page source contains 'Aug': {has_aug}", file=sys.stderr)
                print(f"[DEBUG] Page source contains 'table': {'table' in page_source.lower()}", file=sys.stderr)
                print("[DEBUG] === CALENDAR HTML STRUCTURE ANALYSIS COMPLETE ===", file=sys.stderr)
                # Return anyway, let the parser handle it (might be different year/format)
                return page_source
            
        except Exception as e:
            print(f"[ERROR] Failed to get calendar data: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return None
    
    def cleanup_profile(self):
        """Safely cleanup Chrome profile directory and processes"""
        try:
            # Kill any orphaned Chrome processes for this profile
            if hasattr(self, 'profile_dir') and self.profile_dir:
                import subprocess
                import shutil
                import platform
                
                # Kill Chrome processes on Windows
                if platform.system() == "Windows":
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/IM", "chrome.exe", "/T"],
                            check=False,
                            capture_output=True,
                            timeout=5
                        )
                    except Exception:
                        pass
                
                # Cleanup directory
                if os.path.exists(self.profile_dir):
                    try:
                        # Wait a bit for Chrome to release file locks
                        time.sleep(0.3)  # Optimized - reduced from 1s to 0.3s
                        shutil.rmtree(self.profile_dir, ignore_errors=True)
                        print(f"[CLEANUP] Removed profile directory: {self.profile_dir}", file=sys.stderr)
                    except Exception as e:
                        print(f"[CLEANUP] Could not remove profile: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[CLEANUP] Error in cleanup: {e}", file=sys.stderr)
    
    def close(self):
        """Close the browser and cleanup"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
                print("[OK] Browser closed", file=sys.stderr)
            
            # Cleanup profile directory
            self.cleanup_profile()
        except Exception as e:
            print(f"[ERROR] Error closing browser: {e}", file=sys.stderr)

def main():
    """Test function"""
    scraper = SRMAcademiaScraperSelenium(headless=False, use_session=True)
    
    try:
        email = "gr8790@srmist.edu.in"
        password = "h!Grizi34"
        
        if scraper.login(email, password):
            html_content = scraper.get_calendar_data()
            if html_content:
                print(f"Got calendar HTML content: {len(html_content)} characters", file=sys.stderr)
            else:
                print("Failed to get calendar data", file=sys.stderr)
        else:
            print("Login failed", file=sys.stderr)
    
    finally:
        scraper.close()

if __name__ == "__main__":
    main()

