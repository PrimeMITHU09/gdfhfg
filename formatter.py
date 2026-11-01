from datetime import datetime
from typing import Dict, Any, List


def format_mb(mb: float) -> str:
    """Format MB to human readable MB or GB"""
    try:
        mb_float = float(mb)
    except (ValueError, TypeError):
        return f"{mb} MB"
        
    if mb_float >= 1024:
        gb = mb_float / 1024
        return f"{mb_float:,.2f} MB ({gb:.2f} GB)"
    return f"{mb_float:,.2f} MB"


def generate_progress_bar(percentage: float, length: int = 10) -> str:
    """Generate a clean visual progress bar [████████░░]"""
    try:
        pct = max(0.0, min(100.0, float(percentage)))
    except (ValueError, TypeError):
        pct = 0.0
    
    filled = int(round((pct / 100.0) * length))
    filled = max(0, min(length, filled))
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}] {pct:.1f}%"


def format_proxy_stats(data: Dict[str, Any], proxy_gateway: str = "H143Proxy") -> str:
    """
    Format the H143 API response into a premium, professional card layout.
    """
    username = data.get("username", "Unknown")
    mb_purchased = data.get("mb_purchased", 0)
    mb_used = data.get("mb_used", 0)
    mb_remaining = data.get("mb_remaining", 0)
    mb_used_pct = data.get("mb_used_percentage", 0)
    mb_rem_pct = data.get("mb_remaining_percentage", 0)

    # Determine status
    if mb_remaining <= 0:
        status_text = "🔴 Depleted / Expired"
    elif mb_rem_pct < 10:
        status_text = "🟡 Critical Low"
    else:
        status_text = "🟢 Active"

    progress_bar = generate_progress_bar(mb_used_pct, length=12)
    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

    # Format numbers
    purchased_str = format_mb(mb_purchased)
    used_str = format_mb(mb_used)
    remaining_str = format_mb(mb_remaining)

    # Low balance alert
    alert_box = ""
    if mb_remaining <= 0:
        alert_box = "\n⚠️ *Notice:* Your bandwidth has run out! Please recharge your account.\n"
    elif mb_rem_pct <= 5:
        alert_box = f"\n⚠️ *Warning:* Low bandwidth balance ({mb_remaining} MB remaining)!\n"

    card = (
        "╔══════════════════════════╗\n"
        "   ⚡  *H143 PROXY STATS*  ⚡\n"
        "╚══════════════════════════╝\n\n"
        f"👤 *Proxy Username:* `{username}`\n"
        f"🌐 *Gateway:* `{proxy_gateway}`\n"
        f"📶 *Status:* {status_text}\n"
        f"{alert_box}\n"
        "📊 *Bandwidth Overview:*\n"
        f" ├ 📦 *Total Plan:* `{purchased_str}`\n"
        f" ├ 🔥 *Used:* `{used_str}` ({mb_used_pct}%)\n"
        f" └ 💎 *Remaining:* `{remaining_str}` ({mb_rem_pct}%)\n\n"
        f"📈 *Usage Meter:*\n"
        f"`{progress_bar}` (Used)\n\n"
        "──────────────────────────\n"
        f"🕒 *Checked At:* `{timestamp}`\n"
        "🛡️ *Authentic Data directly from H143 API*"
    )
    return card


def format_profile(user_info: dict, history: list = None) -> str:
    """
    Format user profile card with complete statistics.
    """
    user_id = user_info.get("user_id")
    first_name = user_info.get("first_name", "")
    last_name = user_info.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip() or "Telegram User"
    username = user_info.get("username")
    username_str = f"@{username}" if username else "Not Set"
    selected_proxy = user_info.get("selected_proxy", "H143Proxy")
    check_count = user_info.get("check_count", 0)
    last_user = user_info.get("last_checked_user") or "None"
    last_at = user_info.get("last_checked_at") or "Never"
    last_active = user_info.get("last_active_at") or user_info.get("created_at") or "Recently"
    created_at = user_info.get("created_at") or "Recently"

    # User tier based on checks
    if check_count >= 100:
        tier = "🏆 Legend Checker"
    elif check_count >= 25:
        tier = "💎 Pro Checker"
    elif check_count >= 5:
        tier = "⭐ Regular User"
    else:
        tier = "🌱 New Explorer"

    text = (
        "╔══════════════════════════╗\n"
        "    👤  *USER PROFILE*  👤\n"
        "╚══════════════════════════╝\n\n"
        f"🆔 *Telegram ID:* `{user_id}`\n"
        f"👤 *Name:* {full_name}\n"
        f"🔖 *Username:* {username_str}\n"
        f"🎖️ *Account Rank:* {tier}\n\n"
        "⚙️ *Preferences & Stats:*\n"
        f" ├ 🌐 *Selected Gateway:* `{selected_proxy}`\n"
        f" ├ 🔢 *Total Checks Done:* `{check_count} times`\n"
        f" ├ 📌 *Last Checked User:* `{last_user}`\n"
        f" ├ ⏱️ *Last Checked Time:* `{last_at}`\n"
        f" ├ 📱 *Last Bot Activity:* `{last_active}`\n"
        f" └ 📅 *Joined Bot:* `{created_at}`\n"
    )

    if history and len(history) > 0:
        text += "\n📜 *Recent Checked Accounts:*\n"
        for i, h in enumerate(history[:4], 1):
            p_user = h.get("proxy_username", "Unknown")
            rem = h.get("mb_remaining", 0)
            text += f" {i}. `{p_user}` — Remaining: `{rem} MB`\n"

    text += "\n──────────────────────────\n"
    text += "💡 *Tip:* Click *User* to check any proxy account bandwidth instantly!"
    return text


def format_about() -> str:
    """
    Format detailed About & How-to-use guide.
    """
    about_text = (
        "╔══════════════════════════╗\n"
        "    ℹ️  *ABOUT THIS BOT*  ℹ️\n"
        "╚══════════════════════════╝\n\n"
        "🤖 *H143 Proxy Checker Bot*\n"
        "এই বটটি সরাসরি অফিসিয়াল *H143 API* (`h143.xyz`) এর সাথে সংযুক্ত। "
        "এর মাধ্যমে আপনি কোনো ফেক বা ডামি ডাটা ছাড়াই প্রক্সি অ্যাকাউন্টের ব্যান্ডউইথ ও স্ট্যাটাস রিয়েল-টাইমে দেখতে পারবেন।\n\n"
        "📖 *বট দিয়ে কীভাবে প্রক্সি চেক করবেন? (নিয়মাবলী)*\n"
        "──────────────────────────\n"
        "1️⃣ *ধাপ ১ (গেটওয়ে নির্বাচন):*\n"
        "• নিচের মেনু থেকে `🌐 Proxy` বাটনে চাপুন।\n"
        "• এরপর `⚡ H143Proxy` বাটনে ক্লিক করে গেটওয়ে সক্রিয় করুন। (ডিফল্টভাবে এটি অন থাকে)\n\n"
        "2️⃣ *ধাপ ২ (ইউজারনেম পাঠানো):*\n"
        "• মেনুর `👤 User` বাটনে ক্লিক করুন।\n"
        "• বট আপনাকে মেসেজ দেবে: *'Send me your proxy username and wait a minute...'*\n"
        "• এবার আপনার প্রক্সি ইউজারনেম (যেমন: `liskptf7ly54z7sn5pkf`) লিখে সেন্ড করুন।\n\n"
        "3️⃣ *ধাপ ৩ (ফলাফল ও রিফ্রেশ):*\n"
        "• বট মুহূর্তের মধ্যে আসল ডাটা বিশ্লেষণ করে প্রগ্রেস বার সহ কার্ড প্রদর্শন করবে।\n"
        "• পুনরায় ডাটা রিফ্রেশ করতে কার্ডের নিচের `🔄 Recheck` বাটনে ক্লিক করলেই হবে!\n\n"
        "⚡ *শর্টকাট পদ্ধতি:*\n"
        "আপনি চাইলে যেকোনো সময় সরাসরি চ্যাটে `/check <ইউজারনেম>` (যেমন: `/check liskptf7ly54z7sn5pkf`) লিখলেও সাথে সাথে রেজাল্ট পাবেন!\n\n"
        "📊 *অন্যান্য সুবিধা:*\n"
        "• `📊 Profile` বাটনে ক্লিক করে আপনার মোট চেকের সংখ্যা ও আইডি দেখতে পারবেন।\n"
        "• ১০০% আসল ও লাইভ ডাটার নিশ্চয়তা।\n"
        "──────────────────────────"
    )
    return about_text


# ==========================================
# ADMIN PANEL FORMATTERS
# ==========================================

DEFAULT_WELCOME_MESSAGE = (
    "👋 *Welcome, {name}!* 🎉\n\n"
    "⚡ *H143 Proxy Checker Bot* এ আপনাকে স্বাগতম!\n"
    "এখানে আপনি সরাসরি অফিশিয়াল H143 API এর মাধ্যমে আপনার প্রক্সি ব্যান্ডউইথ ও স্ট্যাটাস রিয়েল-টাইমে চেক করতে পারবেন।\n\n"
    "📋 *মেনু অপশনসমূহ:*\n"
    "• 🌐 *Proxy* — প্রক্সি গেটওয়ে সিলেক্ট করুন (H143Proxy)\n"
    "• 👤 *User* — প্রক্সি ইউজারনেম দিয়ে লাইভ ডাটা চেক করুন\n"
    "• 📊 *Profile* — আপনার আইডি ও মোট চেক হিস্টোরি দেখুন\n"
    "• ℹ️ *About* — ব্যবহারের নিয়মাবলী ও বিস্তারিত জানুন\n\n"
    "👇 *নিচের বাটনগুলোতে ক্লিক করে শুরু করুন:*"
)


def format_admin_dashboard(stats: dict, admin_id: int) -> str:
    total_users = stats.get("total_users", 0)
    total_checks = stats.get("total_checks", 0)
    total_mb = format_mb(stats.get("total_mb_queried", 0))

    text = (
        "╔══════════════════════════╗\n"
        "   👑  *H143 ADMIN PANEL*  👑\n"
        "╚══════════════════════════╝\n\n"
        f"🔐 *Admin ID:* `{admin_id}` (Authorized ✅)\n"
        "🟢 *Server Status:* Online & Healthy\n\n"
        "📊 *System Analytics & Usage:*\n"
        f" ├ 👥 *Total Registered Users :* `{total_users} Users`\n"
        f" ├ ⚡ *Total Checks Executed  :* `{total_checks} Checks`\n"
        f" └ 💾 *Total Bandwidth Queried:* `{total_mb}`\n\n"
        "──────────────────────────\n"
        "🛠️ *Quick Controls:*\n"
        "• 👥 *Users List:* বট ব্যবহারকারীদের তালিকা ও লাস্ট অ্যাক্টিভ সময় দেখুন\n"
        "• ✏️ *Edit Welcome Msg:* নতুন ইউজারদের মেসেজ নিজের মতো এডিট করুন\n"
        "• 📢 *Broadcast:* সকল ইউজারের কাছে এক ক্লিকে নোটিশ পাঠান\n"
        "• 🔴 *Danger / Reset:* সেটিং রিসেট বা কাস্টমাইজেশন নিয়ন্ত্রণ করুন"
    )
    return text


def format_user_list(users: List[dict], page: int = 1, total_count: int = 0) -> str:
    if not users:
        return "👥 *User Directory:*\n\nএখনও কোনো সাধারণ ইউজার যুক্ত হয়নি।"

    text = (
        "╔══════════════════════════╗\n"
        "   👥  *BOT USERS DIRECTORY*  👥\n"
        "╚══════════════════════════╝\n\n"
        f"📊 *Total Users Found:* `{total_count or len(users)}`\n"
        "──────────────────────────\n"
    )

    for i, u in enumerate(users, 1):
        u_id = u["user_id"]
        fname = u["first_name"] or "User"
        lname = u["last_name"] or ""
        fullname = f"{fname} {lname}".strip()
        uname = f"@{u['username']}" if u["username"] else "No Username"
        checks = u["check_count"]
        last_act = u["last_active_at"]
        joined = u["created_at"]

        text += (
            f"*{i}.* 👤 *{fullname}* ({uname})\n"
            f"   ├ 🆔 ID: `{u_id}`\n"
            f"   ├ ⚡ Checks: `{checks} times`\n"
            f"   ├ ⏱️ Last Active: `{last_act}`\n"
            f"   └ 📅 Joined: `{joined}`\n\n"
        )

    text += "──────────────────────────\n"
    text += "💡 *Note:* ব্যবহারকারীদের লাইভ ব্যবহারের সময় উপরে দেখানো হয়েছে।"
    return text


def format_new_user_alert(user_id: int, first_name: str, last_name: str, username: str) -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    fullname = f"{first_name} {last_name}".strip() or "User"
    username_str = f"@{username}" if username else "Not Set"

    return (
        "🚨 *[NEW USER ALERT]* 🚨\n\n"
        "নতুন একজন ইউজার এইমাত্র বট চালু করেছেন:\n"
        f"👤 *Name:* {fullname}\n"
        f"🆔 *Telegram ID:* `{user_id}`\n"
        f"🔖 *Username:* {username_str}\n"
        f"🕒 *Started At:* `{now_str}`"
    )
