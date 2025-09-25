import os
import logging
from waitress import serve
from dotenv import load_dotenv

from manuscript_app import main

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    
    app = main({})

    logging.info(f"Iniciando servidor...")
    serve(app, host='0.0.0.0', port=port)