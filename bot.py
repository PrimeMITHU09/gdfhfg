import logging
import re
import sys
import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configure UTF-8 for Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
    MenuButtonCommands,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, ADMIN_ID, DEFAULT_PROXY, SUPPORTED_PROXIES
from database import (
    init_db,
    register_or_update_user,
    touch_user_activity,
    set_user_proxy,
    record_check,
    get_user,
    get_user_history,
    get_all_users,
    get_all_user_ids,
    get_admin_stats,
    get_setting,
    set_setting,
)
from api_client import fetch_proxy_stats
from formatter import (
    format_proxy_stats,
    format_profile,
    format_about,
    format_admin_dashboard,
    format_user_list,
    format_new_user_alert,
    DEFAULT_WELCOME_MESSAGE,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# COLORED BUTTONS (Clean Text - No Emojis)
# style="success" -> Green
# style="danger"  -> Red
# style="primary" -> Blue
# ==========================================

USER_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            KeyboardButton("Proxy", style="primary"),
            KeyboardButton("User", style="success")
        ],
        [
            KeyboardButton("Profile", style="primary"),
            KeyboardButton("About", style="primary")
        ]
    ],
    resize_keyboard=True,
    is_persistent=True
)

ADMIN_MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            KeyboardButton("Proxy", style="primary"),
            KeyboardButton("User", style="success")
        ],
        [
            KeyboardButton("Profile", style="primary"),
            KeyboardButton("About", style="primary")
        ],
        [
            KeyboardButton("Admin Panel", style="danger")
        ]
    ],
    resize_keyboard=True,
    is_persistent=True
)

ADMIN_PANEL_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            KeyboardButton("System Stats", style="primary"),
            KeyboardButton("User List", style="primary")
        ],
        [
            KeyboardButton("Edit Welcome Msg", style="success"),
            KeyboardButton("Broadcast", style="success")
        ],
        [
            KeyboardButton("Back to Main Menu", style="danger")
        ]
    ],
    resize_keyboard=True,
    is_persistent=True
)


def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Returns admin keyboard if user is ADMIN_ID, else regular user keyboard."""
    return ADMIN_MAIN_KEYBOARD if user_id == ADMIN_ID else USER_KEYBOARD


def get_user_proxy_selection(user_id: int) -> str:
    user = get_user(user_id)
    return user["selected_proxy"] if user and user.get("selected_proxy") else DEFAULT_PROXY


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    context.user_data.clear()
    user = update.effective_user
    is_new = register_or_update_user(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
        last_name=user.last_name or ""
    )

    # Notify admin immediately on new user registration
    if is_new and user.id != ADMIN_ID:
        try:
            alert_msg = format_new_user_alert(
                user_id=user.id,
                first_name=user.first_name or "",
                last_name=user.last_name or "",
                username=user.username or ""
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=alert_msg,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not send new user alert to admin: {e}")

    welcome_template = get_setting("welcome_message", DEFAULT_WELCOME_MESSAGE)
    welcome_text = welcome_template.format(
        name=user.first_name or "User",
        id=user.id,
        username=f"@{user.username}" if user.username else "User"
    )

    keyboard = get_main_keyboard(user.id)
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /help command."""
    touch_user_activity(update.effective_user.id)
    help_text = (
        "📖 *Help & Instructions:*\n\n"
        "1️⃣ *Proxy নির্বাচন:* 'Proxy' বাটনে ক্লিক করে 'H143Proxy' সিলেক্ট করুন।\n"
        "2️⃣ *ব্যান্ডউইথ চেক:* 'User' বাটনে ক্লিক করে প্রক্সি ইউজারনেম সেন্ড করুন।\n"
        "3️⃣ *প্রোফাইল:* 'Profile' বাটনে ক্লিক করে অ্যাকাউন্ট তথ্য ও মোট চেকের সংখ্যা দেখুন।\n"
        "4️⃣ *নিয়মাবলী:* 'About' বাটনে ক্লিক করে বিস্তারিত গাইড দেখুন।\n\n"
        "💡 *টিপ:* আপনি সরাসরি `/check <username>` কমান্ড ব্যবহার করেও সাথে সাথে চেক করতে পারেন!"
    )
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )


async def handle_proxy_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the Proxy button / selection."""
    user = update.effective_user
    touch_user_activity(user.id)
    current_proxy = get_user_proxy_selection(user.id)

    button_text = f"{current_proxy} (Active)" if current_proxy == "H143Proxy" else "Select H143Proxy"
    keyboard = [
        [InlineKeyboardButton(button_text, callback_data="select_proxy:H143Proxy", style="success")],
        [InlineKeyboardButton("Check Username Now", callback_data="prompt_user", style="primary")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "*PROXY GATEWAY SELECTION*\n"
        "──────────────────────────\n"
        f"বর্তমান নির্বাচিত প্রক্সি: `{current_proxy}`\n\n"
        "নিচের অপশনে ক্লিক করে আপনার কাঙ্ক্ষিত প্রক্সি গেটওয়ে সিলেক্ট করুন:"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def handle_user_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompts user to send proxy username."""
    touch_user_activity(update.effective_user.id)
    context.user_data["waiting_for_username"] = True

    prompt_text = (
        "*Send me your proxy username and wait a minute...*\n\n"
        "আপনার প্রক্সি ইউজারনেমটি লিখে এখানে মেসেজ সেন্ড করুন।\n"
        "*(যেমন: `liskptf7ly54z7sn5pkf`)*"
    )
    await update.message.reply_text(
        prompt_text,
        parse_mode="Markdown"
    )


async def handle_profile_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays user profile."""
    user = update.effective_user
    touch_user_activity(user.id)

    user_info = get_user(user.id)
    history = get_user_history(user.id, limit=5)
    profile_text = format_profile(user_info, history)

    keyboard = [
        [
            InlineKeyboardButton("Check Proxy", callback_data="prompt_user", style="success"),
            InlineKeyboardButton("Refresh Profile", callback_data="refresh_profile", style="primary")
        ],
        [
            InlineKeyboardButton("How It Works", callback_data="show_about", style="primary")
        ]
    ]
    await update.message.reply_text(
        profile_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_about_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays About information and usage guide."""
    touch_user_activity(update.effective_user.id)
    about_text = format_about()
    keyboard = [
        [
            InlineKeyboardButton("Check Proxy Now", callback_data="prompt_user", style="success"),
            InlineKeyboardButton("Select Gateway", callback_data="select_proxy:H143Proxy", style="primary")
        ]
    ]
    await update.message.reply_text(
        about_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==========================================
# ADMIN PANEL (Exclusive to ADMIN_ID)
# ==========================================

async def open_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Opens the admin control dashboard."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    stats = get_admin_stats()
    dashboard_text = format_admin_dashboard(stats, ADMIN_ID)

    keyboard = [
        [
            InlineKeyboardButton("View User Directory", callback_data="admin_view_users", style="primary"),
            InlineKeyboardButton("Refresh Stats", callback_data="admin_refresh_dashboard", style="success")
        ],
        [
            InlineKeyboardButton("Edit Welcome Message", callback_data="admin_edit_welcome", style="primary"),
            InlineKeyboardButton("Broadcast Message", callback_data="admin_prompt_broadcast", style="success")
        ],
        [
            InlineKeyboardButton("Reset Welcome Msg", callback_data="admin_reset_welcome", style="danger")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        dashboard_text,
        parse_mode="Markdown",
        reply_markup=ADMIN_PANEL_KEYBOARD
    )
    await update.message.reply_text(
        "*Admin Controls:* বাটনগুলো ব্যবহার করে কার্যক্রম পরিচালনা করুন:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def show_admin_user_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    """Displays registered bot users with bot usage and activity times."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    users = get_all_users(limit=25, offset=(page - 1) * 25)
    stats = get_admin_stats()
    text = format_user_list(users, page=page, total_count=stats["total_users"])

    keyboard = [
        [
            InlineKeyboardButton("Refresh Directory", callback_data="admin_view_users", style="success"),
            InlineKeyboardButton("Admin Panel", callback_data="admin_refresh_dashboard", style="primary")
        ]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def prompt_edit_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompts admin to enter new welcome message."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    context.user_data["admin_state"] = "waiting_for_welcome_msg"
    current_msg = get_setting("welcome_message", DEFAULT_WELCOME_MESSAGE)

    text = (
        "*EDIT WELCOME MESSAGE*\n"
        "──────────────────────────\n"
        "নতুন ব্যবহারকারীদের জন্য আপনার পছন্দমতো স্বাগতম মেসেজ সেট করুন।\n\n"
        "📝 *বর্তমান মেসেজ:*\n\n"
        f"```\n{current_msg}\n```\n\n"
        "💡 *যে ভেরিয়েবলগুলো ব্যবহার করতে পারবেন:*\n"
        "• `{name}` — ইউজারের নাম\n"
        "• `{id}` — ইউজারের আইডি\n"
        "• `{username}` — ইউজারের ইউজারনেম\n\n"
        "👇 *এখন আপনার নতুন মেসেজটি লিখে এখানে পাঠান:*\n"
        "*(বাতিল করতে 'cancel' লিখুন)*"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")


async def prompt_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompts admin to enter broadcast message."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    context.user_data["admin_state"] = "waiting_for_broadcast_msg"
    stats = get_admin_stats()

    text = (
        "*BROADCAST TO ALL USERS*\n"
        "──────────────────────────\n"
        f"মোট প্রাপক: `{stats['total_users']}` জন ব্যবহারকারী।\n\n"
        "👇 *যে বার্তাটি সবার কাছে পাঠাতে চান তা লিখে এখানে সেন্ড করুন:*\n"
        "*(বাতিল করতে 'cancel' লিখুন)*"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")


# ==========================================
# PROXY CHECK LOGIC
# ==========================================

async def perform_proxy_check(chat_id: int, user_id: int, proxy_username: str, context: ContextTypes.DEFAULT_TYPE, message_to_edit=None):
    """
    Core function that queries the H143 API and displays the result.
    """
    clean_username = proxy_username.strip()
    selected_proxy = get_user_proxy_selection(user_id)

    loading_text = f"⏳ *Checking stats for `{clean_username}` from H143 API, please wait...*"
    if message_to_edit:
        status_msg = message_to_edit
        await status_msg.edit_text(loading_text, parse_mode="Markdown")
    else:
        status_msg = await context.bot.send_message(chat_id=chat_id, text=loading_text, parse_mode="Markdown")

    result = await fetch_proxy_stats(clean_username)

    if result.get("success"):
        data = result["data"]
        record_check(
            user_id=user_id,
            proxy_username=clean_username,
            mb_purchased=data.get("mb_purchased", 0),
            mb_used=data.get("mb_used", 0),
            mb_remaining=data.get("mb_remaining", 0)
        )

        formatted_card = format_proxy_stats(data, selected_proxy)

        keyboard = [
            [
                InlineKeyboardButton("Recheck", callback_data=f"recheck:{clean_username}", style="success"),
                InlineKeyboardButton("Check Another", callback_data="prompt_user", style="primary")
            ],
            [
                InlineKeyboardButton("My Profile", callback_data="refresh_profile", style="primary"),
                InlineKeyboardButton("About", callback_data="show_about", style="primary")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await status_msg.edit_text(
            formatted_card,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        error_msg = result.get("error", "Unknown error")
        
        if "not found" in str(error_msg).lower():
            err_text = (
                "❌ *Proxy Account Not Found!*\n\n"
                f"ইউজারনেম: `{clean_username}` দিয়ে কোনো সক্রিয় অ্যাকাউন্ট খুঁজে পাওয়া যায়নি।\n\n"
                "⚠️ অনুগ্রহ করে সঠিক ইউজারনেম চেক করে পুনরায় চেষ্টা করুন।"
            )
        elif "invalid api key" in str(error_msg).lower():
            err_text = (
                "❌ *API Authentication Error!*\n\n"
                "বটটিতে কনফিগার করা H143 API Key অকার্যকর। অনুগ্রহ করে বট অ্যাডমিনের সাথে যোগাযোগ করুন।"
            )
        else:
            err_text = (
                f"❌ *Error Occurred:*\n`{error_msg}`\n\n"
                "কিছুক্ষণ পর পুনরায় চেষ্টা করুন।"
            )

        keyboard = [
            [InlineKeyboardButton("Try Again", callback_data="prompt_user", style="danger")]
        ]
        await status_msg.edit_text(
            err_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /check <username> command."""
    user = update.effective_user
    touch_user_activity(user.id)

    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "ℹ️ *Usage:* `/check <username>`\n\nউদাহরণ:\n`/check liskptf7ly54z7sn5pkf`",
            parse_mode="Markdown"
        )
        return

    proxy_username = context.args[0]
    await perform_proxy_check(
        chat_id=update.effective_chat.id,
        user_id=user.id,
        proxy_username=proxy_username,
        context=context
    )


# ==========================================
# MESSAGE & CALLBACK DISPATCHER
# ==========================================

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all incoming regular text messages."""
    text = update.message.text.strip()
    text_lower = text.lower()
    user = update.effective_user
    touch_user_activity(user.id)

    admin_state = context.user_data.get("admin_state")

    # --- ADMIN STATE HANDLING ---
    if user.id == ADMIN_ID and admin_state:
        if text_lower == "cancel":
            context.user_data["admin_state"] = None
            await update.message.reply_text("কার্যক্রম বাতিল করা হয়েছে।", reply_markup=ADMIN_PANEL_KEYBOARD)
            return

        if admin_state == "waiting_for_welcome_msg":
            context.user_data["admin_state"] = None
            set_setting("welcome_message", text)
            preview = text.format(name=user.first_name, id=user.id, username=f"@{user.username}")
            success_msg = (
                "✅ *Success: Welcome Message Updated!*\n\n"
                "নতুন ইউজাররা এখন থেকে নিচের মেসেজটি দেখতে পাবেন:\n"
                "──────────────────────────\n"
                f"{preview}\n"
                "──────────────────────────"
            )
            await update.message.reply_text(success_msg, parse_mode="Markdown", reply_markup=ADMIN_PANEL_KEYBOARD)
            return

        if admin_state == "waiting_for_broadcast_msg":
            context.user_data["admin_state"] = None
            context.user_data["pending_broadcast_text"] = text

            confirm_keyboard = [
                [
                    InlineKeyboardButton("Confirm & Send", callback_data="admin_do_broadcast", style="success"),
                    InlineKeyboardButton("Cancel", callback_data="admin_cancel_broadcast", style="danger")
                ]
            ]
            await update.message.reply_text(
                "*BROADCAST PREVIEW*\n──────────────────────────\n"
                f"{text}\n──────────────────────────\n"
                "আপনি কি নিশ্চিত এই মেসেজটি সকল ব্যবহারকারীর কাছে পাঠাতে চান?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(confirm_keyboard)
            )
            return

    # --- BUTTON MATCHING ---
    # Match Admin Panel
    if user.id == ADMIN_ID and ("admin" in text_lower or "admin panel" in text_lower):
        await open_admin_panel(update, context)
        return

    # Admin Panel sub-buttons
    if user.id == ADMIN_ID:
        if "user list" in text_lower or "users" in text_lower:
            await show_admin_user_list(update, context)
            return
        elif "stats" in text_lower or "system stats" in text_lower:
            stats = get_admin_stats()
            dashboard_text = format_admin_dashboard(stats, ADMIN_ID)
            await update.message.reply_text(dashboard_text, parse_mode="Markdown", reply_markup=ADMIN_PANEL_KEYBOARD)
            return
        elif "edit welcome" in text_lower or "welcome" in text_lower:
            await prompt_edit_welcome_message(update, context)
            return
        elif "broadcast" in text_lower:
            await prompt_broadcast_message(update, context)
            return
        elif "back" in text_lower or "menu" in text_lower:
            await update.message.reply_text("মূল মেনুতে ফিরে যাওয়া হলো।", reply_markup=ADMIN_MAIN_KEYBOARD)
            return

    # Match Proxy button
    if "proxy" in text_lower:
        await handle_proxy_button(update, context)
        return

    # Match User button
    if "user" in text_lower:
        await handle_user_button(update, context)
        return

    # Match Profile button
    if "profile" in text_lower:
        await handle_profile_button(update, context)
        return

    # Match About button
    if "about" in text_lower or "guide" in text_lower:
        await handle_about_button(update, context)
        return

    # If waiting for username OR user sends a proxy username string directly
    is_waiting = context.user_data.get("waiting_for_username", False)
    if is_waiting or (not text.startswith("/") and len(text.split()) == 1 and len(text) >= 3):
        context.user_data["waiting_for_username"] = False
        await perform_proxy_check(
            chat_id=update.effective_chat.id,
            user_id=user.id,
            proxy_username=text,
            context=context
        )
        return

    # Fallback
    keyboard = get_main_keyboard(user.id)
    await update.message.reply_text(
        "অনুগ্রহ করে নিচের মেনু বাটন থেকে অপশন সিলেক্ট করুন অথবা আপনার প্রক্সি ইউজারনেম সেন্ড করুন:",
        reply_markup=keyboard
    )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all inline keyboard button clicks."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    touch_user_activity(user.id)

    # --- ADMIN INLINE ACTIONS ---
    if user.id == ADMIN_ID:
        if data == "admin_refresh_dashboard":
            stats = get_admin_stats()
            dashboard_text = format_admin_dashboard(stats, ADMIN_ID)
            keyboard = [
                [
                    InlineKeyboardButton("View User Directory", callback_data="admin_view_users", style="primary"),
                    InlineKeyboardButton("Refresh Stats", callback_data="admin_refresh_dashboard", style="success")
                ],
                [
                    InlineKeyboardButton("Edit Welcome Message", callback_data="admin_edit_welcome", style="primary"),
                    InlineKeyboardButton("Broadcast Message", callback_data="admin_prompt_broadcast", style="success")
                ],
                [
                    InlineKeyboardButton("Reset Welcome Msg", callback_data="admin_reset_welcome", style="danger")
                ]
            ]
            try:
                await query.edit_message_text(
                    dashboard_text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception:
                pass
            return

        elif data == "admin_view_users":
            await show_admin_user_list(update, context)
            return

        elif data == "admin_edit_welcome":
            await prompt_edit_welcome_message(update, context)
            return

        elif data == "admin_prompt_broadcast":
            await prompt_broadcast_message(update, context)
            return

        elif data == "admin_reset_welcome":
            set_setting("welcome_message", DEFAULT_WELCOME_MESSAGE)
            await query.message.reply_text("Welcome message restored to default template!", parse_mode="Markdown")
            return

        elif data == "admin_cancel_broadcast":
            context.user_data["pending_broadcast_text"] = None
            await query.edit_message_text("Broadcast cancelled.", parse_mode="Markdown")
            return

        elif data == "admin_do_broadcast":
            b_text = context.user_data.get("pending_broadcast_text")
            if not b_text:
                await query.edit_message_text("No message found to broadcast.", parse_mode="Markdown")
                return

            all_user_ids = get_all_user_ids()
            await query.edit_message_text(f"Broadcasting to {len(all_user_ids)} users... please wait.", parse_mode="Markdown")

            success_cnt = 0
            failed_cnt = 0
            for uid in all_user_ids:
                try:
                    await context.bot.send_message(chat_id=uid, text=b_text, parse_mode="Markdown")
                    success_cnt += 1
                    await asyncio.sleep(0.05)
                except Exception:
                    failed_cnt += 1

            context.user_data["pending_broadcast_text"] = None
            report = (
                "*BROADCAST COMPLETED!*\n"
                "──────────────────────────\n"
                f"• Successful : `{success_cnt}` users\n"
                f"• Failed/Blocked: `{failed_cnt}` users\n"
                f"• Total Target : `{len(all_user_ids)}` users\n"
                "──────────────────────────"
            )
            await query.message.reply_text(report, parse_mode="Markdown", reply_markup=ADMIN_PANEL_KEYBOARD)
            return

    # --- GENERAL USER INLINE ACTIONS ---
    if data.startswith("select_proxy:"):
        proxy_name = data.split(":", 1)[1]
        set_user_proxy(user.id, proxy_name)
        
        keyboard = [
            [InlineKeyboardButton(f"{proxy_name} (Active)", callback_data=f"select_proxy:{proxy_name}", style="success")],
            [InlineKeyboardButton("Check Username Now", callback_data="prompt_user", style="primary")]
        ]
        await query.edit_message_text(
            f"Success! প্রক্সি গেটওয়ে হিসেবে `{proxy_name}` সফলভাবে সিলেক্ট করা হয়েছে。\n\n"
            "এখন 'Check Username Now' বাটনে ক্লিক করে অথবা 'User' বাটনে চেপে আপনার ইউজারনেম চেক করতে পারেন।",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "prompt_user":
        context.user_data["waiting_for_username"] = True
        await query.message.reply_text(
            "Send me your proxy username and wait a minute...\n\n"
            "আপনার প্রক্সি ইউজারনেমটি লিখে মেসেজ পাঠান:",
            parse_mode="Markdown"
        )

    elif data.startswith("recheck:"):
        proxy_username = data.split(":", 1)[1]
        await perform_proxy_check(
            chat_id=query.message.chat_id,
            user_id=user.id,
            proxy_username=proxy_username,
            context=context,
            message_to_edit=query.message
        )

    elif data == "refresh_profile":
        user_info = get_user(user.id)
        history = get_user_history(user.id, limit=5)
        profile_text = format_profile(user_info, history)
        keyboard = [
            [
                InlineKeyboardButton("Check Proxy", callback_data="prompt_user", style="success"),
                InlineKeyboardButton("Refresh Profile", callback_data="refresh_profile", style="primary")
            ],
            [
                InlineKeyboardButton("How It Works", callback_data="show_about", style="primary")
            ]
        ]
        try:
            await query.edit_message_text(
                profile_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            pass

    elif data == "show_about":
        about_text = format_about()
        keyboard = [
            [
                InlineKeyboardButton("Check Proxy Now", callback_data="prompt_user", style="success"),
                InlineKeyboardButton("Select Gateway", callback_data="select_proxy:H143Proxy", style="primary")
            ]
        ]
        await query.message.reply_text(
            about_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def post_init(application):
    """Sets bot commands and chat menu button."""
    commands = [
        BotCommand("start", "Start Bot"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("Bot commands and chat menu button configured successfully.")
    except Exception as e:
        logger.warning(f"Could not set bot commands: {e}")


class RenderHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK - H143 Proxy Checker Bot is Live & Healthy!")

    def log_message(self, format, *args):
        pass  # Suppress console logging


def start_render_health_server():
    """
    Starts a background HTTP health server for Render Web Service.
    Render requires an open port to pass health checks and prevent deployment timeout.
    """
    port_str = os.environ.get("PORT")
    if not port_str:
        return
    try:
        port = int(port_str)
        server = HTTPServer(("0.0.0.0", port), RenderHealthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"Render Web Service Health Server successfully listening on 0.0.0.0:{port}")
    except Exception as e:
        logger.warning(f"Could not start Render health server: {e}")


def main():
    """Starts the Telegram Bot."""
    init_db()
    start_render_health_server()

    if not BOT_TOKEN:
        print("\n" + "=" * 60)
        print("ERROR: BOT_TOKEN is not configured!")
        print("Please open the .env file in this directory and enter your Telegram Bot Token:")
        print("BOT_TOKEN=your_token_from_botfather")
        print("=" * 60 + "\n")
        return

    logger.info("Initializing H143 Proxy Checker Bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("restart", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", handle_about_button))
    app.add_handler(CommandHandler("admin", open_admin_panel))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    print("\n" + "=" * 60)
    print("🚀 H143 Proxy Checker Bot is successfully RUNNING!")
    print(f"Admin ID Authorized: {ADMIN_ID}")
    print("API Endpoint configured: https://h143.xyz/stats")
    print("Press Ctrl+C to stop the bot.")
    print("=" * 60 + "\n")

    app.run_polling()


if __name__ == "__main__":
    main()
