"""
Email templates for outreach campaigns
"""

from air1.services.browser.email import EmailTemplate


# Template functions
def get_meeting_subject(recipient_name: str) -> str:
    """Generate meeting subject line"""
    return f"{recipient_name} x Ali - Meeting"

def get_engineering_subject() -> str:
    """Generate engineering subject line"""
    return "Engineering - Ali Abbassi"


# Template constants for common outreach scenarios
DEFAULT_COLD_OUTREACH_EMAIL = """
Hi {{name}},

I'm a senior backend engineer with 4 years of work experience at Anghami and OSN, the biggest streaming platforms in the middle east, as a part of their early teams where I helped scale throughput of ingestion pipelines and platform apis to millions of users (30M+). Being a part of super lean teams, one of my strongest suits has been the ability to work across the stack from building cost efficient and scalable backend systems to high throughput data ingestion pipelines to prod ready frontend components.

Let's chat?

Ali Abbassi
alialabbassi2001@gmail.com
Beirut, Lebanon
linkedin.com/in/alialabbassi/
hoopaudio.com
resume https: //docs.google. com/document/d/1zQWErF7AZgEokh7pE76VY_MK3aBwTKLwXzBhn3X2Ig8/edit?usp=sharing

---
If you'd prefer not to receive these emails, please reply with "unsubscribe".
"""

DEFAULT_COLD_OUTREACH_TEMPLATE = EmailTemplate(
    subject=get_engineering_subject(),
    content=DEFAULT_COLD_OUTREACH_EMAIL
)