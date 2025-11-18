"""
email.py will have subjects and content templates 

for example 
def get_meeting_with(recipent_name: str) -> str:
    return recipent_name + " x Ali - Meeting"

DEFAULT_COLD_OUTREACH_EMAIL: str

i don't know how would you attach my resume, but do that 
"""
def send_email(self, subject: str, recipients: dict[str], content: str, attachements):
    pass


"""
everything from earlier can be saved into a template. prbbly use a default temp, or a set of available templates that come up. 
"""
def send_outreach_emails(self, leads, template):
    pass


""" 
so basically you were right earlier, have a basic ass send_email that can mimics gmail's api and then have that send_outreach_emails function to send template emails. 

we will implement the gmail like api function later, I don't really give a shit about it for now.
""" 