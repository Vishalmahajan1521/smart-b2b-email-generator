import streamlit as st
import google.generativeai as genai
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict
from utils.config import gemini_api_key

class State(TypedDict):
    messages: Annotated[list, add_messages]

def setup_graph(api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-001')
    graph_builder = StateGraph(State)
    
    def chatbot(state: State):
        prompt = state['messages'][-1].content
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 1500,
                    "temperature": 0.6,
                    "top_p": 0.95
                }
            )
            return {"messages": [("assistant", response.text)]}
        except Exception as e:
            print(f"Error with Gemini API: {str(e)}")
            return {"messages": [("assistant", "Error generating response. Please try again.")]}

    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)
    return graph_builder.compile()

def generate_sales_context(company_data, news_summary, competitor_summary, graph):
    prospect_company = company_data.get("prospect_company", "")
    company_name = company_data.get("company_name", prospect_company)
    product_name = company_data.get("product_name", "")
    product_description = company_data.get("product_description", "")
    industry = company_data.get("industry", "tech")
    competitor_company = company_data.get("competitor_company", "")
    news_context = news_summary if news_summary and "no specific" not in news_summary.lower() else "No specific news available."
    competitor_context = f"""
    COMPETITOR NEWS:
    {competitor_summary}
    """ if competitor_summary and competitor_company else ""
    prompt = f"""
    Analyze the following information about {company_name} to create a detailed and nuanced business context analysis. Provide 4-6 actionable, highly specific insights to help a sales representative pitch {product_name} effectively.

    NEWS SUMMARY:
    {news_context}

    {competitor_context}

    PRODUCT:
    {product_description}

    INDUSTRY: {industry}

    Create a business context analysis with the following components:
    1. Strategic Challenges: Identify 2-3 specific business or operational challenges {company_name} is facing, inferred from the news if available, or common challenges in the {industry} industry if no news is provided.
    2. Strategic Opportunities: Detail how {product_name} can address these challenges, aligning with {company_name}'s goals or pain points. If competitor news is available, highlight how {product_name} can help {company_name} stay competitive.
    3. Engagement Strategy: Provide 3-4 tailored talking points that connect {product_name} to {company_name}'s current situation, emphasizing measurable benefits. Incorporate competitor advancements if provided.
    4. Industry Alignment: Highlight how {product_name} fits into broader {industry} trends that {company_name} is likely prioritizing.

    Ensure the analysis is concise, professional, and avoids generic statements. Use specific examples or metrics where possible. If no news is available for {company_name}, base the analysis on competitor news (if provided) or common {industry} challenges.
    """
    with st.spinner("Generating sales context..."):
        try:
            response = graph.invoke({"messages": [("user", prompt)]})
            if response and "messages" in response and len(response["messages"]) > 0:
                return response["messages"][-1].content
            return f"No specific context generated for {company_name}. Using industry-standard challenges."
        except Exception as e:
            print(f"Error generating sales context: {str(e)}")
            return f"Error generating sales context. Please check your API keys and try again."

def parse_chatbot_input(chat_input, collected_data):
    """Parse chatbot input to populate email_data, returning updated data and next prompt."""
    required_fields = [
        ("prospect_name", "What's the prospect's name?"),
        ("prospect_title", "What's the prospect's job title?"),
        ("prospect_company", "What's the prospect's company name?"),
        ("email_type", "What type of email do you want to generate? Choose: initial pitch, follow-up, thank you, schedule meeting/demo")
    ]
    optional_fields = [
        ("industry", "What's the industry? (Default: tech)"),
        ("length", "What's the email length? Choose: short, medium, long (Default: medium)"),
        ("tone", "What's the tone? (Default: professional)"),
        ("news_summary", "Any recent news about the prospect's company? (Optional)"),
        ("competitor_company", "Name a competitor company, if any. (Optional)"),
        ("competitor_summary", "Any recent advancements by the competitor? (Optional)")
    ]
    
    # Check if all required fields are collected
    for field, prompt in required_fields:
        if field not in collected_data:
            if not chat_input and field == required_fields[0][0]:
                return collected_data, prompt
            if chat_input:
                collected_data[field] = chat_input.strip()
                if field == "email_type" and chat_input.lower() not in ["initial pitch", "follow-up", "thank you", "schedule meeting/demo"]:
                    return collected_data, f"Invalid email type. Please choose: initial pitch, follow-up, thank you, schedule meeting/demo"
                return collected_data, required_fields[required_fields.index((field, prompt)) + 1][1] if field != required_fields[-1][0] else optional_fields[0][1]
            return collected_data, prompt
    
    # Collect optional fields
    for field, prompt in optional_fields:
        if field not in collected_data:
            if chat_input:
                if chat_input.lower() in ["skip", "none", ""]:
                    collected_data[field] = "" if field in ["news_summary", "competitor_company", "competitor_summary"] else ("tech" if field == "industry" else "medium" if field == "length" else "professional")
                    next_index = optional_fields.index((field, prompt)) + 1
                    return collected_data, optional_fields[next_index][1] if next_index < len(optional_fields) else "All data collected! Generating three emails now..."
                collected_data[field] = chat_input.strip()
                next_index = optional_fields.index((field, prompt)) + 1
                return collected_data, optional_fields[next_index][1] if next_index < len(optional_fields) else "All data collected! Generating three emails now..."
            return collected_data, f"{prompt} (Type 'skip' to use default or leave blank)"
    
    return collected_data, ""

def generate_email_pitch(email_data, news_summary, sales_context, competitor_summary, graph):
    # Default salesperson details
    salesperson_name = email_data.get("salesperson_name", "Vishal Mahajan")
    salesperson_title = email_data.get("salesperson_title", "Sales Manager")
    salesperson_company = email_data.get("salesperson_company", "SecureTech Solutions")
    salesperson_email = email_data.get("salesperson_email", "mahajanvishal1521@gmail.com")
    salesperson_mobile = email_data.get("salesperson_mobile", "9421683835")
    salesperson_website = email_data.get("salesperson_website", "www.securetechsolutions.com")
    salesperson_linkedin = email_data.get("salesperson_linkedin", "https://www.linkedin.com/in/vishal-mahajan-a60381258/")
    prospect_name = email_data.get("prospect_name", "")
    prospect_title = email_data.get("prospect_title", "")
    prospect_company = email_data.get("prospect_company", "")
    company_name = email_data.get("company_name", prospect_company)
    email_type = email_data.get("email_type", "initial pitch")
    tone = email_data.get("tone", "professional")
    length = email_data.get("length", "medium")
    industry = email_data.get("industry", "tech")
    
    # SecureShield AI product details for non-thank-you emails
    product_name = "SecureShield AI"
    product_description = "SecureShield AI offers 99.9% threat detection accuracy with automated compliance reporting, reducing response times by 50% compared to traditional solutions."
    product_usp = "Unmatched accuracy and automation for cybersecurity"
    
    # Override news/competitor data if provided
    news_summary = email_data.get("news_summary", news_summary)
    competitor_company = email_data.get("competitor_company", "")
    competitor_summary = email_data.get("competitor_summary", competitor_summary)
    
    length_guide = {
        "short": "Keep the email highly concise and impactful (120-150 words). Use short sentences and avoid unnecessary elaboration.",
        "medium": "Write a balanced email with depth (200-250 words).",
        "long": "Craft a detailed email with comprehensive insights (300-350 words)."
    }.get(length, "Write a balanced email with depth (200-250 words).")
    
    industry_trends = {
        "tech": "increasing demand for AI-driven automation, heightened focus on cybersecurity, and rapid adoption of cloud solutions",
        "healthcare": "need for interoperable systems, patient data security, and telehealth expansion",
        "finance": "focus on fraud prevention, regulatory compliance, and digital banking transformation",
        "retail": "shift to e-commerce, personalized customer experiences, and supply chain optimization",
        "manufacturing": "adoption of Industry 4.0 technologies, supply chain resilience, and sustainability goals",
        "logistics": "demand for real-time tracking, cost optimization, and automation in supply chains",
        "other": "emphasis on operational efficiency, digital transformation, and competitive differentiation"
    }.get(industry.lower(), "emphasis on operational efficiency and digital transformation")
    
    # Set context for non-thank-you emails
    if email_type.lower() != "thank you":
        news_context = news_summary if news_summary and "no specific" not in news_summary.lower() else f"No recent news found for {prospect_company}. Based on {industry} industry trends such as {industry_trends}, {prospect_company} likely faces challenges that SecureShield AI can address."
        competitor_context = f"""
        COMPETITOR CONTEXT:
        Highlight recent advancements by {competitor_company} in areas related to SecureShield AI: {competitor_summary}. Emphasize how SecureShield AI offers a unique or superior solution to help {prospect_company} gain a competitive edge, creating excitement and urgency without criticizing {competitor_company}.
        """ if competitor_summary and competitor_company else ""
        product_context = f"""
        PRODUCT DETAILS:
        - Product: {product_name}
        - Description: {product_description}
        - Unique Selling Proposition: {product_usp}
        """
    else:
        news_context = ""
        competitor_context = ""
        product_context = ""
    
    # Define three prompts for each email type with varied tones
    prompts = []
    tone_variations = [
        ("professional and formal", "Structured and reserved, focusing on business alignment and strategic priorities"),
        ("warm and personable", "Friendly and approachable, emphasizing relationship-building and shared goals"),
        ("enthusiastic and engaging", "Upbeat and forward-looking, highlighting excitement and innovation")
    ]
    
    for tone_name, tone_desc in tone_variations:
        if email_type.lower() == "initial pitch":
            prompt = f"""
            Craft a highly personalized, {tone_name} sales email from {salesperson_name}, {salesperson_title} at {salesperson_company}, to {prospect_name}, {prospect_title} at {prospect_company} in the {industry} industry. The email type is 'initial pitch'. The email must be in plain text, suitable for all email clients, with no HTML, Markdown, or formatting symbols (e.g., avoid *, **, #, or HTML tags). Emphasize key points using natural language, sentence structure, or capitalization.

            NEWS CONTEXT:
            {news_context}

            SALES CONTEXT & TALKING POINTS:
            {sales_context}

            {competitor_context}

            {product_context}

            SALESPERSON DETAILS:
            - Email: {salesperson_email}
            - Mobile: {salesperson_mobile}
            - Company Website: {salesperson_website}
            - LinkedIn: {salesperson_linkedin}

            EMAIL PREFERENCES:
            - Tone: {tone_name} ({tone_desc})
            - Length: {length_guide}

            The email should:
            1. Open with a personalized greeting referencing {prospect_company}'s context (e.g., news, trends).
            2. Introduce SecureShield AI as a solution to {prospect_company}'s challenges, using news, competitor advancements, or {industry} trends.
            3. Provide 2-3 quantifiable benefits as plain text bullet points (using hyphens), varying benefits to reflect {tone_desc} (e.g., cost savings for formal, collaboration for personable, innovation for enthusiastic).
            4. Include a storytelling element (e.g., a success story or relatable scenario) aligned with the tone.
            5. Conclude with a low-pressure call to action for a 15-minute call or demo, phrased to match the tone.
            6. Include a signature with {salesperson_name}'s details, formatted as plain text:
               {salesperson_name}
               {salesperson_title}, {salesperson_company}
               Email: {salesperson_email}
               Mobile: {salesperson_mobile}
               Website: {salesperson_website}
               LinkedIn: {salesperson_linkedin}
            7. Use natural language variations and avoid clichés.
            8. Structure for readability with short paragraphs, plain text bullet points (using hyphens), and a clear flow. Ensure professional, polished, and adheres to the specified word count, using only plain text.
            """
        elif email_type.lower() == "follow-up":
            prompt = f"""
            Craft a highly personalized, {tone_name} sales email from {salesperson_name}, {salesperson_title} at {salesperson_company}, to {prospect_name}, {prospect_title} at {prospect_company} in the {industry} industry. The email type is 'follow-up'. The email must be in plain text, suitable for all email clients, with no HTML, Markdown, or formatting symbols (e.g., avoid *, **, #, or HTML tags). Emphasize key points using natural language, sentence structure, or capitalization.

            NEWS CONTEXT:
            {news_context}

            SALES CONTEXT & TALKING POINTS:
            {sales_context}

            {competitor_context}

            {product_context}

            SALESPERSON DETAILS:
            - Email: {salesperson_email}
            - Mobile: {salesperson_mobile}
            - Company Website: {salesperson_website}
            - LinkedIn: {salesperson_linkedin}

            EMAIL PREFERENCES:
            - Tone: {tone_name} ({tone_desc})
            - Length: {length_guide}

            The email should:
            1. Open with a greeting referencing a prior interaction with {prospect_name}.
            2. Restate SecureShield AI's value, addressing potential concerns (e.g., cost, implementation).
            3. Provide 1-2 updated or reinforced benefits as plain text bullet points (using hyphens), varying benefits to reflect {tone_desc}.
            4. If competitor news is available, emphasize urgency to stay competitive, aligned with the tone.
            5. Include a storytelling element (e.g., recap of prior discussion) matching the tone.
            6. Conclude with a call to action to rekindle interest, suggesting a specific next step, phrased to match the tone.
            7. Include a signature with {salesperson_name}'s details, formatted as plain text:
               {salesperson_name}
               {salesperson_title}, {salesperson_company}
               Email: {salesperson_email}
               Mobile: {salesperson_mobile}
               Website: {salesperson_website}
               LinkedIn: {salesperson_linkedin}
            8. Use natural language variations and avoid clichés.
            9. Structure for readability with short paragraphs, plain text bullet points (using hyphens), and a clear flow. Ensure professional, polished, and adheres to the specified word count, using only plain text.
            """
        elif email_type.lower() == "thank you":
            prompt = f"""
            Craft a highly personalized, {tone_name} sales email from {salesperson_name}, {salesperson_title} at {salesperson_company}, to {prospect_name}, {prospect_title} at {prospect_company} in the {industry} industry. The email type is 'thank you'. The email must be in plain text, suitable for all email clients, with no HTML, Markdown, or formatting symbols (e.g., avoid *, **, #, or HTML tags). Emphasize key points using natural language, sentence structure, or capitalization.

            SALESPERSON DETAILS:
            - Email: {salesperson_email}
            - Mobile: {salesperson_mobile}
            - Company Website: {salesperson_website}
            - LinkedIn: {salesperson_linkedin}

            EMAIL PREFERENCES:
            - Tone: {tone_name} ({tone_desc})
            - Length: Keep the email highly concise and impactful (100-150 words) with short sentences.

            The email should:
            1. Open with a greeting expressing gratitude for a recent interaction (e.g., meeting, call, or response) with {prospect_name}.
            2. Highlight 1-2 discussion points or general benefits of further collaboration (e.g., efficiency for formal, shared goals for personable, innovation for enthusiastic) as plain text bullet points (using hyphens).
            3. Include a brief recap of the interaction as the storytelling element, reflecting {tone_desc}.
            4. Conclude with a low-pressure call to action to schedule a follow-up, phrased to match the tone (e.g., formal for strategic alignment, flexible for personable, specific days for enthusiastic).
            5. Include a signature with {salesperson_name}'s details, formatted as plain text:
               {salesperson_name}
               {salesperson_title}, {salesperson_company}
               Email: {salesperson_email}
               Mobile: {salesperson_mobile}
               Website: {salesperson_website}
               LinkedIn: {salesperson_linkedin}
            6. Use natural language variations and avoid clichés.
            7. Do not reference news, competitor advancements, or product details (product name, description, or USP).
            8. Structure for readability with short paragraphs, plain text bullet points (using hyphens), and a clear flow. Ensure professional, polished, and adheres to the specified word count, using only plain text.
            """
        elif email_type.lower() == "schedule meeting/demo":
            prompt = f"""
            Craft a highly personalized, {tone_name} sales email from {salesperson_name}, {salesperson_title} at {salesperson_company}, to {prospect_name}, {prospect_title} at {prospect_company} in the {industry} industry. The email type is 'schedule meeting/demo'. The email must be in plain text, suitable for all email clients, with no HTML, Markdown, or formatting symbols (e.g., avoid *, **, #, or HTML tags). Emphasize key points using natural language, sentence structure, or capitalization.

            NEWS CONTEXT:
            {news_context}

            SALES CONTEXT & TALKING POINTS:
            {sales_context}

            {competitor_context}

            {product_context}

            SALESPERSON DETAILS:
            - Email: {salesperson_email}
            - Mobile: {salesperson_mobile}
            - Company Website: {salesperson_website}
            - LinkedIn: {salesperson_linkedin}

            EMAIL PREFERENCES:
            - Tone: {tone_name} ({tone_desc})
            - Length: {length_guide}

            The email should:
            1. Open with a greeting proposing a specific time and date for a 15-20 minute meeting or demo (e.g., next Tuesday at 10 AM).
            2. Emphasize the value of the session (e.g., addressing {prospect_company}'s challenges), using news or competitor context for urgency if available.
            3. Provide 1-2 bullet points summarizing what the meeting/demo will cover, varying points to reflect {tone_desc}.
            4. Include a scenario of the demo’s value as the storytelling element, aligned with the tone.
            5. Conclude with a request to confirm or suggest an alternative time, phrased to match the tone.
            6. Include a signature with {salesperson_name}'s details, formatted as plain text:
               {salesperson_name}
               {salesperson_title}, {salesperson_company}
               Email: {salesperson_email}
               Mobile: {salesperson_mobile}
               Website: {salesperson_website}
               LinkedIn: {salesperson_linkedin}
            7. Use natural language variations and avoid clichés.
            8. Structure for readability with short paragraphs, plain text bullet points (using hyphens), and a clear flow. Ensure professional, polished, and adheres to the specified word count, using only plain text.
            """
        else:
            return f"Error: Invalid email type '{email_type}'. Please choose 'initial pitch', 'follow-up', 'thank you', or 'schedule meeting/demo'."
        prompts.append(prompt)
    
    # Generate three emails
    emails = []
    with st.spinner(f"Generating three personalized {email_type} emails..."):
        for i, prompt in enumerate(prompts, 1):
            try:
                response = graph.invoke({"messages": [("user", prompt)]})
                if response and "messages" in response and len(response["messages"]) > 0:
                    emails.append(f"=== Email Option {i} ===\n{response['messages'][-1].content}\n")
                else:
                    emails.append(f"=== Email Option {i} ===\nError: No valid response generated for option {i}. Please try again.\n")
            except Exception as e:
                print(f"Error generating email {i} for {email_type}: {str(e)}")
                emails.append(f"=== Email Option {i} ===\nError generating email {i}. Please check your API keys and try again.\n")
    
    # Combine emails with separators
    return "\n".join(emails)