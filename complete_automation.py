#!/usr/bin/env python3
"""
Complete Universal Web Automation System - Single File
Works with any website using natural language instructions
No external file dependencies - everything in one file
"""

import os
import asyncio
import re
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

# Core imports
try:
    from crewai import Agent, Task, Crew, Process
    from langchain_openai import ChatOpenAI
    from langchain.schema import HumanMessage, SystemMessage
    from pydantic import BaseModel, Field, validator
    from dotenv import load_dotenv
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"❌ Missing required packages. Please install: {e}")
    print("Run: pip install crewai langchain-openai playwright python-dotenv openai")
    exit(1)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('complete_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ActionType(Enum):
    """Universal action types for web automation"""
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    WAIT = "wait"
    SCROLL = "scroll"
    SCREENSHOT = "screenshot"
    EXTRACT_TEXT = "extract_text"
    HOVER = "hover"

@dataclass
class AutomationConfig:
    """Universal automation configuration"""
    headless: bool = False
    timeout: int = 30000
    viewport_width: int = 1920
    viewport_height: int = 1080
    slow_mo: int = 300
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    enable_logging: bool = True
    max_retries: int = 3
    retry_delay: int = 1

@dataclass
class AutomationStep:
    """Universal automation step"""
    action: ActionType
    description: str
    target: Optional[str] = None
    value: Optional[str] = None
    selector: Optional[str] = None
    timeout: int = 15000
    wait_after: int = 1000
    optional: bool = False

class CompleteAutomationTool:
    """Complete automation tool - all functionality in one class"""
    
    def __init__(self, config: AutomationConfig = None):
        self.config = config or AutomationConfig()
        self.browser = None
        self.page = None
        self.context = None
        self.playwright_instance = None
        self.current_url = ""
        
        # Initialize LLM for intelligent planning
        try:
            self.llm = ChatOpenAI(
                model="gpt-4",
                temperature=0.1,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self.llm = None
    
    async def execute_automation(self, instruction: str, url: str = "") -> str:
        """Execute universal automation based on natural language"""
        try:
            logger.info(f"🚀 Starting automation: {instruction}")
            
            # Initialize browser
            await self._init_browser()
            
            # Create automation plan
            automation_plan = await self._create_automation_plan(instruction, url)
            
            results = [f"🎯 Executing {len(automation_plan)} steps for: {instruction}"]
            
            # Execute each step
            for i, step in enumerate(automation_plan, 1):
                try:
                    results.append(f"\n🔄 Step {i}: {step.description}")
                    success = await self._execute_step(step)
                    
                    if success:
                        results.append(f"✅ Step {i} completed successfully")
                    elif step.optional:
                        results.append(f"⚠️ Step {i} skipped (optional)")
                    else:
                        results.append(f"❌ Step {i} failed but continuing...")
                        
                except Exception as e:
                    error_msg = f"❌ Step {i} error: {str(e)}"
                    results.append(error_msg)
                    logger.error(error_msg)
                    continue
            
            results.append(f"\n🎉 Automation completed!")
            return "\n".join(results)
            
        except Exception as e:
            error_msg = f"❌ Critical automation error: {str(e)}"
            logger.error(error_msg)
            return error_msg
        finally:
            await self._cleanup_browser()
    
    async def _create_automation_plan(self, instruction: str, url: str = "") -> List[AutomationStep]:
        """Create intelligent automation plan"""
        
        # Try LLM-based planning first
        if self.llm:
            try:
                return await self._create_llm_plan(instruction, url)
            except Exception as e:
                logger.warning(f"LLM planning failed: {e}, using fallback")
        
        # Fallback to pattern-based planning
        return self._create_pattern_plan(instruction, url)
    
    async def _create_llm_plan(self, instruction: str, url: str = "") -> List[AutomationStep]:
        """Create plan using LLM intelligence"""
        
        system_prompt = """
        You are an expert web automation planner. Create a step-by-step automation plan from natural language.
        
        Available actions: navigate, click, fill, wait, scroll, screenshot, extract_text, hover
        
        Return a JSON array of steps:
        [
            {
                "action": "navigate|click|fill|wait|scroll|screenshot|extract_text|hover",
                "description": "What this step does",
                "target": "URL for navigate, or element description for other actions",
                "value": "Text to enter for fill actions",
                "selector": "CSS selector if known",
                "timeout": 15000,
                "wait_after": 1000,
                "optional": false
            }
        ]
        
        Be smart about:
        1. Detecting websites from instructions
        2. Understanding user intent
        3. Adding appropriate waits
        4. Using keyboard shortcuts when possible
        
        Examples:
        "Go to YouTube and search for cats" -> 
        [
            {"action": "navigate", "description": "Go to YouTube", "target": "https://youtube.com"},
            {"action": "wait", "description": "Wait for page load", "wait_after": 3000},
            {"action": "fill", "description": "Search for cats", "target": "search", "value": "cats"},
            {"action": "wait", "description": "Wait after typing", "wait_after": 1000},
            {"action": "click", "description": "Press Enter to search", "target": "search_submit", "optional": true}
        ]
        
        Return ONLY valid JSON, no other text.
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Create automation plan for: '{instruction}'\nStarting URL: '{url or 'Not specified'}'")
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Clean response
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            plan_data = json.loads(content)
            
            # Convert to AutomationStep objects
            steps = []
            for step_data in plan_data:
                step = AutomationStep(
                    action=ActionType(step_data['action']),
                    description=step_data['description'],
                    target=step_data.get('target'),
                    value=step_data.get('value'),
                    selector=step_data.get('selector'),
                    timeout=step_data.get('timeout', 15000),
                    wait_after=step_data.get('wait_after', 1000),
                    optional=step_data.get('optional', False)
                )
                steps.append(step)
            
            logger.info(f"✅ Created LLM plan with {len(steps)} steps")
            return steps
            
        except Exception as e:
            logger.error(f"LLM plan creation failed: {e}")
            raise
    
    def _create_pattern_plan(self, instruction: str, url: str = "") -> List[AutomationStep]:
        """Create plan using pattern matching (fallback)"""
        steps = []
        instruction_lower = instruction.lower()
        
        # Extract search query
        search_query = self._extract_search_query(instruction)
        
        # Detect website and create appropriate steps
        if 'youtube' in instruction_lower:
            steps.extend([
                AutomationStep(ActionType.NAVIGATE, "Navigate to YouTube", target="https://youtube.com"),
                AutomationStep(ActionType.WAIT, "Wait for YouTube to load", wait_after=3000),
                AutomationStep(ActionType.FILL, f"Search for '{search_query}'", target="search", value=search_query),
                AutomationStep(ActionType.WAIT, "Wait after typing", wait_after=1500),
                AutomationStep(ActionType.CLICK, "Submit search", target="search_submit", optional=True)
            ])
            
            if 'play' in instruction_lower and 'first' in instruction_lower:
                steps.extend([
                    AutomationStep(ActionType.WAIT, "Wait for search results", wait_after=3000),
                    AutomationStep(ActionType.CLICK, "Click first video", target="first_video", optional=True)
                ])
                
        elif 'google' in instruction_lower:
            steps.extend([
                AutomationStep(ActionType.NAVIGATE, "Navigate to Google", target="https://google.com"),
                AutomationStep(ActionType.WAIT, "Wait for Google to load", wait_after=2000),
                AutomationStep(ActionType.FILL, f"Search for '{search_query}'", target="search", value=search_query),
                AutomationStep(ActionType.WAIT, "Wait after typing", wait_after=1000)
            ])
            
        elif 'amazon' in instruction_lower:
            steps.extend([
                AutomationStep(ActionType.NAVIGATE, "Navigate to Amazon", target="https://amazon.com"),
                AutomationStep(ActionType.WAIT, "Wait for Amazon to load", wait_after=2000),
                AutomationStep(ActionType.FILL, f"Search for '{search_query}'", target="search", value=search_query),
                AutomationStep(ActionType.WAIT, "Wait after typing", wait_after=1000),
                AutomationStep(ActionType.CLICK, "Submit search", target="search_submit", optional=True)
            ])
            
        elif url:
            steps.extend([
                AutomationStep(ActionType.NAVIGATE, f"Navigate to {url}", target=url),
                AutomationStep(ActionType.WAIT, "Wait for page to load", wait_after=3000)
            ])
            
        else:
            # Generic web automation
            steps.extend([
                AutomationStep(ActionType.NAVIGATE, "Navigate to Google", target="https://google.com"),
                AutomationStep(ActionType.WAIT, "Wait for page load", wait_after=2000),
                AutomationStep(ActionType.FILL, f"Search for '{search_query}'", target="search", value=search_query)
            ])
        
        logger.info(f"✅ Created pattern plan with {len(steps)} steps")
        return steps
    
    def _extract_search_query(self, instruction: str) -> str:
        """Extract search query from instruction"""
        # Common patterns for search extraction
        patterns = [
            r'search for\s+["\']?([^"\']+?)["\']?(?:\s*(?:,|and|then|\.|play|click|$))',
            r'find\s+["\']?([^"\']+?)["\']?(?:\s*(?:,|and|then|\.|play|click|$))',
            r'look for\s+["\']?([^"\']+?)["\']?(?:\s*(?:,|and|then|\.|play|click|$))',
            r'about\s+["\']?([^"\']+?)["\']?(?:\s*(?:,|and|then|\.|play|click|$))'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, instruction.lower())
            if match:
                query = match.group(1).strip()
                # Clean up query
                stop_words = ['and', 'then', 'play', 'click', 'first', 'video']
                words = [w for w in query.split() if w.lower() not in stop_words]
                return ' '.join(words)
        
        # Fallback - try to extract meaningful words
        words = instruction.lower().split()
        skip_words = {'go', 'to', 'navigate', 'open', 'visit', 'search', 'find', 'look', 'for', 'and', 'then', 'play', 'click', 'first', 'video'}
        meaningful_words = [w for w in words if w not in skip_words and not w.endswith('.com')]
        
        return ' '.join(meaningful_words[:5]) if meaningful_words else "cats"  # Default fallback
    
    async def _init_browser(self):
        """Initialize browser with enhanced settings"""
        try:
            from playwright.async_api import async_playwright
            
            self.playwright_instance = await async_playwright().start()
            
            # Launch browser
            self.browser = await self.playwright_instance.chromium.launch(
                headless=self.config.headless,
                slow_mo=self.config.slow_mo,
                args=[
                    f"--window-size={self.config.viewport_width},{self.config.viewport_height}",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            
            # Create context
            self.context = await self.browser.new_context(
                viewport={"width": self.config.viewport_width, "height": self.config.viewport_height},
                user_agent=self.config.user_agent,
                java_script_enabled=True,
                ignore_https_errors=True
            )
            
            # Create page
            self.page = await self.context.new_page()
            self.page.set_default_timeout(self.config.timeout)
            
            logger.info("✅ Browser initialized successfully")
            
        except Exception as e:
            logger.error(f"Browser initialization failed: {e}")
            raise
    
    async def _execute_step(self, step: AutomationStep) -> bool:
        """Execute a single automation step"""
        try:
            success = False
            
            if step.action == ActionType.NAVIGATE:
                success = await self._navigate(step)
            elif step.action == ActionType.CLICK:
                success = await self._smart_click(step)
            elif step.action == ActionType.FILL:
                success = await self._smart_fill(step)
            elif step.action == ActionType.WAIT:
                success = await self._wait(step)
            elif step.action == ActionType.SCROLL:
                success = await self._scroll(step)
            elif step.action == ActionType.SCREENSHOT:
                success = await self._screenshot(step)
            else:
                logger.warning(f"Unknown action: {step.action}")
                return False
            
            # Wait after action
            if success and step.wait_after > 0:
                await asyncio.sleep(step.wait_after / 1000)
            
            return success
            
        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            return False
    
    async def _navigate(self, step: AutomationStep) -> bool:
        """Navigate to URL"""
        try:
            url = step.target
            if not url.startswith('http'):
                url = f"https://{url}"
            
            logger.info(f"🌐 Navigating to: {url}")
            
            response = await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            if response and response.status < 400:
                self.current_url = url
                
                # Wait for network idle
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    await asyncio.sleep(2)  # Fallback wait
                
                logger.info(f"✅ Successfully navigated to {url}")
                return True
            else:
                logger.warning(f"⚠️ Navigation status: {response.status if response else 'Unknown'}")
                return False
                
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    async def _smart_click(self, step: AutomationStep) -> bool:
        """Intelligent clicking with multiple strategies"""
        try:
            # Try Enter key first for search-related actions
            if step.target and any(word in step.target.lower() for word in ['search', 'submit', 'enter']):
                try:
                    logger.info("⌨️ Trying Enter key")
                    await self.page.keyboard.press("Enter")
                    await asyncio.sleep(1)
                    logger.info("✅ Enter key successful")
                    return True
                except:
                    pass
            
            # Get smart selectors for clicking
            selectors = self._get_smart_selectors(step.target, "click")
            
            for selector in selectors:
                try:
                    logger.info(f"🖱️ Trying to click: {selector}")
                    
                    # Wait for element
                    await self.page.wait_for_selector(selector, timeout=step.timeout)
                    element = self.page.locator(selector)
                    
                    # Scroll into view and click
                    await element.scroll_into_view_if_needed()
                    await asyncio.sleep(0.3)
                    await element.click(timeout=5000)
                    
                    logger.info(f"✅ Successfully clicked: {selector}")
                    return True
                    
                except Exception as e:
                    logger.debug(f"Click failed for {selector}: {e}")
                    continue
            
            # Try clicking by text content as fallback
            if step.target:
                try:
                    await self.page.get_by_text(step.target).click(timeout=3000)
                    logger.info(f"✅ Clicked by text: {step.target}")
                    return True
                except:
                    pass
            
            logger.warning(f"⚠️ Could not click: {step.target}")
            return step.optional  # Return True if optional
            
        except Exception as e:
            logger.error(f"Click operation failed: {e}")
            return False
    
    async def _smart_fill(self, step: AutomationStep) -> bool:
        """Intelligent form filling"""
        try:
            if not step.value:
                logger.warning("No value to fill")
                return False
            
            selectors = self._get_smart_selectors(step.target, "fill")
            
            for selector in selectors:
                try:
                    logger.info(f"✏️ Trying to fill: {selector}")
                    
                    # Wait for element
                    await self.page.wait_for_selector(selector, timeout=step.timeout)
                    element = self.page.locator(selector)
                    
                    # Focus, clear, and fill
                    await element.focus()
                    await element.clear()
                    await asyncio.sleep(0.2)
                    
                    # Type with delay for reliability
                    await element.type(step.value, delay=50)
                    await asyncio.sleep(0.3)
                    
                    # Verify
                    current_value = await element.input_value()
                    if current_value and step.value.lower() in current_value.lower():
                        logger.info(f"✅ Successfully filled: {selector} with '{current_value}'")
                        return True
                    
                except Exception as e:
                    logger.debug(f"Fill failed for {selector}: {e}")
                    continue
            
            logger.warning(f"⚠️ Could not fill: {step.target}")
            return step.optional
            
        except Exception as e:
            logger.error(f"Fill operation failed: {e}")
            return False
    
    def _get_smart_selectors(self, target: str, action: str) -> List[str]:
        """Generate smart selectors based on target and action"""
        selectors = []
        
        if not target:
            return selectors
        
        target_lower = target.lower()
        
        # Website-specific selectors
        if action == "fill":
            if "search" in target_lower:
                selectors.extend([
                    # YouTube
                    "input[name='search_query']",
                    # Google
                    "input[name='q']", "textarea[name='q']", "#APjFqb",
                    # Amazon
                    "input#twotabsearchtextbox", "input[name='field-keywords']",
                    # Generic
                    "input[type='search']", "input[placeholder*='Search']", "#search", ".search-input"
                ])
            else:
                selectors.extend(["input[type='text']", "input", "textarea"])
        
        elif action == "click":
            if "search" in target_lower or "submit" in target_lower:
                selectors.extend([
                    # YouTube
                    "button#search-icon-legacy", "#search-icon-legacy",
                    # Google
                    "input[name='btnK']", "input[value='Google Search']",
                    # Amazon
                    "input#nav-search-submit-button",
                    # Generic
                    "button[type='submit']", "input[type='submit']", "button[aria-label*='Search']"
                ])
            elif "video" in target_lower or "first" in target_lower:
                selectors.extend([
                    # YouTube videos
                    "a#video-title", "#contents a#video-title:first-of-type",
                    ".ytd-video-renderer a:first-of-type", "a[href*='/watch']:first-of-type",
                    # Generic first elements
                    "a:first-of-type", "button:first-of-type"
                ])
            else:
                selectors.extend(["button", "a", "input[type='button']"])
        
        return selectors
    
    async def _wait(self, step: AutomationStep) -> bool:
        """Wait for specified duration"""
        try:
            wait_time = step.wait_after if step.wait_after > 0 else 1000
            await asyncio.sleep(wait_time / 1000)
            logger.info(f"⏳ Waited {wait_time}ms")
            return True
        except Exception as e:
            logger.error(f"Wait failed: {e}")
            return False
    
    async def _scroll(self, step: AutomationStep) -> bool:
        """Scroll page"""
        try:
            if step.value:
                await self.page.mouse.wheel(0, int(step.value))
            else:
                await self.page.keyboard.press("PageDown")
            logger.info("📜 Scrolled page")
            return True
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return False
    
    async def _screenshot(self, step: AutomationStep) -> bool:
        """Take screenshot"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            await self.page.screenshot(path=filename, full_page=True)
            logger.info(f"📸 Screenshot saved: {filename}")
            return True
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return False
    
    async def _cleanup_browser(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright_instance:
                await self.playwright_instance.stop()
            logger.info("🧹 Browser cleanup completed")
        except Exception as e:
            logger.error(f"Browser cleanup failed: {e}")


class CompleteAutomationInterface:
    """Complete automation interface"""
    
    def __init__(self, config: AutomationConfig = None):
        self.config = config or AutomationConfig()
        self.tool = CompleteAutomationTool(self.config)
        self.session_history = []
    
    def run_interactive(self):
        """Interactive automation interface"""
        print("🌟 Complete Universal Web Automation System")
        print("=" * 60)
        print("🎯 Features:")
        print("  • Works with ANY website")
        print("  • Natural language instructions")
        print("  • Intelligent planning with GPT-4")
        print("  • Smart error handling")
        print("  • Universal selectors")
        print("\n📝 Example instructions:")
        print("  • 'Go to YouTube and search for python tutorials'")
        print("  • 'Search Google for best restaurants near me'")
        print("  • 'Navigate to Amazon and find wireless keyboards'")
        print("  • 'Go to LinkedIn and look for data science jobs'")
        print("  • 'Visit any website and perform any action!'")
        print("\n⌨️  Commands: 'quit', 'history', 'help'")
        print("=" * 60)
        
        while True:
            try:
                print(f"\n🌟 Session {len(self.session_history) + 1}")
                instruction = input("Enter your automation instruction: ").strip()
                
                if instruction.lower() in ['quit', 'exit', 'q']:
                    print("👋 Thank you for using Complete Automation!")
                    break
                elif instruction.lower() == 'history':
                    self._show_history()
                    continue
                elif instruction.lower() == 'help':
                    self._show_help()
                    continue
                elif instruction.lower() == 'clear':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue
                
                if not instruction:
                    print("⚠️  Please enter a valid instruction.")
                    continue
                
                # Optional URL
                url = input("🔗 Starting URL (optional): ").strip()
                
                print(f"\n🎯 Processing: {instruction}")
                print("⏳ Please wait...")
                print("-" * 50)
                
                # Execute automation
                start_time = datetime.now()
                result = asyncio.run(self.tool.execute_automation(instruction, url))
                duration = (datetime.now() - start_time).total_seconds()
                
                # Store history
                self.session_history.append({
                    'instruction': instruction,
                    'url': url,
                    'duration': duration,
                    'timestamp': start_time,
                    'success': '✅' in result and '❌' not in result
                })
                
                print(f"\n✅ Completed in {duration:.1f} seconds")
                print("📋 Results:")
                print("-" * 50)
                print(result)
                print("=" * 60)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                logger.error(f"Interface error: {e}")
    
    def _show_history(self):
        """Show automation history"""
        if not self.session_history:
            print("📝 No history available.")
            return
        
        print("\n📈 Automation History:")
        print("-" * 50)
        for i, session in enumerate(self.session_history, 1):
            status = "✅" if session['success'] else "❌"
            print(f"{i}. {status} {session['instruction'][:50]}...")
            print(f"   ⏱️  {session['duration']:.1f}s | 🕐 {session['timestamp'].strftime('%H:%M:%S')}")
    
    def _show_help(self):
        """Show help"""
        print("\n🆘 Help - Complete Web Automation")
        print("-" * 50)
        print("📝 Just describe what you want to do in natural language!")
        print("\nExamples:")
        print("  • 'Go to YouTube and search for cats'")
        print("  • 'Search Google for weather forecast'")
        print("  • 'Navigate to Amazon and find books'")
        print("  • 'Go to any website and do anything!'")
        print("\n⌨️  Commands:")
        print("  • 'quit' - Exit")
        print("  • 'history' - Show history")
        print("  • 'help' - This help")


def validate_environment():
    """Validate environment setup"""
    issues = []
    
    if not os.getenv("OPENAI_API_KEY"):
        issues.append("OPENAI_API_KEY not set")
    
    try:
        import playwright
    except ImportError:
        issues.append("playwright not installed")
    
    return issues


def main():
    """Main function"""
    print("🚀 Complete Universal Web Automation System")
    print("=" * 50)
    
    # Validate environment
    issues = validate_environment()
    if issues:
        print("❌ Setup issues found:")
        for issue in issues:
            print(f"   • {issue}")
        print("\nTo fix:")
        print("1. pip install crewai langchain-openai playwright python-dotenv openai")
        print("2. playwright install chromium")
        print("3. Set OPENAI_API_KEY in .env file")
        return
    
    try:
        # Create config
        config = AutomationConfig(
            headless=False,  # Show browser for demonstration
            timeout=30000,
            slow_mo=300,     # Slow for visibility
            max_retries=3
        )
        
        # Start interface
        interface = CompleteAutomationInterface(config)
        
        print("✅ System ready!")
        print("🎯 Try: 'Go to YouTube and search for thailand itinerary 10 days'")
        
        interface.run_interactive()
        
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        logger.error(f"Startup error: {e}")


if __name__ == "__main__":
    main()


# Quick usage functions for developers
def quick_automation(instruction: str, headless: bool = True, url: str = "") -> str:
    """Quick automation function"""
    config = AutomationConfig(headless=headless)
    tool = CompleteAutomationTool(config)
    return asyncio.run(tool.execute_automation(instruction, url))


def demo_automation():
    """Demo function to test the system"""
    examples = [
        "Go to Google and search for cats",
        "Navigate to YouTube and search for music",
        "Go to Wikipedia and search for Python programming"
    ]
    
    print("🎭 Running demo automations...")
    for instruction in examples:
        print(f"\n📝 Testing: {instruction}")
        try:
            result = quick_automation(instruction, headless=True)
            print(f"✅ Result: {result[:100]}...")
        except Exception as e:
            print(f"❌ Error: {e}")


# Usage examples:
"""
# Interactive mode
python complete_automation.py

# Quick automation
from complete_automation import quick_automation
result = quick_automation("Go to YouTube and search for cats")

# Custom configuration
from complete_automation import AutomationConfig, CompleteAutomationTool
config = AutomationConfig(headless=False, slow_mo=500)
tool = CompleteAutomationTool(config)
result = asyncio.run(tool.execute_automation("Search Google for news"))
"""