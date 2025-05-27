import streamlit as st
import pandas as pd
from utils.news_fetcher import fetch_news
from utils.summarizer import summarize_news, configure_gemini
from utils.sales_context import generate_sales_context, generate_email_pitch, setup_graph
from utils.ui_components import (
    analyze_news_relevance, 
    display_news_articles, 
    display_summaries, 
    display_sales_context, 
    save_email_template, 
    load_email_template,
    display_multiple_emails
)
from utils.auth import signup, login, update_user_details, logout
from utils.config import gemini_api_key, news_api_key, DEFAULT_KEYWORDS, TECH_SOURCES, INDUSTRY_SOURCES
from datetime import datetime

def main():
    st.set_page_config(page_title="📩 Smart B2B Email Generator", layout="wide")
    st.title("📩 Smart B2B Email Generator")

    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'articles_dict' not in st.session_state:
        st.session_state.articles_dict = {}
    if 'summaries_dict' not in st.session_state:
        st.session_state.summaries_dict = {}
    if 'competitor_summaries_dict' not in st.session_state:
        st.session_state.competitor_summaries_dict = {}
    if 'sales_context_dict' not in st.session_state:
        st.session_state.sales_context_dict = {}
    if 'email_content' not in st.session_state:
        st.session_state.email_content = ""
    if 'email_data' not in st.session_state:
        st.session_state.email_data = {}
    if 'sales_context' not in st.session_state:
        st.session_state.sales_context = ""
    if 'batch_emails' not in st.session_state:
        st.session_state.batch_emails = []
    if 'current_mode' not in st.session_state:
        st.session_state.current_mode = "Single Prospect"

    # Authentication
    if not st.session_state.user:
        tabs = st.tabs(["Login", "Signup"])
        with tabs[0]:
            st.subheader("Login")
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login"):
                success, message = login(email, password)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        with tabs[1]:
            st.subheader("Signup")
            signup_name = st.text_input("Salesperson Name", key="signup_name")
            signup_title = st.text_input("Job Title", key="signup_title")
            signup_company = st.text_input("Your Company Name", key="signup_company")
            signup_email = st.text_input("Email", key="signup_email")
            signup_mobile = st.text_input("Mobile Number", key="signup_mobile")
            signup_website = st.text_input("Company Website", key="signup_website")
            signup_linkedin = st.text_input("LinkedIn Profile", key="signup_linkedin")
            signup_password = st.text_input("Password", type="password", key="signup_password")
            if st.button("Signup"):
                success, message = signup(
                    signup_name, signup_title, signup_company, signup_email,
                    signup_mobile, signup_website, signup_linkedin, signup_password
                )
                if success:
                    st.success(message)
                else:
                    st.error(message)
        return

    # Load models
    missing_keys = []
    if not gemini_api_key:
        missing_keys.append("GEMINI_API_KEY")
    if not news_api_key:
        missing_keys.append("NEWS_API")
    if missing_keys:
        st.error(f"❌ Missing API keys: {', '.join(missing_keys)}! Set these in your .env file.")
        st.stop()

    with st.spinner("Loading models..."):
        gemini_model = configure_gemini()
        graph = setup_graph(gemini_api_key)

    # Main application
    st.sidebar.header(f"Welcome, {st.session_state.user['salesperson_name']}")
    if st.sidebar.button("Logout"):
        logout()
        st.rerun()

    tabs = st.tabs(["Email Generator", "Saved Templates", "Settings"])

    with tabs[0]:
        st.subheader("Select Email Generation Mode")
        mode = st.radio("Choose how to input prospect details:", ["Single Prospect", "Multiple Prospects (CSV Upload)"])
        st.session_state.current_mode = mode

        with st.form(key="email_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Salesperson & Product Details")
                salesperson_name = st.text_input("Salesperson Name:", value=st.session_state.user["salesperson_name"])
                salesperson_title = st.text_input("Job Title:", value=st.session_state.user["salesperson_title"])
                salesperson_company = st.text_input("Your Company Name:", value=st.session_state.user["salesperson_company"])
                product_name = st.text_input("Product/Solution Name:")
                product_description = st.text_area("Product Description:", height=80)
                product_keywords = st.text_input("Product Keywords (comma-separated):")
                product_usp = st.text_area("Unique Selling Proposition:", height=80)
            with col2:
                st.subheader("Prospect & Company Details")
                if mode == "Single Prospect":
                    prospect_name = st.text_input("Prospect Name:")
                    prospect_title = st.text_input("Prospect Job Title:")
                    prospect_email = st.text_input("Prospect Email:")
                    prospect_company = st.text_input("Prospect Company:")
                    competitor_company = st.text_input("Competitor Company (optional):")
                else:
                    uploaded_file = st.file_uploader("Upload CSV with prospect details:", type=["csv"])
                    competitor_company = st.text_input("Competitor Company (optional):")
                industry_options = ["Tech", "Healthcare", "Finance", "Retail", "Manufacturing", "Logistics", "Other"]
                industry = st.selectbox("Industry:", industry_options)

            st.subheader("Email Preferences")
            col1, col2, col3 = st.columns(3)
            with col1:
                tone_options = ["Professional", "Friendly", "Formal", "Casual", "Urgent", "Enthusiastic"]
                tone = st.selectbox("Email Tone:", tone_options)
            with col2:
                length_options = ["Short", "Medium", "Long"]
                length = st.selectbox("Email Length:", length_options)
            with col3:
                email_type_options = ["Initial Pitch", "Follow-Up", "Thank You", "Schedule Meeting/Demo"]
                email_type = st.selectbox("Email Type:", email_type_options)
            with col3:
                template_name = st.text_input("Save as template (optional):")

            with st.expander("⚙ Advanced Settings", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    min_articles = st.number_input("Minimum Articles", min_value=1, max_value=10, value=2)
                    max_articles = st.number_input("Maximum Articles", min_value=1, max_value=15, value=5)
                with col2:
                    date_range = st.slider("Search date range (days)", min_value=7, max_value=90, value=30)
                    generate_context = st.checkbox("Generate sales context", value=True)
                    refresh_news = st.checkbox("Refresh news data", value=False)

            submitted = st.form_submit_button("Generate Personalized Email(s)")

        if submitted:
            product_keywords_list = [k.strip() for k in product_keywords.split(",") if k.strip()] if product_keywords else []

            # Prepare base email data
            base_email_data = {
                "salesperson_name": salesperson_name,
                "salesperson_title": salesperson_title,
                "salesperson_company": salesperson_company,
                "salesperson_email": st.session_state.user["salesperson_email"],
                "salesperson_mobile": st.session_state.user["salesperson_mobile"],
                "salesperson_website": st.session_state.user["salesperson_website"],
                "salesperson_linkedin": st.session_state.user["salesperson_linkedin"],
                "product_name": product_name,
                "product_description": product_description,
                "product_usp": product_usp,
                "tone": tone.lower(),
                "length": length.lower(),
                "email_type": email_type.lower(),
                "industry": industry.lower(),
                "product_keywords": product_keywords,
                "competitor_company": competitor_company
            }

            # Generate emails based on mode
            if mode == "Single Prospect":
                if not all([prospect_name, prospect_title, prospect_email, prospect_company]):
                    st.warning("⚠ Please fill in all prospect details for single prospect mode.")
                    return
                email_data = base_email_data.copy()
                email_data.update({
                    "prospect_name": prospect_name,
                    "prospect_title": prospect_title,
                    "prospect_email": prospect_email,
                    "prospect_company": prospect_company,
                    "company_name": prospect_company
                })

                # Fetch news
                if refresh_news or prospect_company not in st.session_state.articles_dict:
                    st.session_state.articles_dict[prospect_company] = []
                    st.session_state.summaries_dict[prospect_company] = []
                    st.session_state.competitor_summaries_dict[prospect_company] = []
                    st.session_state.sales_context_dict[prospect_company] = ""

                    progress_bar = st.progress(0)
                    progress_text = st.empty()

                    progress_text.text("Step 1/4: Searching for relevant news articles...")
                    articles = fetch_news(
                        prospect_company, 
                        news_api_key, 
                        product_keywords_list, 
                        industry.lower(),
                        min_articles, 
                        max_articles,
                        competitor_company=competitor_company
                    )
                    st.session_state.articles_dict[prospect_company] = articles
                    progress_bar.progress(0.25)

                    prospect_articles = [a for a in articles if not a.get("is_competitor", False)][:max_articles]
                    competitor_articles = [a for a in articles if a.get("is_competitor", False)][:min(2, max_articles)]

                    if not prospect_articles:
                        print(f"No news found for {prospect_company}. Checking competitor news for {competitor_company}.")
                        news_summary = f"No specific recent news found for {prospect_company}."
                        summaries = []
                    else:
                        progress_text.text(f"Step 2/4: Summarizing {len(prospect_articles)} news articles for {prospect_company}...")
                        summaries = []
                        for i, article in enumerate(prospect_articles[:max_articles]):  # Limit to max_articles
                            summary = summarize_news(article, gemini_model)
                            if summary:
                                summaries.append(summary)
                            sub_progress = 0.25 + (i + 1) / max(1, len(prospect_articles)) * 0.25
                            progress_bar.progress(min(sub_progress, 0.50))
                        st.session_state.summaries_dict[prospect_company] = summaries
                        news_summary = "\n\n".join(summaries[:3]) if summaries else f"No specific recent news found for {prospect_company}."

                    competitor_summaries = []
                    if competitor_articles:
                        progress_text.text(f"Summarizing {len(competitor_articles)} news articles for {competitor_company}...")
                        for i, article in enumerate(competitor_articles[:min(2, max_articles)]):  # Limit to 2 or max_articles
                            summary = summarize_news(article, gemini_model)
                            if summary:
                                competitor_summaries.append(summary)
                            sub_progress = 0.25 + (i + 1) / max(1, len(competitor_articles)) * 0.25
                            progress_bar.progress(min(sub_progress, 0.50))
                        st.session_state.competitor_summaries_dict[prospect_company] = competitor_summaries
                    competitor_summary = "\n\n".join(competitor_summaries[:2]) if competitor_summaries else ""

                    if not prospect_articles and not competitor_summaries:
                        print(f"No news found for {prospect_company} or {competitor_company}. Falling back to industry trends.")
                    elif not prospect_articles and competitor_summaries:
                        print(f"No news found for {prospect_company}. Using competitor news for {competitor_company}.")

                    progress_bar.progress(0.50)
                else:
                    articles = st.session_state.articles_dict.get(prospect_company, [])
                    prospect_articles = [a for a in articles if not a.get("is_competitor", False)][:max_articles]
                    competitor_articles = [a for a in articles if a.get("is_competitor", False)][:min(2, max_articles)]
                    summaries = st.session_state.summaries_dict.get(prospect_company, [])
                    competitor_summaries = st.session_state.competitor_summaries_dict.get(prospect_company, [])
                    news_summary = "\n\n".join(summaries[:3]) if summaries else f"No specific recent news found for {prospect_company}."
                    competitor_summary = "\n\n".join(competitor_summaries[:2]) if competitor_summaries else ""
                    if not prospect_articles and not competitor_summaries:
                        print(f"Using cached empty news for {prospect_company} and {competitor_company}. Falling back to industry trends.")
                    elif not prospect_articles and competitor_summaries:
                        print(f"Using cached empty news for {prospect_company}. Using competitor news for {competitor_company}.")
                    progress_bar = st.progress(0.50)
                    progress_text = st.empty()

                if generate_context:
                    progress_text.text("Step 3/4: Generating sales context and talking points...")
                    sales_context = generate_sales_context(email_data, news_summary, competitor_summary, graph)
                    st.session_state.sales_context = sales_context
                    st.session_state.sales_context_dict[prospect_company] = sales_context
                    progress_bar.progress(0.75)
                else:
                    sales_context = ""
                    st.session_state.sales_context = sales_context
                    st.session_state.sales_context_dict[prospect_company] = sales_context
                    progress_bar.progress(0.75)

                progress_text.text("Step 4/4: Crafting your personalized email...")
                email_content = generate_email_pitch(email_data, news_summary, sales_context, competitor_summary, graph)
                st.session_state.email_content = email_content
                st.session_state.email_data = email_data
                st.session_state.batch_emails = []

                if template_name:
                    save_email_template(email_content, template_name)
                    st.success(f"✅ Email template '{template_name}' saved!")

                progress_bar.progress(1.0)
                progress_text.success("✅ Email generated successfully!")

                st.subheader("📧 Your Personalized Email:")
                email_box = st.text_area("", email_content, height=400)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Copy to Clipboard"):
                        st.success("✅ Copied to clipboard!")
                with col2:
                    if st.button("Download as Text"):
                        filename = f"email_{prospect_company.replace(' ', '').lower()}{datetime.now().strftime('%Y%m%d')}.txt"
                        st.download_button(
                            label="Download Email",
                            data=email_content,
                            file_name=filename,
                            mime="text/plain",
                        )
            else:  # Multiple Prospects
                if not uploaded_file:
                    st.warning("⚠ Please upload a CSV file with prospect details.")
                    return
                try:
                    df = pd.read_csv(uploaded_file)
                    required_columns = ['prospect_name', 'prospect_title', 'prospect_email', 'prospect_company']
                    if not all(col in df.columns for col in required_columns):
                        st.error("❌ CSV must contain columns: prospect_name, prospect_title, prospect_email, prospect_company")
                        return
                    batch_emails = []
                    progress_bar = st.progress(0)
                    progress_text = st.empty()
                    total_prospects = len(df)
                    prospect_weight = 1.0 / total_prospects

                    for idx, row in df.iterrows():
                        email_data = base_email_data.copy()
                        email_data.update({
                            "prospect_name": row['prospect_name'],
                            "prospect_title": row['prospect_title'],
                            "prospect_email": row['prospect_email'],
                            "prospect_company": row['prospect_company'],
                            "company_name": row['prospect_company']
                        })

                        base_progress = idx * prospect_weight
                        progress_text.text(f"Processing prospect {idx + 1}/{total_prospects}: {row['prospect_name']}...")

                        if refresh_news or row['prospect_company'] not in st.session_state.articles_dict:
                            st.session_state.articles_dict[row['prospect_company']] = []
                            st.session_state.summaries_dict[row['prospect_company']] = []
                            st.session_state.competitor_summaries_dict[row['prospect_company']] = []
                            st.session_state.sales_context_dict[row['prospect_company']] = ""

                            progress_text.text(f"Step 1/4: Searching for relevant news articles for {row['prospect_company']}...")
                            articles = fetch_news(
                                row['prospect_company'], 
                                news_api_key, 
                                product_keywords_list, 
                                industry.lower(),
                                min_articles, 
                                max_articles,
                                competitor_company=competitor_company
                            )
                            st.session_state.articles_dict[row['prospect_company']] = articles
                            progress_bar.progress(base_progress + prospect_weight * 0.25)

                            prospect_articles = [a for a in articles if not a.get("is_competitor", False)][:max_articles]
                            competitor_articles = [a for a in articles if a.get("is_competitor", False)][:min(2, max_articles)]

                            if not prospect_articles:
                                print(f"No news found for {row['prospect_company']}. Checking competitor news for {competitor_company}.")
                                news_summary = f"No specific recent news found for {row['prospect_company']}."
                                summaries = []
                            else:
                                progress_text.text(f"Step 2/4: Summarizing {len(prospect_articles)} news articles for {row['prospect_company']}...")
                                summaries = []
                                for i, article in enumerate(prospect_articles[:max_articles]):  # Limit to max_articles
                                    summary = summarize_news(article, gemini_model)
                                    if summary:
                                        summaries.append(summary)
                                    sub_progress = base_progress + 0.25 * prospect_weight + (i + 1) / max(1, len(prospect_articles)) * 0.25 * prospect_weight
                                    progress_bar.progress(min(sub_progress, base_progress + 0.50 * prospect_weight))
                                st.session_state.summaries_dict[row['prospect_company']] = summaries
                                news_summary = "\n\n".join(summaries[:3]) if summaries else f"No specific recent news found for {row['prospect_company']}."

                            competitor_summaries = []
                            if competitor_articles:
                                progress_text.text(f"Summarizing {len(competitor_articles)} news articles for {competitor_company}...")
                                for i, article in enumerate(competitor_articles[:min(2, max_articles)]):  # Limit to 2 or max_articles
                                    summary = summarize_news(article, gemini_model)
                                    if summary:
                                        competitor_summaries.append(summary)
                                    sub_progress = base_progress + 0.25 * prospect_weight + (i + 1) / max(1, len(competitor_articles)) * 0.25 * prospect_weight
                                    progress_bar.progress(min(sub_progress, base_progress + 0.50 * prospect_weight))
                                st.session_state.competitor_summaries_dict[row['prospect_company']] = competitor_summaries
                            competitor_summary = "\n\n".join(competitor_summaries[:2]) if competitor_summaries else ""

                            if not prospect_articles and not competitor_summaries:
                                print(f"No news found for {row['prospect_company']} or {competitor_company}. Falling back to industry trends.")
                            elif not prospect_articles and competitor_summaries:
                                print(f"No news found for {row['prospect_company']}. Using competitor news for {competitor_company}.")
                        else:
                            articles = st.session_state.articles_dict.get(row['prospect_company'], [])
                            prospect_articles = [a for a in articles if not a.get("is_competitor", False)][:max_articles]
                            competitor_articles = [a for a in articles if a.get("is_competitor", False)][:min(2, max_articles)]
                            summaries = st.session_state.summaries_dict.get(row['prospect_company'], [])
                            competitor_summaries = st.session_state.competitor_summaries_dict.get(row['prospect_company'], [])
                            news_summary = "\n\n".join(summaries[:3]) if summaries else f"No specific recent news found for {row['prospect_company']}."
                            competitor_summary = "\n\n".join(competitor_summaries[:2]) if competitor_summaries else ""
                            if not prospect_articles and not competitor_summaries:
                                print(f"Using cached empty news for {row['prospect_company']} and {competitor_company}. Falling back to industry trends.")
                            elif not prospect_articles and competitor_summaries:
                                print(f"Using cached empty news for {row['prospect_company']}. Using competitor news for {competitor_company}.")
                            progress_bar.progress(base_progress + 0.50 * prospect_weight)

                        if generate_context:
                            progress_text.text(f"Step 3/4: Generating sales context for {row['prospect_company']}...")
                            sales_context = generate_sales_context(email_data, news_summary, competitor_summary, graph)
                            st.session_state.sales_context_dict[row['prospect_company']] = sales_context
                            progress_bar.progress(base_progress + 0.75 * prospect_weight)
                        else:
                            sales_context = ""
                            st.session_state.sales_context_dict[row['prospect_company']] = sales_context
                            progress_bar.progress(base_progress + 0.75 * prospect_weight)

                        progress_text.text(f"Step 4/4: Crafting personalized email for {row['prospect_name']}...")
                        email_content = generate_email_pitch(email_data, news_summary, sales_context, competitor_summary, graph)
                        batch_emails.append({
                            "prospect_name": row['prospect_name'],
                            "prospect_email": row['prospect_email'],
                            "email_content": email_content
                        })
                        progress_bar.progress(base_progress + prospect_weight)

                    st.session_state.batch_emails = batch_emails
                    st.session_state.email_content = ""
                    st.session_state.email_data = base_email_data

                    if template_name:
                        for email in batch_emails:
                            save_email_template(email['email_content'], f"{template_name}_{email['prospect_email']}")
                        st.success(f"✅ Email templates saved with prefix '{template_name}'!")

                    progress_text.success("✅ Emails generated successfully!")

                    st.subheader("📧 Generated Emails:")
                    display_multiple_emails(batch_emails)
                except Exception as e:
                    st.error(f"❌ Error processing CSV: {str(e)}")
                    return

    with tabs[1]:
        st.subheader("📋 Saved Email Templates")
        if 'email_templates' not in st.session_state or not st.session_state.email_templates:
            st.info("No saved templates yet. Save templates in the Email Generator tab.")
        else:
            template_content = load_email_template()
            if template_content:
                st.text_area("Template Content", template_content, height=400)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Copy Template"):
                        st.success("✅ Template copied to clipboard!")
                with col2:
                    if st.button("Delete Template"):
                        template_name = st.session_state.get('selected_template')
                        if template_name and template_name in st.session_state.email_templates:
                            del st.session_state.email_templates[template_name]
                            st.success(f"✅ Template '{template_name}' deleted!")
                            st.rerun()

    with tabs[2]:
        st.subheader("⚙ Application Settings")
        with st.expander("User Details", expanded=True):
            st.markdown("Update your personal details below:")
            update_name = st.text_input("Salesperson Name", value=st.session_state.user["salesperson_name"], key="update_name")
            update_title = st.text_input("Job Title", value=st.session_state.user["salesperson_title"], key="update_title")
            update_company = st.text_input("Your Company Name", value=st.session_state.user["salesperson_company"], key="update_company")
            update_email = st.text_input("Email", value=st.session_state.user["salesperson_email"], key="update_email")
            update_mobile = st.text_input("Mobile Number", value=st.session_state.user["salesperson_mobile"], key="update_mobile")
            update_website = st.text_input("Company Website", value=st.session_state.user["salesperson_website"], key="update_website")
            update_linkedin = st.text_input("LinkedIn Profile", value=st.session_state.user["salesperson_linkedin"], key="update_linkedin")
            if st.button("Update Details"):
                success, message = update_user_details(
                    st.session_state.user["email"],
                    update_name,
                    update_title,
                    update_company,
                    update_email,
                    update_mobile,
                    update_website,
                    update_linkedin
                )
                if success:
                    st.success(message)
                else:
                    st.error(message)

        with st.expander("Default Keywords", expanded=False):
            default_keywords = ", ".join(DEFAULT_KEYWORDS)
            custom_keywords = st.text_area("Customize default industry keywords:", default_keywords)
            if st.button("Save Custom Keywords"):
                try:
                    new_keywords = [k.strip() for k in custom_keywords.split(",") if k.strip()]
                    if len(new_keywords) > 5:
                        DEFAULT_KEYWORDS[:] = new_keywords
                        st.success("✅ Default keywords updated!")
                    else:
                        st.error("Please provide at least 5 keywords")
                except:
                    st.error("Error updating keywords")

    if st.session_state.articles_dict:
        st.markdown("---")
        st.header("📊 News Analysis")
        product_keywords_list = []
        if st.session_state.email_data.get("product_keywords"):
            product_keywords_list = [k.strip() for k in st.session_state.email_data.get("product_keywords", "").split(",") if k.strip()]
        analysis_tab, news_tab, summary_tab, context_tab = st.tabs([
            "Relevance Analysis", 
            "News Articles", 
            "News Summaries", 
            "Sales Context"
        ])
        with analysis_tab:
            analyze_news_relevance(
                st.session_state.articles_dict, 
                st.session_state.summaries_dict,
                product_keywords_list
            )
        with news_tab:
            display_news_articles(st.session_state.articles_dict, product_keywords_list)
        with summary_tab:
            display_summaries(st.session_state.articles_dict, st.session_state.summaries_dict)
        with context_tab:
            display_sales_context(st.session_state.sales_context_dict)

if __name__ == "__main__":
    main()
