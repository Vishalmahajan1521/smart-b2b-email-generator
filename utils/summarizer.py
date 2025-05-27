import streamlit as st
import google.generativeai as genai
import re
from datetime import datetime
import logging
from utils.config import gemini_api_key

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@st.cache_resource(ttl=3600)  # Cache Gemini configuration
def configure_gemini():
    if not gemini_api_key:
        raise ValueError("Gemini API key not found. Please set GEMINI_API_KEY in the .env file.")
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-001')
    return model

def summarize_news(article, model):
    try:
        title = article.get('title', '')
        description = article.get('description', '')
        content = article.get('content', '')
        full_content = article.get('full_content', '')
        if full_content and len(full_content) > 300:
            text_to_summarize = f"{title}. {full_content}"
        elif content and len(content) > 100:
            text_to_summarize = f"{title}. {content}"
        elif description:
            text_to_summarize = f"{title}. {description}"
        else:
            return title
        if len(text_to_summarize) < 50:
            return title

        company_name = article.get('company_name', '')
        key_entities = extract_key_entities(text_to_summarize, company_name)
        
        # Gemini API prompt for summarization
        prompt = f"""
        Summarize the following news article in 50-150 words, focusing on key points relevant to {company_name}. Ensure the summary is concise, professional, and captures critical business or industry insights. Include any mentioned financial figures, products, or strategic initiatives. Avoid redundant phrases like 'the article states.' If no specific details are available, provide a brief summary based on the title.

        Article: {text_to_summarize}
        """
        with st.spinner("Summarizing news with Gemini API..."):
            response = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 150,
                    "temperature": 0.6,
                    "top_p": 0.95
                }
            )
            summary = response.text.strip()
        
        # Ensure key entities and company name are included
        summary = ensure_entities_in_summary(summary, key_entities, company_name)
        
        # Add publication date if available
        if article.get('publishedAt'):
            try:
                pub_date = datetime.strptime(article.get('publishedAt')[:10], "%Y-%m-%d")
                date_str = pub_date.strftime("%B %d, %Y")
                summary = f"According to an article published on {date_str}, {summary}"
            except:
                pass
        
        summary = format_summary(summary)
        return summary
    except Exception as e:
        logger.error(f"Error summarizing article with Gemini API: {str(e)}")
        return article.get('title', 'Summary unavailable')

def extract_key_entities(text, company_name):
    entities = []
    if company_name:
        entities.append(company_name)
    product_pattern = r'\b[A-Z][a-zA-Z0-9]+ (?:API|Cloud|Platform|Suite|Service)\b'
    products = re.findall(product_pattern, text)[:2]
    entities.extend(products)
    money_pattern = r'\$\d+(?:\.\d+)?(?:\s?[mb]illion)?'
    money = re.findall(money_pattern, text)[:1]
    entities.extend(money)
    percentage_pattern = r'\d+(?:\.\d+)?%'
    percentages = re.findall(percentage_pattern, text)[:1]
    entities.extend(percentages)
    return list(set(entities))

def ensure_entities_in_summary(summary, entities, company_name):
    summary_lower = summary.lower()
    if company_name and company_name.lower() not in summary_lower:
        summary = f"In news related to {company_name}, {summary}"
    return summary

def format_summary(summary):
    redundant_phrases = [
        "according to the article",
        "the article states that",
        "the article notes that",
        "the article mentions that",
        "as mentioned in the article",
    ]
    for phrase in redundant_phrases:
        summary = re.sub(phrase, "", summary, flags=re.IGNORECASE)
    sentences = re.split(r'(?<=[.!?])\s+', summary)
    sentences = [s.strip().capitalize() for s in sentences if s.strip()]
    summary = " ".join(sentences)
    return summary
