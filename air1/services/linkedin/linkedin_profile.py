from pydantic import BaseModel


class LinkedinProfile(BaseModel):
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    email: str = ""
    phone_number: str = ""
    linkedin_url: str = ""
    location: str = ""
    headline: str = ""
    about: str = ""
    lead_id: str = ""

    def isTalent(self):
        recruiter_keywords = [
            "recruiter",
            "talent",
            "recruitment",
            "sdr",
            "sourcer",
            "headhunter",
            "hr",
            "placing",
            "growth",
            "organization",
        ]
        headline_lower = self.headline.lower()
        return any(keyword in headline_lower for keyword in recruiter_keywords)

    # engineering managers, techleads, leads in general, founders, and ceos
    def isLeader(self):
        leader_keywords = [
            "engineering manager",
            "tech lead",
            "lead",
            "founder",
            "ceo",
            "cto",
            "vp",
            "director",
            "head of",
            "chief",
        ]
        headline_lower = self.headline.lower()
        return any(keyword in headline_lower for keyword in leader_keywords)

    # software engineers up to senior.
    def isEngineer(self):
        engineer_keywords = [
            "software engineer",
            "developer",
            "programmer",
            "backend",
            "frontend",
            "fullstack",
            "full-stack",
            "engineer",
            "swe",
        ]
        headline_lower = self.headline.lower()
        return any(keyword in headline_lower for keyword in engineer_keywords)


class CompanyPeople(BaseModel):
    profile_ids: set[str]


class Lead(BaseModel):
    first_name: str = ""
    full_name: str = ""
    email: str = ""
    phone_number: str = ""
