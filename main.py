import datetime

import discord
from typing import List, Tuple, Dict
import auth
import time

client = discord.Client()
audit_channel: discord.TextChannel = None
main_guild: discord.Guild = None


async def check_audit_log() -> bool:
    audits = await main_guild.audit_logs(limit=1).flatten()
    for audit in audits:
        if datetime.datetime.utcnow() - audit.created_at > datetime.timedelta(
            seconds=3
        ):
            break
        the_date = datetime.datetime.fromtimestamp(time.time()).strftime(
            "%H:%M, %A %d %B %Y"
        )
        message = ["ㅤㅤ\n[" + the_date + "]\n"]
        instigator = audit.user
        affected = audit.target
        hit = False
        if audit.action.name == "member_update":
            for prev_data in audit.before:
                for next_data in audit.after:
                    prev_key, prev_val = prev_data
                    next_key, next_val = next_data
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
        if audit.action.name == "member_move":
            print()  # TODO
        if hit:
            await audit_channel.send("".join(message) + "\nㅤㅤ")
        return hit


async def diff_voice(
    before: discord.VoiceState,
    after: discord.VoiceState,
    trigger: bool,
    embed_data: Dict,
    field_data: Dict,
) -> Tuple[bool, Dict, Dict]:
    prev_voice = before.channel
    next_voice = after.channel
    if prev_voice != next_voice:
        if prev_voice is None:
            embed_data["title"] = "User Join"
            embed_data["color"] = 0x00FF00
            field_data["value"] = next_voice.name
        elif next_voice is None:
            embed_data["title"] = "User Left"
            embed_data["color"] = 0xFF0000
            field_data["value"] = prev_voice.name
        elif prev_voice is not None and next_voice is not None:
            embed_data["title"] = "User Moved"
            embed_data["color"] = 0x00FFFF
            field_data["value"] = prev_voice.name + " ➡ " + next_voice.name
        trigger = True
    return trigger, embed_data, field_data


@client.event
async def on_voice_state_update(
    member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
):
    the_date = datetime.datetime.fromtimestamp(time.time()).strftime(
        "%H:%M, %A %d %B %Y"
    )
    trigger = False
    await check_audit_log()

    embed_dict = {}
    field_dict = {}
    trigger, embed_dict, field_dict = await diff_voice(
        before, after, trigger, embed_dict, field_dict
    )

    if trigger:
        voice_embed = discord.Embed(**embed_dict)
        voice_embed.add_field(name=member.name, **field_dict)
        voice_embed.set_footer(text=the_date)
        await audit_channel.send(embed=voice_embed)


@client.event
async def on_ready():
    global audit_channel
    global main_guild
    for guild in client.guilds:
        if guild.name == auth.SERVER_NAME:
            main_guild = guild
    for channel in main_guild.channels:
        if channel.name == "voice-logs":
            audit_channel = channel
    print("ready.")


if __name__ == "__main__":
    client.run(auth.TOKEN)
