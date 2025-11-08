from pydantic import BaseModel


class LinkedinProfile(BaseModel):
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    email: str = ""
    phone_number: str = ""
    location: str = ""
    headline: str = ""

    def isTalent(self):
        return self.headline.find("talent")


class CompanyPeople(BaseModel):
    profile_ids: set[str]
