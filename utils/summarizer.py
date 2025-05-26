import streamlit as st
from transformers import BartTokenizer, BartForConditionalGeneration
import re
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@st.cache_resource
def load_summarization_model():
    model_name = "facebook/bart-large-cnn"
    tokenizer = BartTokenizer.from_pretrained(model_name)
    model = BartForConditionalGeneration.from_pretrained(model_name)
    return tokenizer, model

def summarize_news(article, tokenizer, model):
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
        inputs = tokenizer(text_to_summarize, max_length=1024, truncation=True, return_tensors="pt")
        summary_ids = model.generate(
            inputs["input_ids"],
            max_length=200,
            min_length=100,
            length_penalty=2.0,
            num_beams=4,
            early_stopping=True
        )
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        summary = ensure_entities_in_summary(summary, key_entities, company_name)
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
        logger.error(f"Error summarizing article: {str(e)}")
        return article.get('title', 'Summary unavailable')

def extract_key_entities(text, company_name):
    entities = []
    if company_name:
        entities.append(company_name)
    product_pattern = r'\b[A-Z][a-zA-Z0-9]+ (?:[A-Z][a-zA-Z0-9]+ )*(?:API|Cloud|Platform|Suite|Service|Software|Hardware|Solution|Tool|App|Application)\b'
    products = re.findall(product_pattern, text)
    entities.extend(products[:3])
    money_pattern = r'\$\d+(?:\.\d+)?(?:\s?[mb]illion|\s?[mk]?)'
    money = re.findall(money_pattern, text)
    entities.extend(money[:2])
    percentage_pattern = r'\d+(?:\.\d+)?%'
    percentages = re.findall(percentage_pattern, text)
    entities.extend(percentages[:2])
    date_pattern = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}'
    dates = re.findall(date_pattern, text)
    entities.extend(dates[:2])
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