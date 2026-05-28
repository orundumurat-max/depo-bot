import os
import logging
from telegram.ext import ApplicationBuilder
TOKEN = os.environ.get("TOKEN")
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    app.run_polling()
