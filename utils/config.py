import os
from dotenv import load_dotenv
import nltk

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
news_api_key = os.getenv("NEWS_API")
serper_api_key = os.getenv("SERPER_API_KEY")

try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except:
    pass

DEFAULT_KEYWORDS = [
    "cloud", "AI", "artificial intelligence", "ML", "machine learning", 
    "digital transformation", "data", "security", "cyber", "automation", 
    "SaaS", "software", "hardware", "IT services", "tech", "IoT", 
    "blockchain", "DevOps", "API", "enterprise", "computing"
]

TECH_SOURCES = [
    "techcrunch.com", "wired.com", "arstechnica.com", "theverge.com", "spectrum.ieee.org",
    "cnbc.com", "bloomberg.com", "forbes.com", "zdnet.com", "venturebeat.com",
    "cio.com", "informationweek.com", "infoworld.com", "computerworld.com",
    "wsj.com", "reuters.com", "businessinsider.com", "techradar.com", "thenextweb.com",
    "theregister.com", "cnet.com", "engadget.com", "gizmodo.com", "slashdot.org",
    "protocol.com", "siliconangle.com", "fiercetelecom.com", "crn.com", "ciodive.com"
]

INDUSTRY_SOURCES = {
    "healthcare": ["healthcareitnews.com", "mobihealthnews.com", "medcitynews.com", "fiercehealthcare.com"],
    "finance": ["finextra.com", "financemagnates.com", "bankingdive.com", "fintechfutures.com"],
    "retail": ["retaildive.com", "retailwire.com", "modernretail.co", "chainstoreage.com"],
    "manufacturing": ["industryweek.com", "manufacturing.net", "automationworld.com"],
    "logistics": ["supplychaindive.com", "freightwaves.com", "logisticsmgmt.com"]
}