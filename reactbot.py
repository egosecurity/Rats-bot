import discord
from discord.ext import commands
import json
import os
import asyncio
import random

TOKEN = 'TOKEN'
DATA_FILE = 'botdata.json'

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# load and initialize data
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"user_emojis": {}, "command_users": [], "command_roles": [], "mock_targets": {}}
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ botdata.json is corrupted. Resetting to default.")
            return {"user_emojis": {}, "command_users": [], "command_roles": [], "mock_targets": {}}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

data = load_data()
mock_reply_map = {} 

# check perms
def is_authorized(ctx):
    if ctx.author.id in data["command_users"]:
        return True
    if any(role.id in data["command_roles"] for role in ctx.author.roles):
        return True
    return False

# emoji based cmds
@bot.command()
async def addemoji(ctx, user: discord.User, emoji):
    if not is_authorized(ctx): return
    uid = str(user.id)
    if uid not in data["user_emojis"]:
        data["user_emojis"][uid] = []
    if emoji not in data["user_emojis"][uid]:
        data["user_emojis"][uid].append(emoji)
        save_data()
        await ctx.send(f"✅ Added {emoji} for {user.display_name}.")

@bot.command()
async def removeemoji(ctx, user: discord.User, emoji):
    if not is_authorized(ctx): return
    uid = str(user.id)
    if uid in data["user_emojis"] and emoji in data["user_emojis"][uid]:
        data["user_emojis"][uid].remove(emoji)
        save_data()
        await ctx.send(f"❌ Removed {emoji} from {user.display_name}.")

@bot.command()
async def listemojis(ctx, user: discord.User):
    if not is_authorized(ctx): return
    uid = str(user.id)
    emojis = data["user_emojis"].get(uid, [])
    await ctx.send(f"Emojis for {user.display_name}: {' '.join(emojis) if emojis else 'None'}")

# mock based cmds
@bot.command()
async def setmock(ctx, user: discord.User, mode: int):
    if not is_authorized(ctx): return
    if mode not in (1, 2, 3):
        await ctx.send("❌ Invalid mode. Use 1 (copy), 2 (alternating caps), 3 (leetspeak)")
        return
    data["mock_targets"][str(user.id)] = mode
    save_data()
    await ctx.send(f"🧠 Now mocking {user.display_name} with mode {mode}.")

@bot.command()
async def removemock(ctx, user: discord.User):
    if not is_authorized(ctx): return
    uid = str(user.id)
    if uid in data["mock_targets"]:
        del data["mock_targets"][uid]
        save_data()
        await ctx.send(f"🧹 Stopped mocking {user.display_name}.")

@bot.command()
async def listmocks(ctx):
    if not is_authorized(ctx): return
    lines = [f"<@{uid}>: mode {mode}" for uid, mode in data["mock_targets"].items()]
    await ctx.send("\n".join(lines) if lines else "No users are currently being mocked.")

# whitelist cmds
@bot.command()
async def allowuser(ctx, user_id: int):
    if ctx.author.id not in data["command_users"]:
        return
    if user_id not in data["command_users"]:
        data["command_users"].append(user_id)
        save_data()
        await ctx.send(f"✅ Allowed user <@{user_id}>.")

@bot.command()
async def removeuser(ctx, user_id: int):
    if ctx.author.id not in data["command_users"]:
        return
    if user_id in data["command_users"]:
        data["command_users"].remove(user_id)
        save_data()
        await ctx.send(f"❌ Removed user <@{user_id}>.")

@bot.command()
async def allowrole(ctx, role_id: int):
    if ctx.author.id not in data["command_users"]:
        return
    if role_id not in data["command_roles"]:
        data["command_roles"].append(role_id)
        save_data()
        await ctx.send(f"✅ Allowed role `{role_id}`.")

@bot.command()
async def removerole(ctx, role_id: int):
    if ctx.author.id not in data["command_users"]:
        return
    if role_id in data["command_roles"]:
        data["command_roles"].remove(role_id)
        save_data()
        await ctx.send(f"❌ Removed role `{role_id}`.")

@bot.command()
async def showwhitelist(ctx):
    if not is_authorized(ctx): return
    users = [f"<@{uid}>" for uid in data["command_users"]]
    roles = [f"`{rid}`" for rid in data["command_roles"]]
    await ctx.send(f"**Whitelisted Users:** {' '.join(users) or 'None'}\n**Whitelisted Roles:** {' '.join(roles) or 'None'}")

# purge cmds
@bot.command()
async def purge(ctx, amount: int):
    if not is_authorized(ctx): return
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 Deleted {len(deleted)} messages.", delete_after=5)

@bot.command()
async def pure(ctx, user: discord.User, amount: int):
    if not is_authorized(ctx): return
    def is_target(m): return m.author.id == user.id
    deleted = await ctx.channel.purge(limit=1000, check=is_target, bulk=True)
    await ctx.send(f"🧼 Deleted {len(deleted[:amount])} messages from {user.display_name}.", delete_after=5)

# mocking functionality
def mock_text(text, mode):
    if mode == 1:
        return text
    elif mode == 2:
        return ''.join(c.upper() if i % 2 else c.lower() for i, c in enumerate(text))
    elif mode == 3:
        leet = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}
        return ''.join(leet.get(c.lower(), c) for c in text)
    return text

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.author.bot:
        return

    uid = str(message.author.id)

    # reactor
    emojis = data["user_emojis"].get(uid, [])
    for emoji in emojis:
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            pass

    # mocking
    if uid in data["mock_targets"]:
        mode = data["mock_targets"][uid]
        mocked = mock_text(message.content, mode)
        reply = await message.channel.send(mocked)
        mock_reply_map[message.id] = reply

@bot.event
async def on_message_delete(message):
    if message.id in mock_reply_map:
        try:
            await mock_reply_map[message.id].delete()
        except discord.NotFound:
            pass
        del mock_reply_map[message.id]

bot.run(TOKEN)
