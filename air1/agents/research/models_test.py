"""Unit tests for research agent models."""

import pytest
from pydantic import ValidationError

from air1.agents.research.models import (
    ProspectInput,
    PainPoint,
    TalkingPoint,
    ICPProfile,
    ICPScore,
    LinkedInActivity,
    CompanyIntelligence,
    AISummary,
    ResearchOutput,
)


class TestProspectInput:
    """Tests for ProspectInput model."""

    def test_minimal_prospect(self):
        """Test creating prospect with only required field."""
        prospect = ProspectInput(linkedin_username="johndoe")
        assert prospect.linkedin_username == "johndoe"
        assert prospect.full_name is None
        assert prospect.headline is None
        assert prospect.company_name is None
        assert prospect.location is None

    def test_full_prospect(self):
        """Test creating prospect with all fields."""
        prospect = ProspectInput(
            linkedin_username="johndoe",
            full_name="John Doe",
            headline="VP of Sales at Acme",
            company_name="Acme Inc",
            location="San Francisco, CA",
        )
        assert prospect.linkedin_username == "johndoe"
        assert prospect.full_name == "John Doe"
        assert prospect.headline == "VP of Sales at Acme"
        assert prospect.company_name == "Acme Inc"
        assert prospect.location == "San Francisco, CA"

    def test_missing_required_field(self):
        """Test that missing linkedin_username raises error."""
        with pytest.raises(ValidationError):
            ProspectInput()


class TestPainPoint:
    """Tests for PainPoint model."""

    def test_valid_pain_point(self):
        """Test creating valid pain point."""
        pp = PainPoint(
            description="Struggling with lead generation",
            intensity=8,
            evidence="Job posting mentions need for more leads",
        )
        assert pp.description == "Struggling with lead generation"
        assert pp.intensity == 8
        assert pp.urgency_trigger is None

    def test_pain_point_with_urgency(self):
        """Test pain point with urgency trigger."""
        pp = PainPoint(
            description="Need to scale sales team",
            intensity=9,
            evidence="Recent funding round",
            urgency_trigger="Series B funding announced",
        )
        assert pp.urgency_trigger == "Series B funding announced"

    def test_intensity_bounds(self):
        """Test intensity must be between 1-10."""
        with pytest.raises(ValidationError):
            PainPoint(description="Test", intensity=0, evidence="Test")
        
        with pytest.raises(ValidationError):
            PainPoint(description="Test", intensity=11, evidence="Test")

    def test_valid_intensity_bounds(self):
        """Test valid intensity at boundaries."""
        pp1 = PainPoint(description="Test", intensity=1, evidence="Test")
        pp10 = PainPoint(description="Test", intensity=10, evidence="Test")
        assert pp1.intensity == 1
        assert pp10.intensity == 10


class TestTalkingPoint:
    """Tests for TalkingPoint model."""

    def test_valid_talking_point(self):
        """Test creating valid talking point."""
        tp = TalkingPoint(
            point="I noticed you recently posted about AI in sales",
            research_backing="LinkedIn post from last week",
            value_transition="Our tool helps automate that process",
        )
        assert tp.tone == "professional"  # default

    def test_custom_tone(self):
        """Test talking point with custom tone."""
        tp = TalkingPoint(
            point="Hey, saw your post!",
            research_backing="Recent LinkedIn activity",
            value_transition="We should chat",
            tone="casual",
        )
        assert tp.tone == "casual"


class TestICPProfile:
    """Tests for ICPProfile model."""

    def test_default_icp_profile(self):
        """Test creating ICP profile with defaults."""
        icp = ICPProfile()
        assert icp.target_titles == []
        assert icp.target_industries == []
        assert icp.product_description == ""

    def test_full_icp_profile(self):
        """Test creating ICP profile with all fields."""
        icp = ICPProfile(
            target_titles=["VP Sales", "Head of Sales"],
            target_industries=["SaaS", "FinTech"],
            target_company_sizes=["51-200", "201-500"],
            target_seniority=["VP", "Director"],
            pain_points_we_solve=["Manual lead qualification", "Low response rates"],
            value_proposition="Automate your outbound sales",
            product_description="AI-powered sales automation",
            disqualifiers=["Company size < 10", "Non-B2B"],
        )
        assert len(icp.target_titles) == 2
        assert "SaaS" in icp.target_industries
        assert len(icp.disqualifiers) == 2


class TestICPScore:
    """Tests for ICPScore model."""

    def test_valid_icp_score(self):
        """Test creating valid ICP score."""
        score = ICPScore(
            overall=85,
            problem_intensity=90,
            relevance=80,
            likelihood_to_respond=75,
            reasoning="Strong fit based on role and company stage",
        )
        assert score.overall == 85
        assert score.recommendation == "pursue"  # computed from tier

    def test_score_bounds(self):
        """Test scores must be between 0-100."""
        with pytest.raises(ValidationError):
            ICPScore(
                overall=-1,
                problem_intensity=50,
                relevance=50,
                likelihood_to_respond=50,
                reasoning="Test",
            )
        
        with pytest.raises(ValidationError):
            ICPScore(
                overall=101,
                problem_intensity=50,
                relevance=50,
                likelihood_to_respond=50,
                reasoning="Test",
            )

    def test_valid_score_bounds(self):
        """Test valid scores at boundaries."""
        score = ICPScore(
            overall=0,
            problem_intensity=100,
            relevance=0,
            likelihood_to_respond=100,
            reasoning="Test",
        )
        assert score.overall == 0
        assert score.problem_intensity == 100

    def test_tier_1_hot(self):
        """Test tier 1 (hot) for high scores >= 70."""
        score = ICPScore(
            overall=85,
            problem_intensity=90,
            relevance=80,
            likelihood_to_respond=75,
            reasoning="Strong fit",
        )
        assert score.tier == 1
        assert score.tier_label == "hot"
        assert score.recommendation == "pursue"

    def test_tier_2_warm(self):
        """Test tier 2 (warm) for scores 40-69."""
        score = ICPScore(
            overall=55,
            problem_intensity=60,
            relevance=50,
            likelihood_to_respond=50,
            reasoning="Moderate fit",
        )
        assert score.tier == 2
        assert score.tier_label == "warm"
        assert score.recommendation == "nurture"

    def test_tier_3_cold(self):
        """Test tier 3 (cold) for low scores < 40."""
        score = ICPScore(
            overall=25,
            problem_intensity=30,
            relevance=20,
            likelihood_to_respond=20,
            reasoning="Poor fit",
        )
        assert score.tier == 3
        assert score.tier_label == "cold"
        assert score.recommendation == "skip"

    def test_tier_boundaries(self):
        """Test tier boundaries at exact thresholds."""
        # Exactly 70 should be tier 1
        score_70 = ICPScore(
            overall=70, problem_intensity=70, relevance=70,
            likelihood_to_respond=70, reasoning="Test"
        )
        assert score_70.tier == 1
        
        # Exactly 69 should be tier 2
        score_69 = ICPScore(
            overall=69, problem_intensity=70, relevance=70,
            likelihood_to_respond=70, reasoning="Test"
        )
        assert score_69.tier == 2
        
        # Exactly 40 should be tier 2
        score_40 = ICPScore(
            overall=40, problem_intensity=40, relevance=40,
            likelihood_to_respond=40, reasoning="Test"
        )
        assert score_40.tier == 2
        
        # Exactly 39 should be tier 3
        score_39 = ICPScore(
            overall=39, problem_intensity=40, relevance=40,
            likelihood_to_respond=40, reasoning="Test"
        )
        assert score_39.tier == 3

    def test_match_criteria(self):
        """Test ICP match criteria fields."""
        score = ICPScore(
            overall=85,
            problem_intensity=90,
            relevance=80,
            likelihood_to_respond=75,
            reasoning="Strong fit",
            title_match=True,
            industry_match=True,
            company_size_match=False,
            seniority_match=True,
        )
        assert score.title_match is True
        assert score.industry_match is True
        assert score.company_size_match is False
        assert score.seniority_match is True


class TestLinkedInActivity:
    """Tests for LinkedInActivity model."""

    def test_default_values(self):
        """Test default values."""
        activity = LinkedInActivity()
        assert activity.recent_posts == []
        assert activity.engagement_topics == []
        assert activity.posting_frequency == "unknown"
        assert activity.engagement_style == "unknown"

    def test_with_data(self):
        """Test with actual data."""
        activity = LinkedInActivity(
            recent_posts=["Post about AI", "Post about sales"],
            engagement_topics=["AI", "Sales", "Leadership"],
            posting_frequency="weekly",
            engagement_style="comments and shares",
        )
        assert len(activity.recent_posts) == 2
        assert "AI" in activity.engagement_topics


class TestCompanyIntelligence:
    """Tests for CompanyIntelligence model."""

    def test_minimal_company(self):
        """Test with only required field."""
        company = CompanyIntelligence(company_name="Acme Inc")
        assert company.company_name == "Acme Inc"
        assert company.industry is None
        assert company.recent_news == []

    def test_full_company(self):
        """Test with all fields."""
        company = CompanyIntelligence(
            company_name="Acme Inc",
            industry="SaaS",
            size="51-200",
            recent_funding="Series B - $50M",
            recent_news=["Launched new product", "Expanded to Europe"],
            hiring_signals=["Hiring 10 sales reps"],
            growth_indicators=["Revenue doubled YoY"],
        )
        assert company.size == "51-200"
        assert len(company.recent_news) == 2


class TestAISummary:
    """Tests for AISummary model."""

    def test_minimal_summary(self):
        """Test with only required fields."""
        summary = AISummary(
            prospect_summary="John is a VP of Sales with 10 years experience.",
            company_summary="Acme Inc is a B2B SaaS company.",
            relevancy_to_you="Strong fit for our sales automation tool.",
        )
        assert summary.prospect_summary.startswith("John")
        assert summary.notable_achievements_current_role == []
        assert summary.recommended_approach == ""

    def test_full_summary(self):
        """Test with all fields."""
        summary = AISummary(
            prospect_summary="John is a VP of Sales with 10 years experience.",
            company_summary="Acme Inc is a B2B SaaS company.",
            notable_achievements_current_role=[
                "Grew team from 5 to 25",
                "Increased revenue 3x",
            ],
            other_notable_achievements=[
                "Founded previous startup",
                "Speaker at SaaStr",
            ],
            relevancy_to_you="Strong fit for our sales automation tool.",
            key_talking_points=[
                "Recent team growth",
                "AI adoption interest",
            ],
            potential_pain_points=[
                "Scaling sales processes",
                "Lead qualification",
            ],
            recommended_approach="Warm outreach via LinkedIn, reference their recent post about AI.",
        )
        assert len(summary.notable_achievements_current_role) == 2
        assert len(summary.key_talking_points) == 2


class TestResearchOutput:
    """Tests for ResearchOutput model."""

    def test_minimal_output(self):
        """Test with only required field."""
        prospect = ProspectInput(linkedin_username="johndoe")
        output = ResearchOutput(prospect=prospect)
        
        assert output.prospect.linkedin_username == "johndoe"
        assert output.ai_summary is None
        assert output.pain_points == []
        assert output.raw_research == {}

    def test_full_output(self):
        """Test with all fields populated."""
        prospect = ProspectInput(
            linkedin_username="johndoe",
            full_name="John Doe",
            company_name="Acme Inc",
        )
        
        ai_summary = AISummary(
            prospect_summary="John is a leader.",
            company_summary="Acme is growing.",
            relevancy_to_you="Good fit.",
        )
        
        output = ResearchOutput(
            prospect=prospect,
            ai_summary=ai_summary,
            pain_points=[
                PainPoint(
                    description="Scaling issues",
                    intensity=8,
                    evidence="Job postings",
                )
            ],
            talking_points=[
                TalkingPoint(
                    point="Your recent post",
                    research_backing="LinkedIn",
                    value_transition="We can help",
                )
            ],
            icp_score=ICPScore(
                overall=85,
                problem_intensity=90,
                relevance=80,
                likelihood_to_respond=75,
                reasoning="Strong fit",
            ),
            raw_research={"crew_output": "test output"},
        )
        
        assert output.ai_summary is not None
        assert len(output.pain_points) == 1
        assert output.icp_score.overall == 85
