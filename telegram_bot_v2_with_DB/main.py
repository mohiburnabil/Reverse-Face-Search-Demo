import time
import traceback
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import pillow_heif
import logging
from PIL import Image
import io
import os
import asyncio
import utils
import aiohttp  
import utils
from dotenv import load_dotenv
import uuid
import requests
import shutil
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
lock = asyncio.Lock()


# Define the /start command handler
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Hello! Send me an image, and I'll describe it for you.")

async def send_image(path, chat_id, bot: Bot):
    """
    Helper function to send a single image.
    """
    try:
        with open(path, 'rb') as image_file:
            await bot.send_photo(chat_id=chat_id, photo=image_file)
        print(f"Sent image: {path}")
    except Exception as e:
        print(f"Error sending image {path}: {e}")

async def send_images(image_paths, chat_id, bot: Bot):
    """
    Sends images concurrently to the specified Telegram chat.
    """
    tasks = [send_image(path, chat_id, bot) for path in image_paths]
    await asyncio.gather(*tasks)



async def facecheck_call(image_path,chat_id, bot):
    initial_summary= ''
    updated_summary = ''
    FACE_CHECK_API =  os.getenv("FACE_CHECK_API")
    SUMMARY_GENERATION_API = os.getenv("SUMMARY_GENERATION_API")
    form_data = aiohttp.FormData()
    form_data.add_field('file', open(image_path, 'rb'), filename='image.jpg', content_type='image/jpeg')

    async with aiohttp.ClientSession() as session:
        # First API call
        async with session.post(FACE_CHECK_API, data=form_data) as response1:
            if response1.status == 200:
                face_check_response = await response1.json()
                # need to handale the case if result1 is response['error'].code:

                try:
                    response = face_check_response['face_check_response']
                    filtered_urls = await utils.get_best_urls(response)
                    initial_summary+=await utils.get_best_urls_summary(filtered_urls)
                    print('got initial Summary.')
                except Exception as e:
                    if 'error' in face_check_response:
                        print(f"Error in face check API: {face_check_response['error']}")
                        initial_summary = f'Sorry, We Couldn\'t find the person in the image. Please try again with a different image.'
                        async with lock:
                            print("📤 Sending image and first summary to Telegram")
                            await send_image(image_path, chat_id, bot)
                            sent_message = await bot.send_message(chat_id=chat_id, text=initial_summary)
                            face_check_time = time.time() - start_time
                            print(f"✅ face check completed for {image_path} in {face_check_time:.2f} seconds")
                            return
            

            else:
                print(f'Error in summary process..    {response1.status}')
                response = {"error": f"🚫 First API failed. HTTP status: {response1.status}"}
                      

        # Send image and initial summary
    async with lock:
        print("📤 Sending image and first summary to Telegram")
        await send_image(image_path, chat_id, bot)
        sent_message = await bot.send_message(chat_id=chat_id, text=initial_summary)
  
    print(f"🔄 Sending image to second API for further processing: image path: {image_path}")
    absolute_image_path = os.path.abspath(image_path)
    payload2 = {'response':face_check_response, 'image_path': absolute_image_path}

    async with aiohttp.ClientSession() as session:
        async with session.get(SUMMARY_GENERATION_API, json=payload2) as response2:
            if response2.status == 200:
                result2 = await response2.json()
                updated_summary = result2['result']
                final_text = f"📝 Updated Summary:\n{updated_summary}"
            else:
                final_text = f"⚠️ Second API failed. HTTP status: {response2.status}"
                print(final_text)
    
    # Edit the original message
    print("✏️ Editing Telegram message with final summary")
    print("adding data to the database")
    try:
        await db_insert(image_path, updated_summary)
    except Exception as e:
        print(f"Error inserting data into the database: {e}")
        final_text += "\n\n⚠️ Error occurred while saving to the database."
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=sent_message.message_id,
        text=final_text
    )



async def db_insert(image_path, summary):
    DB_INSERT_ENDPOINT = os.getenv("DB_INSERT_ENDPOINT")

    files = {'image': open(image_path, 'rb')}
    data = {'summary': summary}

    response = requests.post(DB_INSERT_ENDPOINT, files=files, data=data)
    print(response.json())



async def db_search(image_path, chat_id, bot,context):

    unique_id = str(uuid.uuid4())

    original_ext = os.path.splitext(image_path)[1]  
    new_filename = f"{unique_id}{original_ext}"
    
    deep_search_dir = os.path.join(os.path.dirname(image_path), 'deep_search_images')
    os.makedirs(deep_search_dir, exist_ok=True)
    new_path = os.path.join(deep_search_dir, new_filename)

    shutil.copy(image_path, new_path)

    if "pending_images" not in context.chat_data:
        context.chat_data["pending_images"] = {}
    context.chat_data["pending_images"][unique_id] = new_path
  
    DB_SEARCH_ENDPOINT = os.getenv("DB_SEARCH_ENDPOINT")
    files = {'image': open(image_path, 'rb')}
    response = requests.post(DB_SEARCH_ENDPOINT, files=files)
    response = response.json()
    print(f"Response from search API: {response}")
    
    matches = response.get("matches", [])
    if not matches:
        print("No internal match found.")
        return False
    else:
        top_match = matches[0]
        score = top_match.get("score", 0.0)

        if score > 0.45:
            metadata = top_match.get("metadata", {})
            summary = metadata.get("summary", "No summary available.")
           
            df_summary = f"Our Internal Search Results\n{summary}"

            async with lock:
                print("📤 Sending image and db summary to Telegram")
                await send_image(image_path, chat_id, bot)
                
                # Send summary message
                db_message = await bot.send_message(chat_id=chat_id, text=df_summary)

                # Add "Deep Search" button
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Do a Deep Search", callback_data=f"deepsearch|{unique_id}")]
                ])
                await bot.send_message(chat_id=chat_id, text="Would you like to do a deep search?", reply_markup=keyboard)
                return True
        return False



async def generate_summary(image_path: str, chat_id,context, processing_message):
    bot = context.bot
    start_time = time.time()  # Start timer
    print(f"Processing image: {image_path}")
    face_check_time = 0
    # bot: Bot = context.bot
   
    
    
    try:
        with open(image_path, 'rb') as image_file:
            image = Image.open(image_file)
            size = image.size
            print(f"Image size: {size}")

            if size[0] < 60 or size[1] < 60:
                result_text = "🚫 Image too small (minimum 60x60 required)."
                async with lock:
                    await send_image(image_path, chat_id, bot)
                    await bot.send_message(chat_id=chat_id, text=result_text)
                return




        db_seach_status = await db_search(image_path, chat_id, bot,context)
        if not db_seach_status:
            # Call the facecheck API
            print("No Entry in the database...🔄 Calling facecheck API...")
            await facecheck_call(image_path, chat_id, bot)

        

    except Exception as e:
        # Get the full traceback as a string
        tb = traceback.format_exc()

        # Log or print a more informative error message
        error_message = (
            f"❌ Error processing image: {image_path}\n"
            f"🔍 Exception: {type(e).__name__}: {e}\n"
            f"📄 Traceback:\n{tb}"
        )
        print(error_message)

        # Optionally send a simpler error to the user
        await send_image(image_path, chat_id, bot)
        await bot.send_message(
            chat_id=chat_id,
            text="🚫 Internal error while summarizing the image. Please try again later or contact support."
        )


    end_time = time.time()  # End timer
    elapsed_time = end_time - start_time
    backend_time = elapsed_time - face_check_time
    print(f"⏱️ Backend processing time: {backend_time:.2f} seconds")
    print(f"⏱️ Total processing time: {elapsed_time:.2f} seconds")
    # print(f"✅ Summary generation completed for {image_path} in {elapsed_time:.2f} seconds")




async def get_summaries(image_paths, chat_id, context,processing_message):
    await asyncio.gather(*(generate_summary(path, chat_id, context,processing_message) for path in image_paths))


async def deep_search_callback(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    # Extract unique_id
    _, unique_id = query.data.split('|')

    # Get image path from stored dict
    image_path = context.chat_data.get("pending_images", {}).get(unique_id)

    if not image_path:
        await context.bot.send_message(chat_id=chat_id, text="❌ Could not find image for this deep search.")
        return

    await context.bot.send_message(chat_id=chat_id, text="🔎 Performing deep search. Please wait...")

    try:
        await facecheck_call(image_path, chat_id, context.bot)
    except Exception as e:
        tb = traceback.format_exc()
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Deep search failed: {e}\n\nTraceback:\n{tb}"
        )



async def handle_document(update: Update, context: CallbackContext) -> None:
    start_time = time.time()  # Start timer
    if update.message.photo:
        # If the user uploaded an image in photo mode
        await update.message.reply_text(
            "❌ It looks like you uploaded an image in regular photo mode. "
            "To Seach the image, please upload it as a document by selecting "
            "'File' instead of 'Gallery' when uploading."
        )
        return
    processing_message = await update.message.reply_text("🔄 Processing your image...")
    # Proceed if the uploaded file is a document
    document = update.message.document
   
    # Check if the document is an image
    pillow_heif.register_heif_opener()
    if document.mime_type.startswith('image/'):
        document_file = await context.bot.get_file(document.file_id)
        file_bytes = await document_file.download_as_bytearray()
        image = Image.open(io.BytesIO(file_bytes))

        try:
            chat_id = update.message.chat_id
            # bot_version = 'v3.0'
            result = utils.face_detection_api(image,chat_id)
            end_time = time.time()
            print(f"Image processing took {end_time - start_time:.2f} seconds")
            if result:
                print('got face detection result')
                await get_summaries(result, chat_id, context,processing_message)

                await update.message.reply_text("✅ Analysis complete!\n\n")

            else:
                await update.message.reply_text("🚫📷Detected faces are too small. Please try uploading a higher-quality image for better results.")
            # try:
            #     directory = '/workspace/meta-glass/backend'
            #     [os.remove(os.path.join(directory, f)) for f in os.listdir(directory) if (f.startswith('selected_') and f.endswith('.html'))]
            # except Exception as e:
            #     print(f'Cannot remove the html as {e}')
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            print(e)
            await update.message.reply_text("Sorry, I couldn't process the document.")
    else:
        await update.message.reply_text("Please upload a valid image file.")



# Define the error handler
async def error(update: Update, context: CallbackContext) -> None:
    logger.warning(f"Update {update} caused error {context.error}")

# Main function to set up the bot
def main():

    TOKEN = os.getenv('TELEGRAM_BOT_V2_2')
    application = Application.builder().token(TOKEN).build()

    # Add command and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_document))

    application.add_handler(CallbackQueryHandler(deep_search_callback, pattern=r'^deepsearch\|'))

    # Run the bot
    application.run_polling()


if __name__ == '__main__':
    main()
