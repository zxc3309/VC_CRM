import os
import logging
import traceback
import asyncio
import nest_asyncio
from dotenv import load_dotenv
from telegram import Update, File
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from deal_analyzer import DealAnalyzer
from sheets_manager import GoogleSheetsManager
from deck_browser import DeckBrowser
from doc_manager import DocManager
from prompt_manager import GoogleSheetPromptManager
import tempfile # 導入 tempfile 模組

# Load environment variables
load_dotenv(override=True)

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
        self.doc_manager = DocManager()
        self.sheets_manager = GoogleSheetsManager()
        logger.debug("Initialization complete")
        self.prompt_manager = GoogleSheetPromptManager()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Start command received from user {update.effective_user.id}")
        await update.message.reply_text(
            'Welcome to VC Deal Sourcing Bot! Send me information about potential deals, '
            'and I will analyze and organize them for you.'
        )

    async def reload_prompt_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            # 直接調用儲存的 prompt_manager 實例的 reload_prompts 方法
            self.prompt_manager.reload_prompts()
            await update.message.reply_text("🔄 Prompt 已重新載入成功！")
        except Exception as e:
            await update.message.reply_text(f"❌ 重新載入失敗：{str(e)}")
            
    async def show_prompt_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        prompt_id = context.args[0] if context.args else "question_list1"
        prompt = self.prompt_manager.get_prompt(prompt_id)
        await update.message.reply_text(prompt or f"找不到 prompt: {prompt_id}")

    def register_handlers(self, application):
        application.add_handler(CommandHandler("reload_prompt", self.reload_prompt_command))
        application.add_handler(CommandHandler("show_prompt", self.show_prompt_command))

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # 使用一個列表來存儲需要清理的臨時文件路徑
        temp_files_to_clean = []
        try:
            message = update.message
            chat_id = message.chat_id
            
            # 獲取訊息文字，優先使用 caption
            message_text = message.caption if message.caption else message.text
            text_preview = message_text[:100] if message_text else "[No text]"
            logger.info(f"Received message from user {chat_id}: {text_preview}") # Log first 100 chars
            
            # 處理附件
            attachments = []
            if message.document:
                logger.info(f"Document received: {message.document.file_name} ({message.document.mime_type})")
                try:
                    tg_file = await context.bot.get_file(message.document.file_id)
                    file_bytes = await tg_file.download_as_bytearray()
                    
                    # 將文件內容保存到臨時文件
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(message.document.file_name)[1]) as tmp_file:
                        tmp_file.write(file_bytes)
                        temp_file_path = tmp_file.name
                        temp_files_to_clean.append(temp_file_path) # 添加到清理列表

                    attachments.append({
                        "name": message.document.file_name,
                        "path": temp_file_path, # 添加文件路徑
                        "mime_type": message.document.mime_type,
                    })
                    logger.info(f"Successfully downloaded and saved document to temporary file: {temp_file_path}")
                except Exception as e:
                    logger.error(f"Error downloading or saving document: {str(e)}")
                    raise
            
            # Inform user that processing has started
            processing_msg = await message.reply_text("Processing your message...")
            
            # Browse the provided deck
            logger.info("Starting deck browsing...")
            try:
                # 確保 message_text 不為 None
                message_text = message_text if message_text else ""
                deck_data = await self.deck_browser.process_input(message_text, attachments)
                logger.info(f"Deck browsing complete. Data: {str(deck_data)[:100]}...")  # Log first 100 chars
            except Exception as e:
                logger.error(f"Error in deck browsing: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Analyze the message
            logger.info("Starting message analysis...")
            try:
                # Analyze the deal with the summary
                analysis_result = await self.deal_analyzer.analyze_deal(message_text, deck_data)
                deal_data = analysis_result["deal_data"]
                input_data = analysis_result["input_data"]
                logger.info(f"Analysis complete. Deal data: {str(deal_data)[:100]}...")  # Log first 100 chars
            except Exception as e:
                logger.error(f"Error in deal analysis: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            #Save to Google Doc
            logger.info("Saving to Google Doc...")
            try:
                # 將 deal_data 和 input_data 都傳給 doc_manager
                result = await self.doc_manager.create_doc(deal_data, input_data)
                doc_url = result["doc_url"]
                logger.info(f"Data saved to Google Doc successfully. URL: {doc_url}")
                
            except Exception as e:
                logger.error(f"Error saving to Google Doc: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Save to Google Sheets
            logger.info("Saving to Google Sheets...")
            try:
                # 將 deal_data 和 input_data 都傳給 sheets_manager
                sheet_url = await self.sheets_manager.save_deal(deal_data, input_data, doc_url)
                logger.info(f"Data saved to sheets successfully. URL: {sheet_url}")
            except Exception as e:
                logger.error(f"Error saving to sheets: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Format founder information for the response
            founder_names = deal_data.get('founder_name', [])
            founder_text = ""
            if founder_names:
                founder_text = "\nFounders:\n" + "\n".join(
                    f"• {name}" for name in founder_names
                )
            
            # Reply with results
            try:
                await processing_msg.edit_text(
                    f"✅ Analysis complete!\n\n"
                    f"Company: {deal_data.get('company_name', 'N/A')}{founder_text}\n\n"
                    f"Log saved to: {doc_url}\n\n"
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
        finally:
            # 清理臨時文件
            for temp_file in temp_files_to_clean:
                try:
                    os.remove(temp_file)
                    logger.info(f"Cleaned up temporary file: {temp_file}")
                except OSError as e:
                    logger.error(f"Error removing temporary file {temp_file}: {e}")

    
    #實際執行主程式
async def run_bot():
    # 設定工作目錄
    
    working_dir = os.getenv("WORKING_DIRECTORY", "/app")
    os.makedirs(working_dir, exist_ok=True)
    os.chdir(working_dir)
    
    logger.info("Initializing bot...")
    bot = DealSourcingBot() # 初始化主 bot，包括 DealAnalyzer 與 SheetsManager
    
    # Create application
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    
    # 註冊 handlers
    bot.register_handlers(application)

    # 錯誤處理（避免崩潰）
    async def error_handler(update: Update, context):
        logger.error(f"❌ Bot error: {context.error}")
    application.add_error_handler(error_handler)
    
    # 清除 webhook 並丟掉舊 update
    await application.bot.delete_webhook(drop_pending_updates=True)
    application.add_handler(CommandHandler("start", bot.start))
    
    # 更新消息處理器以接受更多文件類型
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.Document.ALL) & ~filters.COMMAND,
        bot.handle_message
    ))

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
