# Telegram SMS Bot

This is a Telegram bot for renting temporary phone numbers to receive SMS codes.

## Features

- Get temporary phone numbers
- Fetch SMS codes for assigned numbers
- Remove numbers and get credit refunds
- Admin functionalities for credit management and user listing

## Setup

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd telegram-sms-bot
    ```

2.  **Create a virtual environment and install dependencies:**

    ```bash
    python -m venv venv
    ./venv/Scripts/activate  # On Windows
    source venv/bin/activate  # On macOS/Linux
    pip install -r requirements.txt
    ```

3.  **Environment Variables:**

    Create a `.env` file in the root directory of the project with the following content:

    ```env
    BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    DATABASE_URL="sqlite:///./bot.db" # Or your PostgreSQL connection string, e.g., postgresql+psycopg2://user:password@host:port/dbname
    ```

    -   `BOT_TOKEN`: Obtain this from BotFather on Telegram.
    -   `DATABASE_URL`: Connection string for your database. Defaults to a SQLite file `bot.db`.

4.  **Run Database Migrations:**

    ```bash
    python -m alembic upgrade head
    ```

5.  **Populate Numbers (Important!):

    Since you have real numbers, you'll need to insert them into the `numbers` table. 
    
    a. Open `insert_real_numbers.py` in the project directory.
    b. Modify the `numbers_to_insert` list with your actual phone numbers and their corresponding `gs_token`s. The `gs_token` is a unique identifier for your number in the external SMS service you are using to fetch codes.
    c. Run the script:

    ```bash
    python insert_real_numbers.py
    ```

    This will add your numbers to the database with a `free` status, making them available for assignment by the bot.

## Running the Bot

```bash
python main.py
```

## Commands

### User Commands

-   `/start`: Welcome message, show balance, and a "Get account" button.
-   `/balance`: Show your current credit balance.
-   `/myaccounts`: List your active number assignments with "Get code" and "Remove number" buttons.
-   `/getaccount`: Deduct 1 credit, assign a free number, and reply with the number and action buttons.

### Admin Commands (requires `is_admin=True` in the `users` table)

-   `/admin`: Show admin menu.
-   `/addcredit <@user_or_id> <amount>`: Increment a user's credit balance.
-   `/setcredit <@user_or_id> <amount>`: Set a user's credit balance.
-   `/userbalance <@user_or_id>`: Check a user's credit balance.

## Callback Data Format

-   `code:<assignment_id>`
-   `rem:<assignment_id>`

## Data Model

See `models.py` for the SQLAlchemy data model.