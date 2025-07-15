# app.py - Fixed Web Automation Tool
import streamlit as st
import asyncio
import os
import threading
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from playwright.async_api import async_playwright
import logging

# Load environment
load_dotenv()

# Configure Streamlit
st.set_page_config(
    page_title="🤖 Web Automation Tool",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #2E86AB;
        font-size: 2.5rem;
        margin-bottom: 2rem;
    }
    .success-msg {
        background: #d4edda;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .error-msg {
        background: #f8d7da;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class WebAutomationTool:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            st.error("❌ Please set OPENAI_API_KEY in your environment")
            return
            
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            openai_api_key=self.api_key
        )
        
        # Create CrewAI agents
        self.planner_agent = Agent(
            role="Automation Planner",
            goal="Break down user requests into simple automation steps",
            backstory="You are an expert at understanding user requests and creating step-by-step automation plans for web browsers.",
            llm=self.llm,
            verbose=True,
            allow_delegation=True
        )
        
        self.executor_agent = Agent(
            role="Browser Controller", 
            goal="Execute web automation steps using Playwright",
            backstory="You are a skilled web automation specialist who can navigate websites, click buttons, and fill forms.",
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def create_automation_plan(self, user_request):
        """Create automation plan using CrewAI"""
        planning_task = Task(
            description=f"""
            Create a step-by-step automation plan for this request: "{user_request}"
            
            Break it down into these types of actions:
            1. navigate - Go to a website
            2. fill - Enter text in input fields  
            3. click - Click buttons or links
            4. wait - Wait for page to load
            
            Return a simple list of steps like:
            - navigate: https://amazon.com
            - wait: 3 seconds
            - fill: search box with "wireless headphones"
            - click: search button
            
            Be specific about what to search for and where to click.
            """,
            agent=self.planner_agent,
            expected_output="List of automation steps"
        )
        
        crew = Crew(
            agents=[self.planner_agent],
            tasks=[planning_task],
            verbose=True
        )
        
        result = crew.kickoff()
        return str(result)

    def run_automation_sync(self, plan, user_request):
        """Run automation in a synchronous way for Streamlit"""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the async automation
            results = loop.run_until_complete(self.execute_automation(plan, user_request))
            
            # Clean up
            loop.close()
            
            return results
            
        except Exception as e:
            return [f"❌ Error: {str(e)}"]

    async def execute_automation(self, plan, user_request):
        """Execute the automation plan"""
        results = []
        
        try:
            # Start Playwright
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=False)
            page = await browser.new_page()
            
            results.append("✅ Browser started")
            
            # Parse and execute plan
            lines = plan.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('-'):
                    line = line.lstrip('- ')
                
                try:
                    if line.startswith('navigate:'):
                        url = line.replace('navigate:', '').strip()
                        if not url.startswith('http'):
                            url = f"https://{url}"
                        await page.goto(url, timeout=30000)
                        results.append(f"🌐 Navigated to {url}")
                        
                    elif line.startswith('wait:'):
                        wait_time = 3  # default
                        try:
                            wait_time = int(''.join(filter(str.isdigit, line)))
                        except:
                            pass
                        await asyncio.sleep(wait_time)
                        results.append(f"⏳ Waited {wait_time} seconds")
                        
                    elif line.startswith('fill:'):
                        # Extract search term from the line
                        if 'with "' in line:
                            search_term = line.split('with "')[1].split('"')[0]
                        elif "with '" in line:
                            search_term = line.split("with '")[1].split("'")[0]
                        else:
                            # Fallback - extract from original request
                            search_term = user_request.split('search for ')[-1].split(' and')[0].split(' then')[0]
                        
                        # Common search selectors
                        search_selectors = [
                            'input[name="field-keywords"]',  # Amazon
                            'input#twotabsearchtextbox',     # Amazon
                            'input[name="q"]',               # Google
                            'input[name="search_query"]',    # YouTube
                            'input[type="search"]',
                            'input[placeholder*="Search"]',
                            '#search',
                            '.search-input'
                        ]
                        
                        filled = False
                        for selector in search_selectors:
                            try:
                                await page.wait_for_selector(selector, timeout=10000)
                                await page.fill(selector, search_term)
                                results.append(f"✏️ Filled search with: {search_term}")
                                filled = True
                                break
                            except:
                                continue
                        
                        if not filled:
                            results.append(f"❌ Could not find search box")
                            
                    elif line.startswith('click:'):
                        # Common button selectors
                        button_selectors = [
                            'input[type="submit"]',
                            'button[type="submit"]', 
                            'input#nav-search-submit-button',  # Amazon
                            'button#search-icon-legacy',       # YouTube
                            'input[name="btnK"]',              # Google
                            '.nav-search-submit',
                            '[aria-label*="Search"]',
                            'button:has-text("Search")',
                            'input[value*="Search"]'
                        ]
                        
                        clicked = False
                        for selector in button_selectors:
                            try:
                                await page.wait_for_selector(selector, timeout=5000)
                                await page.click(selector)
                                results.append(f"🖱️ Clicked search button")
                                clicked = True
                                break
                            except:
                                continue
                        
                        if not clicked:
                            # Try pressing Enter
                            try:
                                await page.keyboard.press('Enter')
                                results.append(f"⌨️ Pressed Enter")
                            except:
                                results.append(f"❌ Could not click or press Enter")
                                
                    await asyncio.sleep(1)  # Small delay between actions
                    
                except Exception as step_error:
                    results.append(f"❌ Step error: {str(step_error)}")
                    continue
            
            # Wait to see results
            await asyncio.sleep(5)
            results.append("🎉 Automation completed!")
            
            # Close browser
            await browser.close()
            await playwright.stop()
            
        except Exception as e:
            results.append(f"❌ Error: {str(e)}")
            
        return results

# Initialize session state
if 'automation_history' not in st.session_state:
    st.session_state.automation_history = []

if 'tool' not in st.session_state:
    st.session_state.tool = WebAutomationTool()

# Main UI
st.markdown('<h1 class="main-title">🤖 Web Automation Tool</h1>', unsafe_allow_html=True)
st.markdown("### Tell me what you want to automate and I'll do it!")

# Input section
with st.container():
    user_request = st.text_input(
        "Enter your automation request:",
        placeholder="Example: Go to Amazon and search for wireless headphones",
        help="Just describe what you want to do in plain English"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        automate_button = st.button("🚀 Start Automation", type="primary")
    with col2:
        clear_button = st.button("🗑️ Clear History")

# Handle automation
if automate_button and user_request:
    if not os.getenv("OPENAI_API_KEY"):
        st.error("❌ Please set your OPENAI_API_KEY environment variable")
    else:
        with st.spinner("🤖 Creating automation plan..."):
            try:
                # Create plan
                plan = st.session_state.tool.create_automation_plan(user_request)
                st.success("✅ Plan created!")
                
                # Show plan
                with st.expander("📋 Automation Plan"):
                    st.text(plan)
                
                # Execute automation
                st.info("🌐 Starting browser automation...")
                
                # Use the synchronous wrapper
                results = st.session_state.tool.run_automation_sync(plan, user_request)
                
                # Show results
                st.markdown("### 📊 Automation Results")
                for result in results:
                    if "✅" in result or "🌐" in result or "✏️" in result or "🖱️" in result or "⌨️" in result or "⏳" in result:
                        st.success(result)
                    elif "❌" in result:
                        st.error(result)
                    elif "🎉" in result:
                        st.balloons()
                        st.success(result)
                    else:
                        st.info(result)
                
                # Save to history
                st.session_state.automation_history.append({
                    'request': user_request,
                    'plan': plan,
                    'results': results,
                    'timestamp': str(len(st.session_state.automation_history) + 1)
                })
                
            except Exception as e:
                st.error(f"❌ Automation failed: {str(e)}")

# Clear history
if clear_button:
    st.session_state.automation_history = []
    st.success("✅ History cleared!")

# Show examples
st.markdown("### 💡 Example Requests")
examples = [
    "Go to Amazon and search for wireless headphones",
    "Navigate to Google and search for weather",
    "Go to YouTube and search for python tutorials",
    "Visit GitHub and search for machine learning"
]

cols = st.columns(2)
for i, example in enumerate(examples):
    with cols[i % 2]:
        if st.button(f"📝 {example}", key=f"example_{i}"):
            # Set the example in the text input by using session state
            st.session_state.example_text = example
            st.rerun()

# Set example text if selected
if 'example_text' in st.session_state:
    # This will be handled by the text_input widget
    pass

# Show history
if st.session_state.automation_history:
    st.markdown("### 📈 Automation History")
    for i, item in enumerate(reversed(st.session_state.automation_history)):
        with st.expander(f"🤖 {item['request'][:50]}..."):
            st.write("**Request:**", item['request'])
            st.write("**Plan:**")
            st.text(item['plan'])
            st.write("**Results:**")
            for result in item['results']:
                st.write(f"- {result}")

# Footer
st.markdown("---")
st.markdown("🤖 **Simple Web Automation** - Powered by CrewAI + Playwright + GPT-4o")