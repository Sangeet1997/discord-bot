import time
from dataclasses import dataclass

from discord import Member, VoiceState
from discord.channel import VocalGuildChannel
from discord.ext import commands


@dataclass
class VoiceSession:
    joined_at: float
    channel_id: int
    channel_name: str
    server_name: str
    paused_at: float | None = None
    paused_seconds: float = 0.0


active_sessions: dict[int, VoiceSession] = {}


def is_deafened(state: VoiceState | None) -> bool:
    return state is not None and (state.self_deaf or state.deaf)


def start_session(
    member: Member,
    channel: VocalGuildChannel,
    paused: bool = False,
) -> None:
    now = time.monotonic()
    active_sessions[member.id] = VoiceSession(
        joined_at=now,
        channel_id=channel.id,
        channel_name=channel.name,
        server_name=channel.guild.name,
        paused_at=now if paused else None,
    )


def finish_session(member: Member, session: VoiceSession) -> None:
    now = time.monotonic()
    paused_seconds = session.paused_seconds
    if session.paused_at is not None:
        paused_seconds += now - session.paused_at

    duration_seconds = max(0.0, now - session.joined_at - paused_seconds)
    duration_minutes = round(duration_seconds / 60, 2)
    print(
        f"User {member.name} stayed in {session.server_name} / "
        f"{session.channel_name} (ID: {session.channel_id}) "
        f"for {duration_minutes} minutes."
    )


async def on_voice_state_update(
    member: Member,
    before: VoiceState,
    after: VoiceState,
) -> None:
    if member.bot:
        return

    previous_channel = before.channel
    current_channel = after.channel
    session = active_sessions.get(member.id)

    if previous_channel is None and current_channel is not None:
        start_session(member, current_channel, is_deafened(after))
    elif previous_channel is not None and current_channel is None:
        if session is not None:
            active_sessions.pop(member.id, None)
            finish_session(member, session)
    elif (
        previous_channel is not None
        and current_channel is not None
        and previous_channel.id != current_channel.id
    ):
        if session is not None:
            active_sessions.pop(member.id, None)
            finish_session(member, session)
        start_session(member, current_channel, is_deafened(after))
    elif session is not None and is_deafened(before) != is_deafened(after):
        now = time.monotonic()
        if is_deafened(after):
            session.paused_at = now
        elif session.paused_at is not None:
            session.paused_seconds += now - session.paused_at
            session.paused_at = None


async def setup(bot: commands.Bot) -> None:
    bot.add_listener(on_voice_state_update)
