"""Tasks for company finder agents."""

from crewai import Agent, Task

from air1.agents.company_finder.models import TargetCompanyProfile


def create_search_strategy_task(agent: Agent, target: TargetCompanyProfile) -> Task:
    """Task to generate search queries."""
    
    # Format list fields for string injection
    industries = ", ".join(target.industries) if target.industries else "Any"
    keywords = ", ".join(target.keywords)
    exclude = ", ".join(target.exclude_keywords) if target.exclude_keywords else "None"
    locations = ", ".join(target.locations) if target.locations else "Anywhere"
    signals = ", ".join(target.buying_signals) if target.buying_signals else "None specified"
    
    return Task(
        description=f"""
        Analyze the target company profile and generate effective search queries to find 
        LinkedIn Company pages (NOT personal profiles).
        
        TARGET PROFILE:
        - Business Model: {target.business_model}
        - Services: {target.service_description}
        - Industries: {industries}
        - Locations: {locations}
        - Keywords: {keywords}
        - Exclude: {exclude}
        - Signals: {signals}
        - Size: {target.min_employees or 1} - {target.max_employees or 'Any'} employees
        - Detailed Criteria: {target.detailed_criteria}
        
        Generate 5-10 specific search queries using "site:linkedin.com/company/" operator 
        combined with the keywords and business model logic.
        
        Example queries logic:
        - site:linkedin.com/company/ "{target.business_model}" "{target.service_description}"
        - site:linkedin.com/company/ "AI agent" "integration" {locations}
        """,
        expected_output="""A list of 5-10 distinct search queries optimized for finding 
        Target Company LinkedIn pages on search engines.""",
        agent=agent,
    )


def create_company_search_task(
    agent: Agent, 
    search_strategy_task: Task,
    max_results: int = 20
) -> Task:
    """Task to execute searches and find company URLs."""
    return Task(
        description=f"""
        Execute the search queries generated in the previous task using the Web Search tool.
        
        1. For each query, perform a search.
        2. Extract valid LinkedIn Company URLs (format: linkedin.com/company/xyz).
        3. Ignore personal profiles (linkedin.com/in/).
        4. Collect up to {max_results} unique company URLs.
        
        For each valid result, capture:
        - Company Name (from title)
        - LinkedIn URL
        """,
        expected_output=f"""A list of found unique LinkedIn Company URLs with their names. 
        Limit to {max_results} unique companies.""",
        agent=agent,
        context=[search_strategy_task],
    )


def create_signal_analysis_task(
    agent: Agent,
    search_task: Task,
    target: TargetCompanyProfile
) -> Task:
    """Task to find buying signals for candidates."""
    signals_text = ", ".join(target.buying_signals) if target.buying_signals else "General growth signals (Funding, Hiring, SEC filings)"
    
    return Task(
        description=f"""
        For each company found in the search task, analyze if they exhibit recent buying signals.
        
        Target Signals: {signals_text}
        
        For each company:
        1. Use SEC Filing Search tool to check for recent filings (10-K, S-1, 8-K).
        2. Use Crunchbase Search tool to check for recent funding or acquisitions.
        3. Use Web Search tool to find other relevant news/signals.
        
        Compile a list of signals found for each company. If no signals are found, note that.
        """,
        expected_output="""A mapping of Company Results with detected signals:
        - Company Name
        - LinkedIn URL
        - Detected Signals: [List of signals found with sources]
        """,
        agent=agent,
        context=[search_task],
    )


def create_company_validation_task(
    agent: Agent, 
    target: TargetCompanyProfile,
    search_task: Task,
    signal_task: Task
) -> Task:
    """Task to validate found companies."""
    return Task(
        description=f"""
        Validate the companies found in the search task against the target profile, taking into 
        account the buying signals found.
        
        For each company URL found:
        1. Fetch the company details using the LinkedIn Company Info tool.
        2. Analyze if it matches the target criteria:
           - Matches Business Model: {target.business_model}
           - Offers Services: {target.service_description}
           - Matches Size: {target.min_employees or 1}-{target.max_employees or 'Any'}
           - Has Buying Signals: Review the signals found in previous step.
        
        3. Score the match (0-100). Bonus points for strong buying signals.
        4. Provide reasoning for the score.
        
        You MUST fetch the real company info for validation. Do not guess based on search snippets.
        """,
        expected_output="""A list of validated companies in STRICT JSON format.
        
        The output must be a valid JSON array containing objects with these exact keys:
        [
            {
                "Company Name": "string",
                "LinkedIn URL": "string",
                "Match Score": int,
                "Reasoning": "string",
                "Detected Signals": ["signal 1", "signal 2"],
                "Extracted Details": {
                    "Industry": "string",
                    "Size": "string",
                    "Website": "string",
                    "Description": "string"
                }
            }
        ]
        Do not include markdown formatting like ```json ... ``` or any other text. Just the raw JSON array.
        """,
        agent=agent,
        context=[search_task, signal_task],
    )
