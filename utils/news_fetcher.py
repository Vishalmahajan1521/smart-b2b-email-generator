import streamlit as st
import requests
from datetime import datetime, timedelta
import json
import re
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from utils.config import serper_api_key, DEFAULT_KEYWORDS, TECH_SOURCES, INDUSTRY_SOURCES
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_content_from_url(article_url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(article_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.extract()
        text = soup.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', ' ', text)
        words = text.split()
        if len(words) > 800:
            text = ' '.join(words[:800]) + "..."
        return text
    except Exception as e:
        logger.error(f"Error extracting content from URL {article_url}: {str(e)}")
        return ""

def calculate_relevance_score(article_text, company_name, product_keywords, industry, is_competitor=False):
    text_lower = article_text.lower()
    company_lower = company_name.lower()
    relevance_score = 0
    relevance_details = {}
    company_count = text_lower.count(company_lower)
    company_score = min(company_count * 5, 25) if not is_competitor else min(company_count * 3, 15)
    relevance_score += company_score
    relevance_details["company_mentions"] = company_count
    company_variations = [f" {company_lower} ", f"{company_lower},", f"{company_lower}.", f"{company_lower}'s"]
    variation_count = sum(text_lower.count(var) for var in company_variations)
    relevance_score += min(variation_count * 2, 10) if not is_competitor else min(variation_count * 1, 5)
    keyword_matches = []
    for keyword in product_keywords:
        if keyword.lower() in text_lower:
            keyword_matches.append(keyword)
            relevance_score += 3 if not is_competitor else 2
    relevance_details["keyword_matches"] = keyword_matches
    industry_terms = DEFAULT_KEYWORDS + INDUSTRY_SOURCES.get(industry.lower(), [])
    industry_matches = []
    for term in industry_terms:
        if term.lower() in text_lower:
            industry_matches.append(term)
            relevance_score += 1
    relevance_details["industry_matches"] = industry_matches
    if isinstance(article_text, dict) and "publishedAt" in article_text:
        try:
            published_date = datetime.strptime(article_text["publishedAt"][:10], "%Y-%m-%d")
            days_ago = (datetime.now() - published_date).days
            recency_score = max(0, 10 - days_ago / 3)
            relevance_score += recency_score
            relevance_details["recency_days"] = days_ago
        except:
            pass
    if len(str(article_text)) < 500:
        relevance_score *= 0.7
    return relevance_score, relevance_details

def fetch_news(company_name, api_key, product_keywords, industry="tech", min_articles=3, max_articles=7, competitor_company=None):
    url = "https://newsapi.org/v2/everything"
    headers = {
        "User-Agent": "SmartB2BEmailGenerator/1.0",
        "Accept": "application/json"
    }
    if isinstance(product_keywords, str):
        product_keywords = [k.strip() for k in product_keywords.split(",") if k.strip()]
    keywords_to_use = product_keywords if product_keywords else DEFAULT_KEYWORDS[:5]
    base_query = f'"{company_name}"'
    keyword_query = " OR ".join([f'"{term}"' for term in keywords_to_use[:5]])
    from_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    to_date = datetime.now().strftime('%Y-%m-%d')
    request_count = max_articles  # Fetch exactly max_articles
    sources_to_use = TECH_SOURCES
    if industry.lower() in INDUSTRY_SOURCES:
        sources_to_use = TECH_SOURCES[:10] + INDUSTRY_SOURCES[industry.lower()]
    params = {
        "q": f'{base_query} AND ({keyword_query})',
        "language": "en",
        "sortBy": "relevancy",
        "from": from_date,
        "to": to_date,
        "pageSize": request_count,
        "apiKey": api_key,
    }
    articles = []
    with st.spinner(f"Fetching industry news for {company_name}..."):
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "ok" or not data.get("articles"):
                logger.warning(f"Trying simpler query for {company_name}")
                params["q"] = base_query
                response = requests.get(url, params=params, headers=headers)
                data = response.json()
            if data.get("status") == "ok" and data.get("articles"):
                api_articles = data["articles"]
                with ThreadPoolExecutor(max_workers=5) as executor:
                    article_texts = []
                    for article in api_articles[:max_articles]:  # Limit to max_articles
                        if not article.get("title") or not (article.get("description") or article.get("content")):
                            continue
                        article_text = {
                            "title": article.get("title", ""),
                            "description": article.get("description", ""),
                            "content": article.get("content", ""),
                            "url": article.get("url", ""),
                            "publishedAt": article.get("publishedAt", ""),
                            "source": article.get("source", {}).get("name", "Unknown Source"),
                            "company_name": company_name,
                            "is_competitor": False
                        }
                        if article.get("url") and len(article_text["content"]) < 500:
                            additional_content = extract_content_from_url(article.get("url"))
                            if additional_content:
                                article_text["full_content"] = additional_content
                        text_for_scoring = article_text["title"] + " " + article_text.get("description", "") + " " + article_text.get("content", "")
                        score, details = calculate_relevance_score(text_for_scoring, company_name, keywords_to_use, industry)
                        article_text["relevance_score"] = score
                        article_text["relevance_details"] = details
                        article_texts.append(article_text)
                article_texts.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
                articles = article_texts[:max_articles]

            # Fetch competitor news if provided
            competitor_articles = []
            competitor_max = min(2, max_articles)  # Limit competitor articles to 2 or max_articles
            if competitor_company:
                with st.spinner(f"Fetching news for competitor {competitor_company}..."):
                    params["q"] = f'"{competitor_company}" AND ({keyword_query})'
                    params["pageSize"] = competitor_max
                    try:
                        response = requests.get(url, params=params, headers=headers)
                        response.raise_for_status()
                        data = response.json()
                        if data.get("status") == "ok" and data.get("articles"):
                            api_articles = data["articles"]
                            with ThreadPoolExecutor(max_workers=5) as executor:
                                for article in api_articles[:competitor_max]:
                                    if not article.get("title") or not (article.get("description") or article.get("content")):
                                        continue
                                    article_text = {
                                        "title": article.get("title", ""),
                                        "description": article.get("description", ""),
                                        "content": article.get("content", ""),
                                        "url": article.get("url", ""),
                                        "publishedAt": article.get("publishedAt", ""),
                                        "source": article.get("source", {}).get("name", "Unknown Source"),
                                        "company_name": competitor_company,
                                        "is_competitor": True
                                    }
                                    if article.get("url") and len(article_text["content"]) < 500:
                                        additional_content = extract_content_from_url(article.get("url"))
                                        if additional_content:
                                            article_text["full_content"] = additional_content
                                    text_for_scoring = article_text["title"] + " " + article_text.get("description", "") + " " + article_text.get("content", "")
                                    score, details = calculate_relevance_score(text_for_scoring, competitor_company, keywords_to_use, industry, is_competitor=True)
                                    article_text["relevance_score"] = score
                                    article_text["relevance_details"] = details
                                    competitor_articles.append(article_text)
                            competitor_articles.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
                            competitor_articles = competitor_articles[:competitor_max]
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Failed to fetch competitor news for {competitor_company}: {str(e)}")

            articles.extend(competitor_articles)

            if len([a for a in articles if not a["is_competitor"]]) < min_articles and serper_api_key:
                backup_articles = search_google_news(company_name, product_keywords, industry, serper_api_key)
                seen_urls = {a.get("url") for a in articles}
                for article in backup_articles[:max_articles - len([a for a in articles if not a["is_competitor"]])]:
                    if article.get("url") not in seen_urls:
                        article["is_competitor"] = False
                        articles.append(article)
                        seen_urls.add(article.get("url"))
            if len([a for a in articles if not a["is_competitor"]]) < min_articles:
                logger.warning(f"Only found {len([a for a in articles if not a['is_competitor']])} relevant articles for {company_name}")
            return articles
        except requests.exceptions.RequestException as e:
            logger.error(f"API Request Error: {str(e)}")
            if serper_api_key:
                return search_google_news(company_name, product_keywords, industry, serper_api_key)
            return []

def search_google_news(company_name, product_keywords, industry, api_key):
    if not api_key:
        return []
    url = "https://google.serper.dev/search"
    if isinstance(product_keywords, str):
        product_keywords = [k.strip() for k in product_keywords.split(",") if k.strip()]
    keywords_to_use = product_keywords if product_keywords else DEFAULT_KEYWORDS[:3]
    query = f"{company_name} {' '.join(keywords_to_use[:3])}"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = json.dumps({
        "q": query,
        "gl": "us",
        "hl": "en",
        "num": 10,
        "type": "news"
    })
    with st.spinner(f"Searching alternate sources for {company_name} news..."):
        try:
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()
            data = response.json()
            articles = []
            if "news" in data:
                for item in data["news"]:
                    article = {
                        "title": item.get("title", ""),
                        "description": item.get("snippet", ""),
                        "content": item.get("snippet", ""),
                        "url": item.get("link", ""),
                        "publishedAt": item.get("date", ""),
                        "source": item.get("source", "Google Search"),
                        "company_name": company_name,
                        "is_competitor": False
                    }
                    if article["url"]:
                        additional_content = extract_content_from_url(article["url"])
                        if additional_content:
                            article["full_content"] = additional_content
                    text_for_scoring = article["title"] + " " + article.get("description", "") + " " + article.get("content", "")
                    score, details = calculate_relevance_score(text_for_scoring, company_name, product_keywords, industry)
                    article["relevance_score"] = score
                    article["relevance_details"] = details
                    articles.append(article)
            articles.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            return articles[:5]
        except Exception as e:
            logger.error(f"Google Search API Error: {str(e)}")
            return []