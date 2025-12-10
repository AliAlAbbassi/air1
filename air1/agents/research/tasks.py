"""Tasks for research prospecting agents."""

from crewai import Task, Agent

from air1.agents.research.models import ProspectInput


def create_linkedin_research_task(agent: Agent, prospect: ProspectInput) -> Task:
    """Task to research a prospect's LinkedIn profile."""
    return Task(
        description=f"""
        Research the LinkedIn profile for: {prospect.linkedin_username}
        
        Gather the following information:
        1. Current role and company
        2. Professional headline and summary
        3. Work history (last 3-5 positions)
        4. Education background
        5. Recent posts and engagement patterns
        6. Topics they frequently discuss or engage with
        7. Any mutual connections or shared interests
        
        Focus on finding information that can be used for personalized outreach.
        """,
        expected_output="""A comprehensive LinkedIn profile analysis including:
        - Professional background summary
        - Current role context
        - Recent activity highlights
        - Key topics of interest
        - Potential conversation starters based on their activity""",
        agent=agent,
    )


def create_company_research_task(agent: Agent, company_name: str) -> Task:
    """Task to research a prospect's company."""
    return Task(
        description=f"""
        Research the company: {company_name}
        
        Gather the following intelligence:
        1. Company overview (size, industry, founding date)
        2. Recent funding rounds or financial news
        3. Product launches or major announcements
        4. Leadership changes
        5. Hiring trends and open positions
        6. Competitive positioning
        7. Recent press coverage
        
        Focus on identifying buying signals and conversation starters.
        """,
        expected_output="""A comprehensive company intelligence report including:
        - Company overview and positioning
        - Recent developments and news
        - Growth signals (funding, hiring, expansion)
        - Potential pain points based on company stage/industry
        - Relevant talking points for outreach""",
        agent=agent,
    )


def create_pain_point_analysis_task(
    agent: Agent, 
    prospect: ProspectInput,
    linkedin_research: Task,
    company_research: Task,
) -> Task:
    """Task to analyze and infer prospect pain points."""
    return Task(
        description=f"""
        Based on the LinkedIn and company research, analyze potential pain points for:
        
        Prospect: {prospect.full_name or prospect.linkedin_username}
        Role: {prospect.headline or 'Unknown'}
        Company: {prospect.company_name or 'Unknown'}
        
        Consider:
        1. Common challenges for their role/seniority level
        2. Industry-specific pain points
        3. Company stage challenges (startup vs enterprise)
        4. Recent company developments that might create urgency
        5. Technology or process gaps based on job postings
        
        Rank pain points by:
        - Intensity (how painful is this problem?)
        - Relevance (how relevant is our solution?)
        - Urgency (is there a trigger event?)
        """,
        expected_output="""A prioritized list of pain points including:
        - Top 3-5 pain points with descriptions
        - Intensity score (1-10) for each
        - Evidence/reasoning for each pain point
        - Potential trigger events or urgency factors""",
        agent=agent,
        context=[linkedin_research, company_research],
    )


def create_talking_points_task(
    agent: Agent,
    prospect: ProspectInput,
    linkedin_research: Task,
    company_research: Task,
    pain_point_analysis: Task,
) -> Task:
    """Task to generate personalized talking points."""
    return Task(
        description=f"""
        Generate personalized talking points for outreach to:
        
        Prospect: {prospect.full_name or prospect.linkedin_username}
        
        Create talking points that:
        1. Reference specific details from their LinkedIn profile
        2. Acknowledge recent company developments
        3. Address identified pain points naturally
        4. Provide value before asking for anything
        5. Feel personal, not templated
        
        Generate 3-5 talking points, each with:
        - The talking point itself
        - Why it's relevant (the research backing it)
        - How to naturally transition to your value prop
        """,
        expected_output="""3-5 personalized talking points, each including:
        - The talking point/conversation starter
        - Supporting research/evidence
        - Suggested transition to value proposition
        - Tone recommendation (casual, professional, etc.)""",
        agent=agent,
        context=[linkedin_research, company_research, pain_point_analysis],
    )


def create_icp_scoring_task(
    agent: Agent,
    prospect: ProspectInput,
    product_context: str,
    linkedin_research: Task,
    company_research: Task,
    pain_point_analysis: Task,
) -> Task:
    """Task to score prospect against ICP criteria."""
    return Task(
        description=f"""
        Score this prospect against the Ideal Customer Profile:
        
        Prospect: {prospect.full_name or prospect.linkedin_username}
        
        Product/ICP Context:
        {product_context}
        
        Score on these dimensions (0-100):
        1. Overall ICP Fit - How well do they match the ideal customer?
        2. Problem Intensity - How much do they need this solution?
        3. Relevance - How relevant is the product to their role/company?
        4. Likelihood to Respond - Based on their activity and engagement patterns
        
        Provide reasoning for each score.
        """,
        expected_output="""ICP scoring report with:
        - Overall score (0-100) with reasoning
        - Problem intensity score (0-100) with reasoning
        - Relevance score (0-100) with reasoning
        - Likelihood to respond score (0-100) with reasoning
        - Final recommendation (pursue/nurture/skip)""",
        agent=agent,
        context=[linkedin_research, company_research, pain_point_analysis],
    )
