import os
from dotenv import load_dotenv

load_dotenv()

LOCATIONIQ_API_KEY = os.getenv("LOCATIONIQ_API_KEY", "")
LOCATIONIQ_URL = "https://us1.locationiq.com/v1/search.php"

AFRICAS_TALKING_USERNAME = os.getenv("AFRICAS_TALKING_USERNAME", "sandbox")
AFRICAS_TALKING_API_KEY = os.getenv("AFRICAS_TALKING_API_KEY", "")
AFRICAS_TALKING_URL = "https://api.africastalking.com/version1/messaging"
