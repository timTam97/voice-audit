import datetime
from math import floor
from typing import Dict, Tuple

import discord

import auth

client = discord.Client()
audit_channel: discord.TextChannel = None
main_guild: discord.Guild = None
member_time: Dict = {}


async def check_audit_log() -> None:
    audit = (await main_guild.audit_logs(limit=1).flatten())[0]
    if datetime.datetime.utcnow() - audit.created_at > datetime.timedelta(seconds=3):
        return
    the_date = datetime.datetime.now().strftime("%H:%M, %A %d %B %Y")
    message = ["\u3164\n[" + the_date + "]\n"]
    instigator = audit.user
    affected = audit.target
    hit = False
    if audit.action.name == "member_update":
        for prev_key, prev_val in audit.before:
            for next_key, next_val in audit.after:
                if prev_key == "mute" and next_key == "mute":
                    if prev_val and not next_val:
                        message.append(
                            "**{}** was un-server muted by **{}**".format(
                                affected, instigator
                            )
                        )
                        hit = True
                    elif not prev_val and next_val:
                        message.append(
                            "**{}** was server muted by **{}**".format(
                                affected, instigator
                            )
                        )
                        hit = True
                elif prev_key == "deaf" and next_key == "deaf":
                    if prev_val and not next_val:
                        message.append(
                            "**{}** was un-server deafened by **{}**".format(
                                affected, instigator
                            )
                        )
                        hit = True
                    elif not prev_val and next_val:
                        message.append(
                            "**{}** was server deafened by **{}**".format(
                                affected, instigator
                            )
                        )
                        hit = True
    if hit:
        await audit_channel.send("".join(message) + "\n\u3164")


async def diff_voice(
    before: discord.VoiceState,
    after: discord.VoiceState,
) -> Tuple[bool, bool, bool, dict, dict]:
    global member_time
    prev_voice = before.channel
    next_voice = after.channel
    trigger = False
    join = False
    leave = False
    embed_data = {}
    field_data = {}
    if prev_voice != next_voice:
        if prev_voice is None:
            embed_data["title"] = "User Join"
            embed_data["color"] = 0x00FF00
            field_data["value"] = next_voice.name
            join = True
        elif next_voice is None:
            embed_data["title"] = "User Left"
            embed_data["color"] = 0xFF0000
            field_data["value"] = prev_voice.name
            leave = True
        elif prev_voice is not None and next_voice is not None:
            embed_data["title"] = "User Moved"
            embed_data["color"] = 0x00FFFF
            field_data["value"] = prev_voice.name + " ➡ " + next_voice.name
        trigger = True
    return trigger, join, leave, embed_data, field_data


@client.event
async def on_voice_state_update(
    member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
):
    await check_audit_log()
    trigger, join, leave, embed_dict, field_dict = await diff_voice(
        before, after
    )
    if trigger:
        the_date = datetime.datetime.now().strftime("%H:%M, %A %d %B %Y")
        member_count = sum(
            map(
                lambda x: len(x),
                [channel.members for channel in main_guild.voice_channels],
            )
        )
        update = "{}\n{} in all voice channels".format(the_date, member_count)
        if join:
            member_time[str(member)] = datetime.datetime.now()
        elif leave:
            join_time = member_time.get(str(member))
            if join_time is not None:
                delta = datetime.timedelta(
                    seconds=floor((datetime.datetime.now() - join_time).total_seconds())
                )
                update += "\nDuration: {}".format(delta)
        await audit_channel.send(
            embed=discord.Embed(**embed_dict)
            .add_field(**field_dict, name=member.name)
            .set_footer(text=update)
        )


@client.event
async def on_ready():
    global audit_channel
    global main_guild
    for guild in client.guilds:
        if guild.name == auth.SERVER_NAME:
            main_guild = guild
    for channel in main_guild.channels:
        if channel.name == auth.BOT_CHANNEL:
            audit_channel = channel
    print("Logged in as {0.user} and bound to #{1.name}".format(client, audit_channel))


if __name__ == "__main__":
    client.run(auth.TOKEN)
