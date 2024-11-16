import os
import json
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.error import RetryAfter

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
BOT_TOKEN = "7858062770:AAGfBC6-6DSWEoujKLDgkK4VSY3CTPwr-4A"
OWNER_ID = 1653775890

# Config file path
CONFIG_FILE = 'config.json'

# Load or create config
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {CONFIG_FILE}. Using default configuration.")
        except Exception as e:
            logger.error(f"Error reading {CONFIG_FILE}: {e}")
    
    # Return default configuration if file doesn't exist or there's an error
    return {
        'source_id': None,
        'destination_id': None,
        'bot_token': None,
        'owner_id': None
    }

# Save config
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# Load initial config
config = load_config()

async def start(update: Update, context):
    await update.message.reply_text('Hello! I am a message forwarding bot. Use /help to see available commands.')

async def help_command(update: Update, context):
    help_text = """
Available commands:
/setsource <channel_id> - Set the source channel/group/forum ID
/setdestination <channel_id> - Set the destination channel ID
/config - Show current configuration
/help - Show this help message
"""
    await update.message.reply_text(help_text)

async def set_source(update: Update, context):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You're not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Please provide the source channel/group/forum ID.")
        return

    config['source_id'] = int(context.args[0])
    save_config(config)
    await update.message.reply_text(f"Source ID set to: {config['source_id']}")

async def set_destination(update: Update, context):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You're not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Please provide the destination channel ID.")
        return

    config['destination_id'] = int(context.args[0])
    save_config(config)
    await update.message.reply_text(f"Destination ID set to: {config['destination_id']}")

async def show_config(update: Update, context):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You're not authorized to use this command.")
        return

    config_text = f"Source ID: {config['source_id']}\nDestination ID: {config['destination_id']}"
    await update.message.reply_text(config_text)

async def forward_message(update: Update, context):
    if update.effective_chat.id != config['source_id']:
        return

    if not config['destination_id']:
        logger.warning("Destination channel not set. Skipping forwarding.")
        return

    try:
        # Check if the message is part of a media group
        if update.message.media_group_id:
            # If it's the first message in the group, forward the entire group
            if not hasattr(context.bot_data, 'last_media_group_id') or context.bot_data.last_media_group_id != update.message.media_group_id:
                media_group = await context.bot.get_media_group(update.effective_chat.id, update.message.message_id)
                media = [msg.effective_attachment for msg in media_group]
                await context.bot.send_media_group(chat_id=config['destination_id'], media=media)
                context.bot_data.last_media_group_id = update.message.media_group_id
        else:
            # If it's not part of a media group, forward as before
            await context.bot.copy_message(
                chat_id=config['destination_id'],
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
    except RetryAfter as err:
        logger.warning(f"Rate limit exceeded. Retrying after {err.retry_after} seconds.")
        await asyncio.sleep(err.retry_after)
        await forward_message(update, context)
                
    except Exception as e:
        logger.error(f"Error forwarding message: {e}")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("setsource", set_source))
    application.add_handler(CommandHandler("setdestination", set_destination))
    application.add_handler(CommandHandler("config", show_config))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_message))

    application.run_polling()

if __name__ == '__main__':
    main()
