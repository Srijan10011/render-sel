import logging
import httpx
import random
import datetime
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import get_session
from models import User, Assignment, Number, StatusEnum, CreditTransaction, ReasonEnum

logger = logging.getLogger(__name__)

# In-memory rate limiter for code callbacks
_last_code_request_time = {}
RATE_LIMIT_SECONDS = 10  # 10 seconds cooldown for fetching codes


async def is_admin(user_tg_id: int) -> bool:
    with get_session() as session:
        user = session.query(User).filter_by(tg_id=user_tg_id).first()
        return user and user.is_admin


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user_tg_id = update.effective_user.id
    username = update.effective_user.username

    with get_session() as session:
        user = session.query(User).filter_by(tg_id=user_tg_id).first()
        if not user:
            user = User(tg_id=user_tg_id, username=username)
            session.add(user)
            session.commit()
            session.refresh(user)

        keyboard = [[InlineKeyboardButton("Get account", callback_data="get_account")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Welcome! Your current balance is {user.credits} credits.",
            reply_markup=reply_markup,
        )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current credits."""
    user_tg_id = update.effective_user.id

    with get_session() as session:
        user = session.query(User).filter_by(tg_id=user_tg_id).first()
        if user:
            await update.message.reply_text(f"Your current balance is {user.credits} credits.")
        else:
            await update.message.reply_text("You don't have an account yet. Use /start to create one.")


async def getaccount_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /getaccount command."""
    await get_account_logic(update, context)


async def get_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Get account' button callback."""
    query = update.callback_query
    await query.answer()
    await get_account_logic(update, context, is_callback=True)


async def get_account_logic(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    user_tg_id = update.effective_user.id
    message_sender = update.callback_query.message if is_callback else update.message

    with get_session() as session:
        user = session.query(User).filter_by(tg_id=user_tg_id).first()

        if not user or user.credits < 1:
            await message_sender.reply_text("Insufficient credits.")
            return

        free_number = session.query(Number).filter_by(status=StatusEnum.free).first()

        if not free_number:
            await message_sender.reply_text("No numbers available.")
            return

        # Deduct credit
        user.credits -= 1
        session.add(user)

        # Record transaction
        credit_tx = CreditTransaction(
            user_id=user.id,
            delta=-1,
            reason=ReasonEnum.get_account,
            meta={"description": "Deducted for getting an account"}
        )
        session.add(credit_tx)

        # Assign number
        free_number.status = StatusEnum.assigned
        session.add(free_number)

        assignment = Assignment(
            user_id=user.id,
            number_id=free_number.id,
            assigned_at=datetime.datetime.utcnow(),
            active=True
        )
        session.add(assignment)
        session.commit()
        session.refresh(assignment)

        keyboard = [
            [InlineKeyboardButton("Get code", callback_data=f"code:{assignment.id}")],
            [InlineKeyboardButton("Remove number", callback_data=f"rem:{assignment.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await message_sender.reply_text(
            f"Assigned number: {free_number.phone}\ncode:",
            reply_markup=reply_markup
        )


async def myaccounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List user's active assignments."""
    user_tg_id = update.effective_user.id

    with get_session() as session:
        user = session.query(User).filter_by(tg_id=user_tg_id).first()
        if not user:
            await update.message.reply_text("You don't have any accounts yet.")
            return

        active_assignments = (
            session.query(Assignment)
            .filter_by(user_id=user.id, active=True)
            .join(Number)
            .all()
        )

        if not active_assignments:
            await update.message.reply_text("You don't have any active assignments.")
            return

        for assignment in active_assignments:
            number = session.query(Number).filter_by(id=assignment.number_id).first()
            if number:
                keyboard = [
                    [InlineKeyboardButton("Get code", callback_data=f"code:{assignment.id}")]
                ]
                if not assignment.code_fetched_at:
                    keyboard.append([InlineKeyboardButton("Remove number", callback_data=f"rem:{assignment.id}")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"Number: {number.phone}\nLast code: {assignment.last_code if assignment.last_code else 'None'}",
                    reply_markup=reply_markup
                )


async def code_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Get code' button callback."""
    query = update.callback_query
    await query.answer()
    assignment_id = int(query.data.split(":")[1])
    user_tg_id = update.effective_user.id

    # Rate limiting
    current_time = time.time()
    if user_tg_id in _last_code_request_time and \
       (current_time - _last_code_request_time[user_tg_id]) < RATE_LIMIT_SECONDS:
        remaining_time = int(RATE_LIMIT_SECONDS - (current_time - _last_code_request_time[user_tg_id]))
        await query.edit_message_text(f"Please wait {remaining_time} seconds before requesting another code.")
        return
    _last_code_request_time[user_tg_id] = current_time

    with get_session() as session:
        assignment = session.query(Assignment).filter_by(id=assignment_id).first()
        if not assignment:
            await query.edit_message_text("Assignment not found.")
            return

        number = session.query(Number).filter_by(id=assignment.number_id).first()
        if not number:
            await query.edit_message_text("Number not found for this assignment.")
            return

        # Fetch code
        try:
            code = await fetch_code(number.gs_token)
        except Exception as e:
            logger.error(f"Error fetching code for assignment {assignment.id}: {e}")
            await query.edit_message_text("Temporary error fetching code. Try again.")
            return

        if code:
            assignment.last_code = code
            assignment.code_fetched_at = datetime.datetime.utcnow()
            session.add(assignment)
            session.commit()
            await query.edit_message_text(
                f"Number: {number.phone}\ncode: {code}"
            )
        else:
            await query.edit_message_text("No code found.")


async def rem_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Remove number' button callback."""
    query = update.callback_query
    await query.answer()
    assignment_id = int(query.data.split(":")[1])

    with get_session() as session:
        assignment = session.query(Assignment).filter_by(id=assignment_id).first()
        if not assignment:
            await query.edit_message_text("Assignment not found.")
            return

        if assignment.code_fetched_at:
            await query.edit_message_text("Cannot remove after code has been fetched.")
            return

        user = session.query(User).filter_by(id=assignment.user_id).first()
        number = session.query(Number).filter_by(id=assignment.number_id).first()

        if user and number:
            # Refund credit
            user.credits += 1
            session.add(user)

            credit_tx = CreditTransaction(
                user_id=user.id,
                delta=1,
                reason=ReasonEnum.refund_remove,
                ref_assignment_id=assignment.id,
                meta={"description": "Refund for removing number"}
            )
            session.add(credit_tx)

            # Release number
            number.status = StatusEnum.free
            session.add(number)

            # Deactivate assignment
            assignment.active = False
            assignment.released_at = datetime.datetime.utcnow()
            session.add(assignment)

            session.commit()
            await query.edit_message_text("Number removed. 1 credit refunded.")
        else:
            await query.edit_message_text("Error removing number.")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin menu."""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    keyboard = [
        [InlineKeyboardButton("Add credit", callback_data="admin_add_credit")],
        [InlineKeyboardButton("User balance", callback_data="admin_user_balance")],
        [InlineKeyboardButton("List users", callback_data="admin_list_users")],
        [InlineKeyboardButton("Inventory", callback_data="admin_inventory")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Admin Menu:", reply_markup=reply_markup)


async def admin_add_credit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder for admin add credit callback."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Please use /addcredit <@user_or_id> <amount> to add credits.")


async def admin_user_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder for admin user balance callback."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Please use /userbalance <@user_or_id> to check user balance.")


async def admin_list_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder for admin list users callback."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("List users functionality not yet implemented.")


async def admin_inventory_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder for admin inventory callback."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Inventory functionality not yet implemented.")


async def addcredit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add credits to a user."""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /addcredit <@user_or_id> <amount>")
        return

    target_user_str = context.args[0]
    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        return

    with get_session() as session:
        user = None
        if target_user_str.startswith("@"):
            username = target_user_str[1:]
            user = session.query(User).filter_by(username=username).first()
        else:
            try:
                user_id = int(target_user_str)
                user = session.query(User).filter_by(tg_id=user_id).first()
            except ValueError:
                pass
        
        if not user:
            await update.message.reply_text("User not found.")
            return

        user.credits += amount
        session.add(user)

        credit_tx = CreditTransaction(
            user_id=user.id,
            delta=amount,
            reason=ReasonEnum.admin_grant,
            meta={"admin_id": update.effective_user.id, "description": f"Admin added {amount} credits"}
        )
        session.add(credit_tx)
        session.commit()
        await update.message.reply_text(f"Successfully added {amount} credits to {user.username or user.tg_id}. New balance: {user.credits}")


async def setcredit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a user's credit balance."""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /setcredit <@user_or_id> <amount>")
        return

    target_user_str = context.args[0]
    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        return

    with get_session() as session:
        user = None
        if target_user_str.startswith("@"):
            username = target_user_str[1:]
            user = session.query(User).filter_by(username=username).first()
        else:
            try:
                user_id = int(target_user_str)
                user = session.query(User).filter_by(tg_id=user_id).first()
            except ValueError:
                pass
        
        if not user:
            await update.message.reply_text("User not found.")
            return

        old_credits = user.credits
        user.credits = amount
        session.add(user)

        credit_tx = CreditTransaction(
            user_id=user.id,
            delta=amount - old_credits,
            reason=ReasonEnum.admin_set_adjust,
            meta={"admin_id": update.effective_user.id, "description": f"Admin set credits to {amount}"}
        )
        session.add(credit_tx)
        session.commit()
        await update.message.reply_text(f"Successfully set credits for {user.username or user.tg_id} to {user.credits}")


async def userbalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check a user's credit balance."""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /userbalance <@user_or_id>")
        return

    target_user_str = context.args[0]

    with get_session() as session:
        user = None
        if target_user_str.startswith("@"):
            username = target_user_str[1:]
            user = session.query(User).filter_by(username=username).first()
        else:
            try:
                user_id = int(target_user_str)
                user = session.query(User).filter_by(tg_id=user_id).first()
            except ValueError:
                pass
        
        if not user:
            await update.message.reply_text("User not found.")
            return

        await update.message.reply_text(f"User {user.username or user.tg_id} has {user.credits} credits.")


async def fetch_code(gs_token: str) -> str:
    """Fetches SMS code from the external service."""
    url = f"http://ca.irbots.com:27/gs={gs_token}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes
            # Assuming the code is in the response body as text
            code = response.text.strip()
            return code
    except httpx.RequestError as e:
        logger.error(f"Error fetching code for gs_token {gs_token}: {e}")
        return None