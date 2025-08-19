import os
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from handlers import start_command, balance_command, getaccount_command, get_account_callback, myaccounts_command, code_callback, rem_callback, admin_command, addcredit_command, setcredit_command, userbalance_command, admin_add_credit_callback, admin_user_balance_callback, admin_list_users_callback, admin_inventory_callback, add_number_command
from db import SessionLocal, engine, setup_db
from models import Base

load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_health_check_server():
    port = int(os.getenv("PORT", 8080)) # Default to 8080 if PORT not set
    server_address = ('', port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    print(f"Starting health check server on port {port}")
    httpd.serve_forever()

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("getaccount", getaccount_command))
    application.add_handler(CallbackQueryHandler(get_account_callback, pattern="^get_account$"))
    application.add_handler(CommandHandler("myaccounts", myaccounts_command))
    application.add_handler(CallbackQueryHandler(code_callback, pattern=r"^code:\d+$"))
    application.add_handler(CallbackQueryHandler(rem_callback, pattern=r"^rem:\d+$"))

    # Admin commands
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("addcredit", addcredit_command))
    application.add_handler(CommandHandler("setcredit", setcredit_command))
    application.add_handler(CommandHandler("userbalance", userbalance_command))
    application.add_handler(CommandHandler("addnumber", add_number_command))
    application.add_handler(CallbackQueryHandler(admin_add_credit_callback, pattern="^admin_add_credit$"))
    application.add_handler(CallbackQueryHandler(admin_user_balance_callback, pattern="^admin_user_balance$"))
    application.add_handler(CallbackQueryHandler(admin_list_users_callback, pattern="^admin_list_users$"))
    application.add_handler(CallbackQueryHandler(admin_inventory_callback, pattern="^admin_inventory$"))

    # Initialize database (create tables if they don't exist) and setup SessionLocal
    setup_db(Base.metadata)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # Start the health check server in a separate thread
    health_check_thread = threading.Thread(target=run_health_check_server)
    health_check_thread.daemon = True  # Allow the main program to exit even if this thread is running
    health_check_thread.start()
    main()