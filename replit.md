# Intel Engine - Roblox Background Check Discord Bot

## Overview
A Discord bot that performs comprehensive background checks on Roblox users, featuring risk assessment, alt account detection, intelligence group detection, and color-coded reports.

## Features
- **/check** - Run a basic background check on a Roblox user
- **/altcheck** - Check if a user is likely an alt account (scoring system)
- **/risk** - Get a detailed risk assessment with all factors
- **/scan** - Run a deep background scan with full details

## Risk Levels
- **LOW** (Green) - No flags detected
- **MEDIUM** (Gold) - One or more minor flags (new account, low friends, no description, etc.)
- **HIGH** (Red) - Major flags (banned, in custom banned list, flagged clothing)

## Risk Factors Checked
- Account age (under 14 days = flag)
- Friends count (under 5 = flag)
- Group membership (0 groups = flag)
- Badge count (0 badges = flag)
- Profile description (empty = flag)
- Previous username changes (3+ changes = flag)
- Flagged group membership (toxic/exploit groups detected)
- Inventory/clothing (private inventory flagged, flagged items detected)
- Custom banned list
- Roblox termination status

## Project Structure
```
/
├── main.py          # Main bot code with all slash commands
├── pyproject.toml   # Python dependencies
├── .gitignore       # Git ignore rules
└── replit.md        # This file
```

## Configuration (in main.py)
- `BANNED_USERS` - List of Roblox user IDs to flag as banned
- `NEW_ACCOUNT_DAYS` - Days threshold for "new account" (default: 14)
- `MIN_FRIENDS_COUNT` - Minimum friends before flagging (default: 5)
- `MIN_GROUPS_COUNT` - Minimum groups before flagging (default: 1)
- `FLAGGED_GROUPS` - Dictionary of toxic/exploit group IDs and names to flag
- `FLAGGED_CLOTHING_IDS` - List of clothing asset IDs to flag

## Environment Variables
- `DISCORD_BOT_TOKEN` - Your Discord bot token (required)

## Recent Changes
- November 30, 2025: Added comprehensive risk factors (friends, groups, badges, previous names, inventory)
- November 30, 2025: Added intelligence group detection
- November 30, 2025: Added alt account scoring system
- November 30, 2025: Initial bot creation with core features

## User Preferences
- None recorded yet
