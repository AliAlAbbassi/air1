import asyncio

from air1.services.outreach.service import Service
from air1.services.outreach.templates import DEFAULT_COLD_CONNECTION_NOTE


async def connect_with_profiles_workflow(
    profile_usernames: list[str], message_note
) -> bool:
    async with Service() as service:
        for profile_username in profile_usernames:
            ok = service.send_connection_request(
                profile_username=profile_username, message_note=message_note
            )
            if ok is not True:
                return ok

    return True


def run():
    asyncio.run(
        connect_with_profiles_workflow(
            profile_usernames=["suneeta-patel-326359140"],
            message_note=DEFAULT_COLD_CONNECTION_NOTE,
        )
    )


run()
