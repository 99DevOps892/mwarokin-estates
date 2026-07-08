# .env file (add to .gitignore!)
API_KEY=your_secret_key_here
ANOTHER_KEY=another_secret

# Access in code
import os
api_key = os.getenv('API_KEY')