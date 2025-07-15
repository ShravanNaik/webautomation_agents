
import sys
import importlib
importlib.import_module('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')# app.py - Complete Popup & CAPTCHA Handling Automation
import streamlit as st
import asyncio
import os
import threading
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from playwright.async_api import async_playwright
import logging
import time
import random

# Load environment
load_dotenv()

# Configure Streamlit
st.set_page_config(
    page_title="🛡️ Agentic Smart Automation",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #FF6B35;
        font-size: 2.5rem;
        margin-bottom: 2rem;
    }
    .smart-badge {
        background: linear-gradient(90deg, #667eea, #764ba2);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin: 0.5rem;
    }
    .popup-badge {
        background: linear-gradient(90deg, #28a745, #20c997);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

class CompleteSmartAutomation:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            st.error("❌ Please set OPENAI_API_KEY in your environment")
            return
            
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.5,
            openai_api_key=self.api_key
        )
        
        # Create specialized agents
        self.popup_agent = Agent(
            role="Popup & Modal Handler",
            goal="Detect and automatically close all types of popups, modals, and overlays",
            backstory="You are an expert at identifying and dismissing popups, cookie banners, newsletter signups, privacy notices, and any overlay that blocks user interaction.",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )
        
        self.captcha_agent = Agent(
            role="CAPTCHA & Bot Detection Specialist", 
            goal="Handle all forms of bot detection and verification systems",
            backstory="You specialize in solving CAPTCHAs, handling 'I'm not a robot' challenges, and bypassing bot detection systems.",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

    def run_complete_automation(self, user_request):
        """Complete automation with popup and CAPTCHA handling"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(self.execute_complete_automation(user_request))
            loop.close()
            return results
        except Exception as e:
            return [f"❌ Critical Error: {str(e)}"]

    async def human_delay(self, min_ms=300, max_ms=1000):
        """Human-like delay"""
        delay = random.uniform(min_ms/1000, max_ms/1000)
        await asyncio.sleep(delay)
        return delay

    async def detect_and_close_popups(self, page):
        """Detect and close all types of popups"""
        popups_closed = []
        
        try:
            # Common popup patterns
            popup_patterns = [
                # Cookie banners
                {'selectors': ['button:has-text("Accept")', 'button:has-text("Accept all")', 'button:has-text("I agree")', '#L2AGLb'], 'type': 'Cookie banner'},
                {'selectors': ['button:has-text("Allow all")', 'button:has-text("Accept cookies")', '[data-testid="accept-all"]'], 'type': 'Cookie consent'},
                
                # Privacy notices
                {'selectors': ['button:has-text("OK")', 'button:has-text("Got it")', 'button:has-text("Understand")'], 'type': 'Privacy notice'},
                {'selectors': ['[aria-label="Close"]', 'button[aria-label="Close"]', '.close', '[data-dismiss="modal"]'], 'type': 'Close button'},
                
                # Newsletter/signup modals
                {'selectors': ['button:has-text("No thanks")', 'button:has-text("Skip")', 'button:has-text("Maybe later")'], 'type': 'Newsletter popup'},
                {'selectors': ['button:has-text("Continue without")', 'button:has-text("Not now")'], 'type': 'Signup modal'},
                
                # Location/notification requests
                {'selectors': ['button:has-text("Block")', 'button:has-text("Not now")', 'button:has-text("Deny")'], 'type': 'Permission request'},
                
                # Generic overlay closers
                {'selectors': ['.modal-close', '.popup-close', '.overlay-close', 'button.close'], 'type': 'Generic overlay'},
                {'selectors': ['[role="dialog"] button', '.dialog button', '.modal button'], 'type': 'Dialog button'},
                
                # Specific website patterns
                {'selectors': ['button#W0wltc', 'button.VfPpkd-LgbsSe'], 'type': 'Google specific'},  # Google "Accept" button
                {'selectors': ['button[data-cookiebanner="accept_button"]', '#onetrust-accept-btn-handler'], 'type': 'OneTrust cookie'},
                {'selectors': ['button.ot-sdk-button-primary', '.cookie-accept'], 'type': 'Cookie widget'}
            ]
            
            # Try each pattern
            for pattern in popup_patterns:
                for selector in pattern['selectors']:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        
                        if count > 0:
                            # Check if element is visible
                            for i in range(count):
                                element = elements.nth(i)
                                if await element.is_visible():
                                    await element.click()
                                    popups_closed.append(f"✅ Closed {pattern['type']}: {selector}")
                                    await self.human_delay(500, 1500)
                                    break
                    except Exception as e:
                        continue
            
            # Check for overlay backgrounds and click outside
            overlay_selectors = ['.modal-backdrop', '.overlay', '.popup-background', '[role="presentation"]']
            for selector in overlay_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        # Try pressing Escape key
                        await page.keyboard.press('Escape')
                        popups_closed.append(f"⌨️ Pressed Escape for overlay")
                        await self.human_delay(500, 1000)
                        break
                except:
                    continue
                    
        except Exception as e:
            popups_closed.append(f"❌ Popup detection error: {str(e)}")
        
        return popups_closed

    async def detect_captcha_elements(self, page):
        """Enhanced CAPTCHA detection"""
        captcha_found = []
        
        try:
            # CAPTCHA patterns
            captcha_patterns = [
                # reCAPTCHA
                {'selectors': ['iframe[src*="recaptcha"]', '.g-recaptcha', '#recaptcha', '[data-sitekey]'], 'type': 'reCAPTCHA'},
                
                # hCaptcha
                {'selectors': ['iframe[src*="hcaptcha"]', '.h-captcha', '[data-hcaptcha-site-key]'], 'type': 'hCaptcha'},
                
                # Cloudflare
                {'selectors': ['#cf-challenge-stage', '.cf-browser-verification'], 'type': 'Cloudflare'},
                
                # Generic bot detection
                {'selectors': ['input[type="checkbox"][title*="robot"]', '[aria-label*="not a robot"]'], 'type': 'Bot verification'}
            ]
            
            for pattern in captcha_patterns:
                for selector in pattern['selectors']:
                    try:
                        if await page.locator(selector).count() > 0:
                            captcha_found.append(pattern['type'])
                    except:
                        continue
            
            # Text-based detection
            try:
                page_text = await page.text_content('body')
                if page_text:
                    bot_texts = ["I'm not a robot", "Verify you are human", "Complete the security check"]
                    for text in bot_texts:
                        if text.lower() in page_text.lower():
                            captcha_found.append("Text-based verification")
                            break
            except:
                pass
                
        except Exception as e:
            captcha_found.append(f"Detection error: {str(e)}")
        
        return captcha_found

    async def handle_captcha(self, page, captcha_types):
        """Handle detected CAPTCHAs"""
        solved = []
        
        for captcha_type in captcha_types:
            try:
                if "reCAPTCHA" in captcha_type:
                    # Handle reCAPTCHA
                    selectors = ['.recaptcha-checkbox-border', '#recaptcha-anchor', 'span[role="checkbox"]']
                    for selector in selectors:
                        try:
                            element = page.locator(selector)
                            if await element.count() > 0 and await element.is_visible():
                                await element.click()
                                solved.append("🤖 Clicked reCAPTCHA checkbox")
                                await self.human_delay(2000, 4000)
                                break
                        except:
                            continue
                            
                elif "hCaptcha" in captcha_type:
                    # Handle hCaptcha
                    selectors = ['#checkbox', '.hcaptcha-box']
                    for selector in selectors:
                        try:
                            element = page.locator(selector)
                            if await element.count() > 0 and await element.is_visible():
                                await element.click()
                                solved.append("🤖 Clicked hCaptcha checkbox")
                                await self.human_delay(2000, 4000)
                                break
                        except:
                            continue
                            
                elif "Cloudflare" in captcha_type:
                    # Wait for Cloudflare
                    solved.append("🛡️ Waiting for Cloudflare verification...")
                    await self.human_delay(5000, 10000)
                    
                elif "Bot verification" in captcha_type or "Text-based" in captcha_type:
                    # Handle generic verification
                    selectors = ['input[type="checkbox"]', '[role="checkbox"]', 'button:has-text("Verify")', 'button:has-text("Continue")']
                    for selector in selectors:
                        try:
                            element = page.locator(selector)
                            if await element.count() > 0 and await element.is_visible():
                                await element.click()
                                solved.append("✅ Completed verification")
                                await self.human_delay(1000, 3000)
                                break
                        except:
                            continue
                            
            except Exception as e:
                solved.append(f"❌ CAPTCHA handling error: {str(e)}")
        
        return solved

    async def smart_search(self, page, search_term):
        """Smart search that handles different website types"""
        try:
            # Wait for page to stabilize
            await self.human_delay(1000, 2000)
            
            # Close any popups first
            popup_results = await self.detect_and_close_popups(page)
            
            # Detect website type from URL
            current_url = page.url.lower()
            
            # Website-specific search strategies
            if 'google.com' in current_url:
                selectors = [
                    'textarea[name="q"]',      # New Google search
                    'input[name="q"]',         # Classic Google search
                    'input[title="Search"]',   # Google search with title
                    '#APjFqb',                 # Google search ID
                    '.gLFyf'                   # Google search class
                ]
            elif 'amazon.com' in current_url:
                selectors = [
                    'input#twotabsearchtextbox',
                    'input[name="field-keywords"]',
                    '#nav-search-bar-form input'
                ]
            elif 'youtube.com' in current_url:
                selectors = [
                    'input[name="search_query"]',
                    '#search input',
                    'input[placeholder*="Search"]'
                ]
            else:
                # Generic selectors
                selectors = [
                    'input[type="search"]',
                    'input[name="q"]',
                    'input[placeholder*="Search"]',
                    'input[placeholder*="search"]',
                    '#search input',
                    '.search-input',
                    'input[role="searchbox"]'
                ]
            
            # Try each selector
            for selector in selectors:
                try:
                    element = page.locator(selector)
                    await element.wait_for(timeout=5000)
                    
                    if await element.is_visible() and await element.is_enabled():
                        # Clear and type
                        await element.clear()
                        await element.focus()
                        
                        # Human-like typing
                        for char in search_term:
                            await page.keyboard.type(char)
                            await asyncio.sleep(random.uniform(0.05, 0.15))
                        
                        return f"✅ Successfully searched: {search_term}"
                        
                except Exception as e:
                    continue
            
            return "❌ Could not find search box"
            
        except Exception as e:
            return f"❌ Search error: {str(e)}"

    async def smart_submit(self, page):
        """Smart submit that tries multiple methods"""
        try:
            current_url = page.url.lower()
            
            # Website-specific submit strategies
            if 'google.com' in current_url:
                submit_selectors = [
                    'input[name="btnK"]',
                    'button[aria-label="Google Search"]',
                    '.gNO89b',
                    '.FPdoLc input'
                ]
            elif 'amazon.com' in current_url:
                submit_selectors = [
                    'input#nav-search-submit-button',
                    '#nav-search-submit-button',
                    '.nav-search-submit input'
                ]
            elif 'youtube.com' in current_url:
                submit_selectors = [
                    'button#search-icon-legacy',
                    '#search-icon-legacy',
                    'button[aria-label*="Search"]'
                ]
            else:
                submit_selectors = [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Search")',
                    '[aria-label*="Search"]'
                ]
            
            # Try clicking submit buttons
            for selector in submit_selectors:
                try:
                    element = page.locator(selector)
                    if await element.count() > 0 and await element.is_visible():
                        await element.click()
                        return "🖱️ Clicked submit button"
                except:
                    continue
            
            # Fallback: Press Enter
            await page.keyboard.press('Enter')
            return "⌨️ Pressed Enter (fallback)"
            
        except Exception as e:
            return f"❌ Submit error: {str(e)}"

    async def execute_complete_automation(self, user_request):
        """Execute complete automation with all smart features"""
        results = []
        popups_closed = 0
        captchas_solved = 0
        
        try:
            # Extract website and search term
            url = "https://google.com"  # Default
            search_term = "search query"
            
            if "amazon" in user_request.lower():
                url = "https://amazon.com"
            elif "youtube" in user_request.lower():
                url = "https://youtube.com"
            elif "github" in user_request.lower():
                url = "https://github.com"
            
            # Extract search term
            if "search for" in user_request.lower():
                search_term = user_request.lower().split("search for")[1].strip().split(" and")[0].split(" then")[0]
            elif "find" in user_request.lower():
                search_term = user_request.lower().split("find")[1].strip().split(" and")[0].split(" then")[0]
            
            # Start stealth browser
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            # Remove automation detection
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}};
            """)
            
            results.append("🛡️ Smart browser started with full protection")
            
            # Navigate to website
            await page.goto(url, wait_until='networkidle')
            results.append(f"🌐 Navigated to {url}")
            
            # Wait for page to load
            await self.human_delay(2000, 3000)
            
            # Phase 1: Handle popups
            popup_results = await self.detect_and_close_popups(page)
            if popup_results:
                results.extend(popup_results)
                popups_closed = len(popup_results)
                await self.human_delay(1000, 2000)
            
            # Phase 2: Handle CAPTCHAs
            captcha_types = await self.detect_captcha_elements(page)
            if captcha_types:
                results.append(f"🚨 Detected: {', '.join(captcha_types)}")
                captcha_results = await self.handle_captcha(page, captcha_types)
                results.extend(captcha_results)
                captchas_solved = len(captcha_results)
                await self.human_delay(2000, 4000)
            
            # Phase 3: Perform search
            search_result = await self.smart_search(page, search_term)
            results.append(search_result)
            
            await self.human_delay(1000, 2000)
            
            # Phase 4: Submit search
            submit_result = await self.smart_submit(page)
            results.append(submit_result)
            
            # Final check for new popups/CAPTCHAs
            await self.human_delay(2000, 3000)
            
            final_popups = await self.detect_and_close_popups(page)
            if final_popups:
                results.extend(final_popups)
                popups_closed += len(final_popups)
            
            final_captchas = await self.detect_captcha_elements(page)
            if final_captchas:
                final_captcha_results = await self.handle_captcha(page, final_captchas)
                results.extend(final_captcha_results)
                captchas_solved += len(final_captcha_results)
            
            # Wait to see results
            await self.human_delay(3000, 5000)
            
            results.append(f"🎉 Complete! Closed {popups_closed} popups, solved {captchas_solved} challenges")
            
            # Close browser
            await browser.close()
            await playwright.stop()
            
        except Exception as e:
            results.append(f"❌ Critical Error: {str(e)}")
            
        return results

# Initialize session state
if 'automation_history' not in st.session_state:
    st.session_state.automation_history = []

if 'tool' not in st.session_state:
    st.session_state.tool = CompleteSmartAutomation()

# Main UI
st.markdown('<h1 class="main-title">🛡️ Agentic Smart Automation</h1>', unsafe_allow_html=True)

# # Feature badges
# col1, col2, col3 = st.columns(3)
# with col1:
#     st.markdown('<div class="popup-badge">🚫 Popup Killer</div>', unsafe_allow_html=True)
# with col2:
#     st.markdown('<div class="smart-badge">🤖 CAPTCHA Solver</div>', unsafe_allow_html=True)
# with col3:
#     st.markdown('<div class="popup-badge">🛡️ Full Protection</div>', unsafe_allow_html=True)

st.markdown("### Handles popups, CAPTCHAs, cookie banners - everything automatically!")

# Input section
with st.container():
    user_request = st.text_input(
        "Enter your automation request:",
        placeholder="Example: Go to Google and search for wireless headphones",
        help="Complete automation that handles all website obstacles"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        automate_button = st.button("🛡️ Start Complete Automation", type="primary")
    with col2:
        clear_button = st.button("🗑️ Clear History")

# Handle automation
if automate_button and user_request:
    if not os.getenv("OPENAI_API_KEY"):
        st.error("❌ Please set your OPENAI_API_KEY environment variable")
    else:
        start_time = time.time()
        
        with st.spinner("🧠 Starting complete automation..."):
            try:
                st.info("🤖 Executing with full popup & CAPTCHA protection...")
                
                # Use complete automation
                results = st.session_state.tool.run_complete_automation(user_request)
                
                total_time = time.time() - start_time
                
                # Show results
                st.markdown("### 🛡️ Complete Results")
                popup_count = 0
                captcha_count = 0
                
                for result in results:
                    if "✅ Closed" in result or "⌨️ Pressed Escape" in result:
                        st.success(result)
                        popup_count += 1
                    elif "🤖" in result or "🛡️" in result or "🚨" in result:
                        st.success(result)
                        if "CAPTCHA" in result or "reCAPTCHA" in result or "verification" in result:
                            captcha_count += 1
                    elif "❌" in result:
                        st.error(result)
                    elif "🎉" in result:
                        st.success(result)
                    else:
                        st.info(result)
                
                # Metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("⏱️ Total Time", f"{total_time:.2f}s")
                with col2:
                    st.metric("🚫 Popups Closed", popup_count)
                with col3:
                    st.metric("🤖 CAPTCHAs Solved", captcha_count)
                
                # Save to history
                st.session_state.automation_history.append({
                    'request': user_request,
                    'results': results,
                    'execution_time': total_time,
                    'popup_count': popup_count,
                    'captcha_count': captcha_count,
                    'timestamp': time.strftime("%H:%M:%S")
                })
                
            except Exception as e:
                st.error(f"❌ Automation failed: {str(e)}")

# Clear history
if clear_button:
    st.session_state.automation_history = []
    st.success("✅ History cleared!")

# Show examples
st.markdown("### 🛡️ Complete Test Examples")
examples = [
    "Go to Google and search for wireless headphones",
    "Go to Amazon and search for laptop deals", 
    "Go to YouTube and search for python tutorials",
    "Go to GitHub and search for automation projects"
]

cols = st.columns(2)
for i, example in enumerate(examples):
    with cols[i % 2]:
        if st.button(f"🛡️ {example}", key=f"example_{i}"):
            st.session_state.example_text = example
            st.rerun()

# Show complete history
if st.session_state.automation_history:
    st.markdown("### 📊 Complete Automation History")
    for i, item in enumerate(reversed(st.session_state.automation_history)):
        with st.expander(f"🛡️ {item['request'][:40]}... ({item['execution_time']:.1f}s)"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Request:**", item['request'])
                st.write("**Time:**", f"{item['execution_time']:.2f}s")
                st.write("**Popups Closed:**", item['popup_count'])
                st.write("**CAPTCHAs Solved:**", item['captcha_count'])
            with col2:
                st.write("**Key Results:**")
                important_results = [r for r in item['results'] if any(word in r for word in ['Closed', 'Clicked', 'Successfully', 'Complete'])]
                for result in important_results[:4]:
                    st.write(f"- {result}")

# Footer
st.markdown("---")
st.markdown("🛡️ **Complete Smart Automation** - Handles Everything: Popups + CAPTCHAs + Cookie Banners")
