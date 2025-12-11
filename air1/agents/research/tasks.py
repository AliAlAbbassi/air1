"""Tasks for research prospecting agents."""

from crewai import Task, Agent

from air1.agents.research.models import ProspectInput, ICPProfile


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
    icp_profile: ICPProfile,
    linkedin_research: Task,
    company_research: Task,
    pain_point_analysis: Task,
) -> Task:
    """Task to score prospect against ICP criteria."""
    icp_details = f"""
    TARGET TITLES: {', '.join(icp_profile.target_titles) or 'Not specified'}
    TARGET INDUSTRIES: {', '.join(icp_profile.target_industries) or 'Not specified'}
    TARGET COMPANY SIZES: {', '.join(icp_profile.target_company_sizes) or 'Not specified'}
    TARGET SENIORITY: {', '.join(icp_profile.target_seniority) or 'Not specified'}
    PAIN POINTS WE SOLVE: {', '.join(icp_profile.pain_points_we_solve) or 'Not specified'}
    VALUE PROPOSITION: {icp_profile.value_proposition or 'Not specified'}
    PRODUCT: {icp_profile.product_description or 'Not specified'}
    DISQUALIFIERS: {', '.join(icp_profile.disqualifiers) or 'None'}
    """
    
    return Task(
        description=f"""
        Score this prospect against the Ideal Customer Profile (ICP):
        
        PROSPECT:
        - Name: {prospect.full_name or prospect.linkedin_username}
        - Headline: {prospect.headline or 'Unknown'}
        - Company: {prospect.company_name or 'Unknown'}
        
        ICP CRITERIA:
        {icp_details}
        
        Score on these dimensions:
        1. Title Match (Yes/No): Does their title match target titles?
        2. Industry Match (Yes/No): Is their company in a target industry?
        3. Company Size Match (Yes/No): Does company size match?
        4. Seniority Match (Yes/No): Does seniority level match?
        5. Overall ICP Fit (0-100): How well do they match overall?
        6. Problem Intensity (0-100): How much do they need our solution?
        7. Relevance (0-100): How relevant is our product to their role?
        8. Likelihood to Respond (0-100): Based on their activity patterns
        
        Check for DISQUALIFIERS - if any apply, recommend "skip".
        
        Recommendation: "pursue" (>=70), "nurture" (40-69), or "skip" (<40)
        """,
        expected_output="""ICP scoring report with:
        - Title Match: Yes/No
        - Industry Match: Yes/No
        - Company Size Match: Yes/No
        - Seniority Match: Yes/No
        - Overall: X/100 with reasoning
        - Problem Intensity: X/100 with reasoning
        - Relevance: X/100 with reasoning
        - Likelihood to Respond: X/100 with reasoning
        - Recommendation: pursue/nurture/skip""",
        agent=agent,
        context=[linkedin_research, company_research, pain_point_analysis],
    )


def create_ai_summary_task(
    agent: Agent,
    prospect: ProspectInput,
    icp_profile: ICPProfile,
    linkedin_research: Task,
    company_research: Task,
    pain_point_analysis: Task,
) -> Task:
    """
    Task to generate the comprehensive AI Summary.
    
    This is the main output that provides deep prospect insights for
    sales meetings, email sequences, and phone calls.
    """
    return Task(
        description=f"""
        Generate a comprehensive AI Summary for this prospect:
        
        Prospect: {prospect.full_name or prospect.linkedin_username}
        LinkedIn: {prospect.linkedin_username}
        Current Role: {prospect.headline or 'Unknown'}
        Company: {prospect.company_name or 'Unknown'}
        
        Our Product: {icp_profile.product_description or 'B2B solution'}
        Value Proposition: {icp_profile.value_proposition or 'Not specified'}
        Pain Points We Solve: {', '.join(icp_profile.pain_points_we_solve) or 'Not specified'}
        
        Create a summary with these sections:
        
        1. PROSPECT SUMMARY
        Write a comprehensive 2-3 paragraph summary of who this person is professionally.
        Include their career trajectory, current focus, and professional identity.
        
        2. COMPANY SUMMARY  
        Write a summary of their current company - what it does, its market position,
        recent developments, and any relevant context for sales.
        
        3. NOTABLE ACHIEVEMENTS IN CURRENT ROLE
        List 3-5 specific achievements or responsibilities in their current position.
        Be specific - reference actual projects, metrics, or initiatives if available.
        
        4. OTHER NOTABLE ACHIEVEMENTS
        List 3-5 achievements from earlier in their career that demonstrate their
        expertise, leadership, or relevance to our solution.
        
        5. RELEVANCY TO YOU
        Explain specifically why this prospect is relevant to our product/company.
        Connect their role, challenges, and company situation to our value proposition.
        
        6. KEY TALKING POINTS
        List 3-5 specific talking points for outreach based on the research.
        
        7. POTENTIAL PAIN POINTS
        List the top pain points our solution could address for them.
        
        8. RECOMMENDED APPROACH
        Suggest the best approach for reaching out (tone, channel, timing, angle).
        """,
        expected_output="""A comprehensive AI Summary with all sections:
        
        PROSPECT SUMMARY: [2-3 paragraphs about the person]
        
        COMPANY SUMMARY: [1-2 paragraphs about their company]
        
        NOTABLE ACHIEVEMENTS IN CURRENT ROLE:
        - [Achievement 1]
        - [Achievement 2]
        - [Achievement 3]
        
        OTHER NOTABLE ACHIEVEMENTS:
        - [Achievement 1]
        - [Achievement 2]
        - [Achievement 3]
        
        RELEVANCY TO YOU: [1-2 paragraphs on why they're a good prospect]
        
        KEY TALKING POINTS:
        - [Talking point 1]
        - [Talking point 2]
        - [Talking point 3]
        
        POTENTIAL PAIN POINTS:
        - [Pain point 1]
        - [Pain point 2]
        - [Pain point 3]
        
        RECOMMENDED APPROACH: [Specific recommendation for outreach]""",
        agent=agent,
        context=[linkedin_research, company_research, pain_point_analysis],
    )
