import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import datetime
import os
import json
import csv
import io
from flask import Flask
from threading import Thread

# Simple Flask server to keep Render awake
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)



TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

BANNED_USERS = [
]

NEW_ACCOUNT_DAYS = 14
MIN_FRIENDS_COUNT = 5
MIN_GROUPS_COUNT = 1

FLAGGED_GROUPS = {
}

FLAGGED_CLOTHING_IDS = [
]

last_scan_results = {}


async def roblox_user_from_name(username):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://users.roblox.com/v1/usernames/users",
                json={"usernames": [username], "excludeBannedUsers": False}
            ) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                if "data" in data and len(data["data"]) > 0:
                    return data["data"][0].get("id")
                return None
    except (aiohttp.ClientError, Exception):
        return None


async def roblox_user_info(userid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://users.roblox.com/v1/users/{userid}") as r:
                data = await r.json()
                
                if "errors" in data:
                    for error in data["errors"]:
                        if error.get("code") == 1 and "does not exist" in error.get("message", "").lower():
                            return {"banned_by_roblox": True, "id": userid}
                    return None
                
                if r.status != 200:
                    return None
                    
                if "id" not in data or "created" not in data:
                    return None
                    
                data["banned_by_roblox"] = False
                return data
    except (aiohttp.ClientError, Exception):
        return None


async def get_friends_count(userid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://friends.roblox.com/v1/users/{userid}/friends/count") as r:
                if r.status == 200:
                    data = await r.json()
                    return data.get("count", 0)
                return None
    except:
        return None


async def get_user_groups(userid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://groups.roblox.com/v1/users/{userid}/groups/roles") as r:
                if r.status == 200:
                    data = await r.json()
                    return data.get("data", [])
                return []
    except:
        return []


async def get_badge_count(userid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://badges.roblox.com/v1/users/{userid}/badges?limit=10&sortOrder=Desc") as r:
                if r.status == 200:
                    data = await r.json()
                    return len(data.get("data", []))
                return None
    except:
        return None


async def get_previous_usernames(userid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://users.roblox.com/v1/users/{userid}/username-history?limit=10&sortOrder=Desc") as r:
                if r.status == 200:
                    data = await r.json()
                    names = [item.get("name") for item in data.get("data", [])]
                    return names
                return []
    except:
        return []


async def get_user_inventory(userid, asset_type="Shirt"):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://inventory.roblox.com/v2/users/{userid}/inventory?assetTypes={asset_type}&limit=100"
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    return data.get("data", [])
                elif r.status == 403:
                    return "private"
                return []
    except:
        return []


async def get_premium_status(userid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://users.roblox.com/v1/users/{userid}/membership-types") as r:
                if r.status == 200:
                    data = await r.json()
                    return data.get("isCurrentlyMember", False)
                return False
    except:
        return False


async def get_followers_count(userid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://friends.roblox.com/v1/users/{userid}/followers/count") as r:
                if r.status == 200:
                    data = await r.json()
                    return data.get("count", 0)
                return None
    except:
        return None


async def get_user_games_created(userid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://games.roblox.com/v2/users/{userid}/games?accessFilter=Public&limit=10"
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    return len(data.get("data", []))
                return 0
    except:
        return 0


async def get_user_last_online(userid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://presence.roblox.com/v1/presence/last-online",
                json={"userIds": [userid]}
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    if "lastOnlineTimestamps" in data and data["lastOnlineTimestamps"]:
                        last_online_str = data["lastOnlineTimestamps"][0].get("lastOnline")
                        if last_online_str:
                            last_online = datetime.datetime.fromisoformat(last_online_str.replace("Z", "+00:00"))
                            days_offline = (datetime.datetime.now(datetime.timezone.utc) - last_online).days
                            return days_offline
                return None
    except Exception as e:
        return None


async def get_avatar_data(userid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://avatar.roblox.com/v1/users/{userid}/avatar") as r:
                if r.status == 200:
                    data = await r.json()
                    body_colors = data.get("bodyColors", {})
                    assets = data.get("assets", [])
                    return {"asset_count": len(assets), "has_custom_colors": bool(body_colors)}
                return None
    except:
        return None


def generate_json_export(username, userid, risk_level, reasons, extra_info):
    report = {
        "username": username,
        "user_id": userid,
        "profile_url": f"https://roblox.com/users/{userid}/profile",
        "risk_level": risk_level,
        "scan_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "flags": reasons,
        "account_age_days": extra_info.get("last_online_days", 0),
        "friends": extra_info.get("friends_count"),
        "followers": extra_info.get("followers"),
        "groups": extra_info.get("group_count", 0),
        "badges": extra_info.get("badge_count"),
        "games_created": extra_info.get("games_created", 0),
        "premium": extra_info.get("is_premium", False),
        "flagged_groups": extra_info.get("flagged_groups", []),
        "has_description": bool(extra_info.get("description")),
        "inventory_private": extra_info.get("inventory_private", False),
        "avatar_customized": extra_info.get("avatar_data", {}).get("asset_count", 0) > 0 if extra_info.get("avatar_data") else None
    }
    return json.dumps(report, indent=2)


def generate_csv_export(username, userid, risk_level, reasons, extra_info):
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["Field", "Value"])
    writer.writerow(["Username", username])
    writer.writerow(["User ID", userid])
    writer.writerow(["Profile URL", f"https://roblox.com/users/{userid}/profile"])
    writer.writerow(["Risk Level", risk_level])
    writer.writerow(["Scan Timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()])
    writer.writerow([""])
    writer.writerow(["Flags", ""])
    for flag in reasons:
        writer.writerow(["", flag])
    writer.writerow([""])
    writer.writerow(["Statistics", ""])
    writer.writerow(["Friends", extra_info.get("friends_count", "N/A")])
    writer.writerow(["Followers", extra_info.get("followers", "N/A")])
    writer.writerow(["Groups", extra_info.get("group_count", 0)])
    writer.writerow(["Badges", extra_info.get("badge_count", "N/A")])
    writer.writerow(["Games Created", extra_info.get("games_created", 0)])
    writer.writerow(["Premium Member", "Yes" if extra_info.get("is_premium") else "No"])
    writer.writerow(["Has Description", "Yes" if extra_info.get("description") else "No"])
    writer.writerow(["Inventory Private", "Yes" if extra_info.get("inventory_private") else "No"])
    
    return output.getvalue()


def risk_color(risk):
    if risk == "LOW":
        return discord.Color.green()
    if risk == "MEDIUM":
        return discord.Color.gold()
    return discord.Color.red()


async def evaluate_risk_full(userinfo, userid):
    risk = "LOW"
    reasons = []
    age_days = 0
    extra_info = {}

    if userinfo.get("banned_by_roblox", False):
        risk = "HIGH"
        reasons.append("Account is BANNED/TERMINATED on Roblox")
        return risk, reasons, age_days, extra_info

    try:
        created = datetime.datetime.fromisoformat(userinfo["created"].replace("Z", "+00:00"))
        age_days = (datetime.datetime.now(datetime.timezone.utc) - created).days

        if age_days < NEW_ACCOUNT_DAYS:
            if risk != "HIGH":
                risk = "MEDIUM"
            reasons.append(f"New account ({age_days} days old)")
    except (KeyError, ValueError):
        pass

    if userinfo.get("id") in BANNED_USERS:
        risk = "HIGH"
        reasons.append("User is in custom banned database")

    description = userinfo.get("description", "")
    if not description or description.strip() == "":
        if risk == "LOW":
            risk = "MEDIUM"
        reasons.append("No profile description")
    extra_info["description"] = description

    friends_count = await get_friends_count(userid)
    extra_info["friends_count"] = friends_count
    if friends_count is not None and friends_count < MIN_FRIENDS_COUNT:
        if risk == "LOW":
            risk = "MEDIUM"
        reasons.append(f"Low friends count ({friends_count})")

    groups = await get_user_groups(userid)
    extra_info["groups"] = groups
    group_count = len(groups)
    extra_info["group_count"] = group_count
    
    if group_count < MIN_GROUPS_COUNT:
        if risk == "LOW":
            risk = "MEDIUM"
        reasons.append(f"Not in any groups")

    flagged_groups_found = []
    for group in groups:
        group_id = group.get("group", {}).get("id")
        if group_id in FLAGGED_GROUPS:
            flagged_groups_found.append(FLAGGED_GROUPS[group_id])
    extra_info["flagged_groups"] = flagged_groups_found
    if flagged_groups_found:
        risk = "HIGH"
        reasons.append(f"Member of flagged group(s): {', '.join(flagged_groups_found)}")

    badge_count = await get_badge_count(userid)
    extra_info["badge_count"] = badge_count
    if badge_count is not None and badge_count == 0:
        if risk == "LOW":
            risk = "MEDIUM"
        reasons.append("No badges earned")

    previous_names = await get_previous_usernames(userid)
    extra_info["previous_names"] = previous_names
    if len(previous_names) > 3:
        if risk == "LOW":
            risk = "MEDIUM"
        reasons.append(f"Changed username {len(previous_names)} times")

    shirts = await get_user_inventory(userid, "Shirt")
    pants = await get_user_inventory(userid, "Pants")
    
    if shirts == "private" or pants == "private":
        extra_info["inventory_private"] = True
        reasons.append("Inventory is set to private")
    else:
        extra_info["inventory_private"] = False
        flagged_items = []
        
        if isinstance(shirts, list):
            for item in shirts:
                if item.get("assetId") in FLAGGED_CLOTHING_IDS:
                    flagged_items.append(item.get("name", "Unknown"))
        
        if isinstance(pants, list):
            for item in pants:
                if item.get("assetId") in FLAGGED_CLOTHING_IDS:
                    flagged_items.append(item.get("name", "Unknown"))
        
        extra_info["flagged_clothing"] = flagged_items
        if flagged_items:
            risk = "HIGH"
            reasons.append(f"Owns flagged clothing: {', '.join(flagged_items[:3])}")
        
        clothing_count = 0
        if isinstance(shirts, list):
            clothing_count += len(shirts)
        if isinstance(pants, list):
            clothing_count += len(pants)
        extra_info["clothing_count"] = clothing_count

    is_premium = await get_premium_status(userid)
    extra_info["is_premium"] = is_premium

    followers = await get_followers_count(userid)
    extra_info["followers"] = followers
    if followers is not None and followers == 0:
        if risk == "LOW":
            risk = "MEDIUM"
        reasons.append("Zero followers")

    games_created = await get_user_games_created(userid)
    extra_info["games_created"] = games_created
    if games_created == 0:
        reasons.append("No games created")

    last_online_days = await get_user_last_online(userid)
    extra_info["last_online_days"] = last_online_days
    if last_online_days is not None and last_online_days > 365:
        if risk == "LOW":
            risk = "MEDIUM"
        reasons.append(f"Inactive for {last_online_days} days")

    avatar_data = await get_avatar_data(userid)
    extra_info["avatar_data"] = avatar_data
    if avatar_data and avatar_data.get("asset_count", 0) == 0:
        reasons.append("No avatar customization (default)")

    return risk, reasons, age_days, extra_info


def evaluate_risk_basic(userinfo):
    risk = "LOW"
    reasons = []
    age_days = 0

    if userinfo.get("banned_by_roblox", False):
        risk = "HIGH"
        reasons.append("Account is BANNED/TERMINATED on Roblox")
        return risk, reasons, age_days

    try:
        created = datetime.datetime.fromisoformat(userinfo["created"].replace("Z", "+00:00"))
        age_days = (datetime.datetime.now(datetime.timezone.utc) - created).days

        if age_days < NEW_ACCOUNT_DAYS:
            risk = "MEDIUM"
            reasons.append(f"New account ({age_days} days old)")
    except (KeyError, ValueError):
        pass

    if userinfo.get("id") in BANNED_USERS:
        risk = "HIGH"
        reasons.append("User is in custom banned database")

    return risk, reasons, age_days


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@bot.tree.command(name="check", description="Run a basic background check on a Roblox user")
@app_commands.describe(username="The Roblox username to check")
async def check(interaction: discord.Interaction, username: str):
    await interaction.response.defer()

    userid = await roblox_user_from_name(username)
    if userid is None:
        return await interaction.followup.send("User not found on Roblox.")

    userinfo = await roblox_user_info(userid)
    if userinfo is None:
        return await interaction.followup.send("Could not fetch user information. The Roblox API may be unavailable.")

    is_banned = userinfo.get("banned_by_roblox", False)
    risk, reasons, age_days = evaluate_risk_basic(userinfo)
    reasons_text = "\n".join([f"- {r}" for r in reasons]) if reasons else "No flags detected."

    embed = discord.Embed(
        title=f"Background Check: {userinfo.get('name', username)}",
        color=risk_color(risk),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    if not is_banned:
        embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={userid}&width=150&height=150&format=png")
    
    embed.add_field(name="Profile", value=f"[View Profile](https://roblox.com/users/{userid}/profile)", inline=True)
    embed.add_field(name="User ID", value=str(userid), inline=True)
    
    if is_banned:
        embed.add_field(name="Status", value="**BANNED**", inline=True)
    else:
        embed.add_field(name="Account Age", value=f"{age_days} days", inline=True)
        
    embed.add_field(name="Risk Level", value=f"**{risk}**", inline=True)
    
    if not is_banned:
        embed.add_field(name="Display Name", value=userinfo.get("displayName", "N/A"), inline=True)
        
    embed.add_field(name="Flags", value=reasons_text, inline=False)
    embed.set_footer(text="Intel Engine | Use /scan for full report")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="altcheck", description="Check if a user is likely an alt account")
@app_commands.describe(username="The Roblox username to check for alt status")
async def altcheck(interaction: discord.Interaction, username: str):
    await interaction.response.defer()

    userid = await roblox_user_from_name(username)
    if userid is None:
        return await interaction.followup.send("User not found on Roblox.")

    userinfo = await roblox_user_info(userid)
    if userinfo is None:
        return await interaction.followup.send("Could not fetch user information. The Roblox API may be unavailable.")

    is_banned = userinfo.get("banned_by_roblox", False)
    
    if is_banned:
        embed = discord.Embed(
            title=f"Alt Check: {username}",
            description="**Account is BANNED/TERMINATED on Roblox**",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Alt Status", value="Cannot determine - account banned", inline=True)
        embed.add_field(name="Profile", value=f"[View Profile](https://roblox.com/users/{userid}/profile)", inline=False)
        embed.set_footer(text="Intel Engine Alt Detection")
        return await interaction.followup.send(embed=embed)

    try:
        created = datetime.datetime.fromisoformat(userinfo["created"].replace("Z", "+00:00"))
        age_days = (datetime.datetime.now(datetime.timezone.utc) - created).days
    except (KeyError, ValueError):
        return await interaction.followup.send("Could not determine account age.")

    friends_count = await get_friends_count(userid)
    badge_count = await get_badge_count(userid)
    groups = await get_user_groups(userid)
    
    alt_score = 0
    alt_reasons = []
    
    if age_days < NEW_ACCOUNT_DAYS:
        alt_score += 3
        alt_reasons.append(f"New account ({age_days} days)")
    elif age_days < 30:
        alt_score += 2
        alt_reasons.append(f"Account under 30 days ({age_days} days)")
    elif age_days < 90:
        alt_score += 1
        alt_reasons.append(f"Account under 90 days ({age_days} days)")
    
    if friends_count is not None and friends_count < 5:
        alt_score += 2
        alt_reasons.append(f"Low friends ({friends_count})")
    
    if badge_count is not None and badge_count == 0:
        alt_score += 2
        alt_reasons.append("No badges")
    
    if len(groups) == 0:
        alt_score += 1
        alt_reasons.append("Not in any groups")
    
    description = userinfo.get("description", "")
    if not description or description.strip() == "":
        alt_score += 1
        alt_reasons.append("No description")
    
    if alt_score >= 5:
        alt_status = "LIKELY ALT"
        color = discord.Color.red()
    elif alt_score >= 3:
        alt_status = "POSSIBLY ALT"
        color = discord.Color.orange()
    else:
        alt_status = "NOT AN ALT"
        color = discord.Color.green()

    embed = discord.Embed(
        title=f"Alt Check: {userinfo.get('name', 'Unknown')}",
        description=f"Alt Score: **{alt_score}/10**",
        color=color,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={userid}&width=150&height=150&format=png")
    embed.add_field(name="Alt Status", value=f"**{alt_status}**", inline=True)
    embed.add_field(name="Account Age", value=f"{age_days} days", inline=True)
    embed.add_field(name="Friends", value=str(friends_count) if friends_count else "N/A", inline=True)
    embed.add_field(name="Badges", value=str(badge_count) if badge_count else "N/A", inline=True)
    embed.add_field(name="Groups", value=str(len(groups)), inline=True)
    embed.add_field(name="Indicators", value="\n".join([f"- {r}" for r in alt_reasons]) if alt_reasons else "None", inline=False)
    embed.add_field(name="Profile", value=f"[View Profile](https://roblox.com/users/{userid}/profile)", inline=False)
    embed.set_footer(text="Intel Engine Alt Detection")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="risk", description="Get a risk score for a Roblox user")
@app_commands.describe(username="The Roblox username to assess risk")
async def risk_cmd(interaction: discord.Interaction, username: str):
    await interaction.response.defer()

    userid = await roblox_user_from_name(username)
    if userid is None:
        return await interaction.followup.send("User not found on Roblox.")

    userinfo = await roblox_user_info(userid)
    if userinfo is None:
        return await interaction.followup.send("Could not fetch user information. The Roblox API may be unavailable.")

    is_banned = userinfo.get("banned_by_roblox", False)
    risk_level, reasons, age_days, extra_info = await evaluate_risk_full(userinfo, userid)

    embed = discord.Embed(
        title=f"Risk Report: {userinfo.get('name', username)}",
        color=risk_color(risk_level),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    if not is_banned:
        embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={userid}&width=150&height=150&format=png")
        
    embed.add_field(name="Risk Level", value=f"**{risk_level}**", inline=True)
    embed.add_field(name="Account Age", value=f"{age_days} days" if not is_banned else "N/A", inline=True)
    friends = extra_info.get("friends_count")
    embed.add_field(name="Friends", value=str(friends) if friends is not None else "N/A", inline=True)
    embed.add_field(name="Followers", value=str(extra_info.get("followers", "N/A")), inline=True)
    embed.add_field(name="Premium", value="Yes" if extra_info.get("is_premium") else "No", inline=True)
    embed.add_field(name="Groups", value=str(extra_info.get("group_count", 0)), inline=True)
    badges = extra_info.get("badge_count")
    embed.add_field(name="Badges", value=str(badges) if badges is not None else "N/A", inline=True)
    embed.add_field(name="Games Created", value=str(extra_info.get("games_created", 0)), inline=True)
    last_online = extra_info.get("last_online_days")
    embed.add_field(name="Last Online", value=f"{last_online} days ago" if last_online is not None else "N/A", inline=True)
    
    if extra_info.get("flagged_groups"):
        embed.add_field(name="Flagged Groups", value=", ".join(extra_info["flagged_groups"]), inline=True)
    
    embed.add_field(name="Profile", value=f"[View Profile](https://roblox.com/users/{userid}/profile)", inline=True)
    embed.add_field(name="Risk Factors", value="\n".join([f"- {r}" for r in reasons]) if reasons else "No risk flags detected.", inline=False)
    embed.set_footer(text="Intel Engine Risk Assessment")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="scan", description="Run a deep background scan on a Roblox user")
@app_commands.describe(username="The Roblox username for deep scan")
async def scan(interaction: discord.Interaction, username: str):
    await interaction.response.defer()

    userid = await roblox_user_from_name(username)
    if userid is None:
        return await interaction.followup.send("User not found on Roblox.")

    userinfo = await roblox_user_info(userid)
    if userinfo is None:
        return await interaction.followup.send("Could not fetch user information. The Roblox API may be unavailable.")

    is_banned = userinfo.get("banned_by_roblox", False)
    risk_level, reasons, age_days, extra_info = await evaluate_risk_full(userinfo, userid)

    embed = discord.Embed(
        title=f"Deep Scan: {userinfo.get('name', username)}",
        color=risk_color(risk_level),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    if not is_banned:
        embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={userid}&width=150&height=150&format=png")
        
    embed.add_field(name="User ID", value=str(userid), inline=True)
    embed.add_field(name="Display Name", value=userinfo.get("displayName", "N/A") if not is_banned else "N/A", inline=True)
    embed.add_field(name="Risk Level", value=f"**{risk_level}**", inline=True)
    
    if is_banned:
        embed.add_field(name="Account Status", value="**BANNED/TERMINATED**", inline=True)
        embed.add_field(name="Account Age", value="N/A", inline=True)
    else:
        created_date = userinfo.get("created", "Unknown")[:10]
        embed.add_field(name="Account Created", value=created_date, inline=True)
        embed.add_field(name="Account Age", value=f"{age_days} days", inline=True)
    
    friends = extra_info.get("friends_count")
    embed.add_field(name="Friends", value=str(friends) if friends is not None else "N/A", inline=True)
    followers = extra_info.get("followers")
    embed.add_field(name="Followers", value=str(followers) if followers is not None else "N/A", inline=True)
    embed.add_field(name="Premium", value="Yes" if extra_info.get("is_premium") else "No", inline=True)
    embed.add_field(name="Groups", value=str(extra_info.get("group_count", 0)), inline=True)
    badges = extra_info.get("badge_count")
    embed.add_field(name="Badges", value=str(badges) if badges is not None else "N/A", inline=True)
    embed.add_field(name="Games Created", value=str(extra_info.get("games_created", 0)), inline=True)
    last_online = extra_info.get("last_online_days")
    embed.add_field(name="Last Online", value=f"{last_online} days ago" if last_online is not None else "N/A", inline=True)
    avatar_data = extra_info.get("avatar_data")
    if avatar_data:
        embed.add_field(name="Avatar Customized", value="Yes" if avatar_data.get("asset_count", 0) > 0 else "No", inline=True)
    
    if extra_info.get("flagged_groups"):
        embed.add_field(name="Flagged Groups", value=", ".join(extra_info["flagged_groups"]), inline=False)
    
    previous_names = extra_info.get("previous_names", [])
    if previous_names:
        embed.add_field(name="Previous Names", value=", ".join(previous_names[:5]), inline=False)
    
    if extra_info.get("inventory_private"):
        embed.add_field(name="Inventory", value="Private", inline=True)
    else:
        clothing_count = extra_info.get("clothing_count", 0)
        embed.add_field(name="Clothing Items", value=str(clothing_count), inline=True)
        
        flagged = extra_info.get("flagged_clothing", [])
        if flagged:
            embed.add_field(name="Flagged Clothing", value=", ".join(flagged[:3]), inline=True)
    
    if not is_banned:
        description = extra_info.get("description", "")
        if description and description.strip():
            if len(description) > 150:
                description = description[:150] + "..."
            embed.add_field(name="Description", value=description, inline=False)
        else:
            embed.add_field(name="Description", value="*No description*", inline=False)
    
    embed.add_field(name="Profile", value=f"[View Profile](https://roblox.com/users/{userid}/profile)", inline=False)
    embed.add_field(name="All Flags", value="\n".join([f"- {r}" for r in reasons]) if reasons else "No issues detected.", inline=False)
    embed.set_footer(text="Intel Engine Deep Scan")

    last_scan_results[interaction.user.id] = {
        "username": userinfo.get("name", username),
        "userid": userid,
        "risk_level": risk_level,
        "reasons": reasons,
        "extra_info": extra_info
    }
    
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="export", description="Export the last scan as JSON or CSV")
@app_commands.describe(format="Export format: json or csv")
async def export_report(interaction: discord.Interaction, format: str = "json"):
    await interaction.response.defer()
    
    user_id = interaction.user.id
    if user_id not in last_scan_results:
        return await interaction.followup.send("No scan results to export. Run /scan first.")
    
    result = last_scan_results[user_id]
    format = format.lower()
    
    if format == "json":
        content = generate_json_export(
            result["username"],
            result["userid"],
            result["risk_level"],
            result["reasons"],
            result["extra_info"]
        )
        filename = f"{result['username']}_scan_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file = discord.File(io.BytesIO(content.encode()), filename=filename)
    elif format == "csv":
        content = generate_csv_export(
            result["username"],
            result["userid"],
            result["risk_level"],
            result["reasons"],
            result["extra_info"]
        )
        filename = f"{result['username']}_scan_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file = discord.File(io.BytesIO(content.encode()), filename=filename)
    else:
        return await interaction.followup.send("Invalid format. Use 'json' or 'csv'.")
    
    embed = discord.Embed(
        title="Report Export",
        description=f"Scan report for **{result['username']}** (ID: {result['userid']})",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Risk Level", value=result['risk_level'], inline=True)
    embed.add_field(name="Format", value=format.upper(), inline=True)
    embed.set_footer(text="Intel Engine Report Export")
    
    await interaction.followup.send(embed=embed, file=file)


if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN environment variable not set!")
        print("Please add your Discord bot token to the Secrets.")
    else:
        # Start the Flask webserver in a background thread
        Thread(target=run).start()
        # Start the Discord bot
        bot.run(TOKEN)

