import streamlit as st
import pandas as pd
from datetime import datetime
from utils.config import DEFAULT_KEYWORDS

def analyze_news_relevance(articles_dict, summaries_dict, product_keywords):
    st.subheader("📊 News Relevance Analysis")
    if not articles_dict:
        st.info("No news data available.")
        return
    for company, articles in articles_dict.items():
        if not articles:
            continue
        with st.expander(f"Relevance Analysis for {company}"):
            metrics = []
            for article in articles:
                metrics.append({
                    'title': article.get('title', '')[:50] + "...",
                    'score': article.get('relevance_score', 0),
                    'company_mentions': article.get('relevance_details', {}).get('company_mentions', 0),
                    'keyword_matches': len(article.get('relevance_details', {}).get('keyword_matches', [])),
                    'date': article.get('publishedAt', '')[:10],
                    'source': article.get('source', 'Unknown'),
                    'is_competitor': article.get('is_competitor', False)
                })
            df = pd.DataFrame(metrics)
            if len(df) > 0:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Average Relevance Score", f"{df['score'].mean():.1f}")
                with col2:
                    st.metric("Company Mentions", f"{df['company_mentions'].sum()}")
                with col3:
                    st.metric("Keyword Matches", f"{df['keyword_matches'].sum()}")
                st.bar_chart(df.set_index('title')['score'])
            else:
                st.info(f"No relevant articles foundcq for {company}.")

def display_news_articles(articles_dict, product_keywords=None):
    st.subheader("📰 News Articles")
    if not articles_dict:
        st.info("No articles found.")
        return
    keywords = product_keywords if product_keywords else DEFAULT_KEYWORDS
    for company, articles in articles_dict.items():
        st.markdown(f"### Articles for {company}")
        with st.container():
            if not articles:
                st.info(f"No articles found for {company}.")
                continue
            articles = sorted(articles, key=lambda x: x.get('relevance_score', 0), reverse=True)
            for i, article in enumerate(articles):
                relevance_score = article.get('relevance_score', 0)
                if relevance_score > 30:
                    color = "green"
                elif relevance_score > 15:
                    color = "orange"
                else:
                    color = "red"
                with st.expander(f"Article {i+1}: {article.get('title', 'Untitled')} (Relevance: {relevance_score:.1f})"):
                    st.markdown(f"Source: {article.get('source', 'Unknown')}")
                    st.markdown(f"Published: {article.get('publishedAt', 'Unknown date')}")
                    st.markdown(f"URL: [{article.get('url', '#')}]({article.get('url', '#')})")
                    if article.get('is_competitor', False):
                        st.markdown(f"**Competitor Article** for {article.get('company_name', 'Unknown')}")
                    st.markdown("### Relevance Metrics:")
                    st.markdown(f"*Overall Score:* {relevance_score:.1f}")
                    if 'relevance_details' in article:
                        details = article['relevance_details']
                        metrics_text = []
                        if 'company_mentions' in details:
                            metrics_text.append(f"Company mentions: {details['company_mentions']}")
                        if 'keyword_matches' in details:
                            matched_keywords = details.get('keyword_matches', [])
                            if matched_keywords:
                                metrics_text.append(f"Keywords found: {', '.join(matched_keywords[:5])}")
                        if 'industry_matches' in details:
                            industry_terms = details.get('industry_matches', [])
                            if industry_terms:
                                metrics_text.append(f"Industry terms: {', '.join(industry_terms[:3])}")
                        if 'recency_days' in details:
                            metrics_text.append(f"Article age: {details['recency_days']} days old")
                        st.markdown("• " + "\n• ".join(metrics_text))
                    st.markdown("### Content:")
                    if 'full_content' in article and article['full_content']:
                        content = article['full_content'][:1000] + "..." if len(article['full_content']) > 1000 else article['full_content']
                    elif 'content' in article and article['content']:
                        content = article['content']
                    else:
                        content = article.get('description', 'No content available')
                    st.markdown(content)

def display_summaries(articles_dict, summaries_dict):
    st.subheader("📝 News Summaries")
    if not summaries_dict:
        st.info("No summaries available.")
        return
    for company, summaries in summaries_dict.items():
        st.markdown(f"### Summaries for {company}")
        with st.container():
            if not summaries:
                st.info(f"No summaries available for {company}.")
                continue
            articles = articles_dict.get(company, [])
            for i, summary in enumerate(summaries):
                if i < len(articles):
                    with st.expander(f"Summary {i+1}: {articles[i].get('title', 'Untitled')}"):
                        st.markdown(summary)
                        st.markdown(f"Published: {articles[i].get('publishedAt', '')[:10]}")
                        st.markdown(f"Source: {articles[i].get('source', 'Unknown')}")
                        if articles[i].get('is_competitor', False):
                            st.markdown(f"**Competitor Summary** for {articles[i].get('company_name', 'Unknown')}")
                        st.markdown(f"[Read full article]({articles[i].get('url', '#')})")

def display_sales_context(sales_context_dict):
    st.subheader("🎯 Sales Context & Talking Points")
    if not sales_context_dict:
        st.info("No sales context available.")
        return
    for company, sales_context in sales_context_dict.items():
        st.markdown(f"### Sales Context for {company}")
        with st.container():
            if not sales_context:
                st.info(f"No sales context generated for {company}.")
                continue
            st.markdown(sales_context)

def save_email_template(email_content, template_name):
    if not email_content or not template_name:
        return False
    if 'email_templates' not in st.session_state:
        st.session_state.email_templates = {}
    st.session_state.email_templates[template_name] = email_content
    return True

def load_email_template():
    if 'email_templates' not in st.session_state or not st.session_state.email_templates:
        st.info("No saved templates found.")
        return None
    template_name = st.selectbox("Select a template:", list(st.session_state.email_templates.keys()))
    if template_name:
        st.session_state.selected_template = template_name
        return st.session_state.email_templates[template_name]
    return None

def display_multiple_emails(batch_emails):
    if not batch_emails:
        st.info("No emails generated.")
        return
    for i, email_data in enumerate(batch_emails):
        with st.expander(f"Email {i+1}: To {email_data['prospect_name']} ({email_data['prospect_email']})"):
            st.text_area("", email_data['email_content'], height=300, key=f"email_{i}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Copy to Clipboard", key=f"copy_{i}"):
                    st.success(f"✅ Email for {email_data['prospect_name']} copied to clipboard!")
            with col2:
                filename = f"email_{email_data['prospect_email'].replace('@', '_')}_{datetime.now().strftime('%Y%m%d')}.txt"
                st.download_button(
                    label="Download Email",
                    data=email_data['email_content'],
                    file_name=filename,
                    mime="text/plain",
                    key=f"download_{i}"
                )