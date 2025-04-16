import os
import logging
import traceback
import asyncio
import nest_asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from deal_analyzer import DealAnalyzer
from sheets_manager import SheetsManager
from deck_browser import DeckBrowser

# Load environment variables
load_dotenv()

#重新串回 Event Loop
nest_asyncio.apply()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DealSourcingBot:
    def __init__(self):
        logger.debug("Initializing Bots...")
        self.deck_browser = DeckBrowser()
        self.deal_analyzer = DealAnalyzer()
        self.sheets_manager = SheetsManager()
        logger.debug("Initialization complete")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Start command received from user {update.effective_user.id}")
        await update.message.reply_text(
            'Welcome to VC Deal Sourcing Bot! Send me information about potential deals, '
            'and I will analyze and organize them for you.'
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            message = update.message
            chat_id = message.chat_id
            logger.info(f"Received message from user {chat_id}: {message.text[:100]}...")  # Log first 100 chars
            
            # Inform user that processing has started
            processing_msg = await message.reply_text("Processing your message...")
            
            # Browse the provided deck
            logger.info("Starting deck browsing...")
            try:
                deck_data = await self.deck_browser.process_input(message.text, message.attachments)
                logger.info(f"Deck browsing complete. Data: {str(deck_data)[:100]}...")  # Log first 100 chars
            except Exception as e:
                logger.error(f"Error in deck browsing: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Analyze the message
            logger.info("Starting message analysis...")
            try:
                # Analyze the deal with the summary
                deal_data = await self.deal_analyzer.analyze_deal(message.text, deck_data)
                logger.info(f"Analysis complete. Deal data: {str(deal_data)[:100]}...")  # Log first 100 chars
            except Exception as e:
                logger.error(f"Error in deal analysis: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Save to Google Sheets
            logger.info("Saving to Google Sheets...")
            try:
                sheet_url = await self.sheets_manager.save_deal(deal_data, deck_data)
                logger.info(f"Data saved to sheets successfully. URL: {sheet_url}")
            except Exception as e:
                logger.error(f"Error saving to sheets: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Format founder information for the response
            founder_info = deal_data.get('founder_information', [])
            founder_text = ""
            if founder_info:
                founder_text = "\nFounders:\n" + "\n".join(
                    f"• {founder['name']}" for founder in founder_info
                )
            
            # Reply with results
            try:
                await processing_msg.edit_text(
                    f"✅ Analysis complete!\n\n"
                    f"Company: {deal_data['company_name']}{founder_text}\n\n"
                    f"Details saved to: {sheet_url}"
                )
                logger.info("Response sent to user")
            except Exception as e:
                logger.error(f"Error sending response: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            await message.reply_text(
                "Sorry, there was an error processing your message. Please try again.\n"
                f"Error: {str(e)}"
            )
    
    
    #實際執行主程式
async def run_bot():
    # 設定工作目錄
    os.chdir(os.getenv("WORKING_DIRECTORY"))
    
    logger.info("Initializing bot...")
    bot = DealSourcingBot() # 初始化主 bot，包括 DealAnalyzer 與 SheetsManager
    
    # Create application
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    
    # 錯誤處理（避免崩潰）
    async def error_handler(update: Update, context):
        logger.error(f"❌ Bot error: {context.error}")
    application.add_error_handler(error_handler)
    
    # 清除 webhook 並丟掉舊 update
    await application.bot.delete_webhook(drop_pending_updates=True)
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))

    # Start the bot
    print("Starting bot...")
    logger.info("Bot is starting...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)
    print("Bot stopped.")

#實際觸發點
if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("Bot stopped by user.")
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        logger.error(traceback.format_exc())