import requests
import json
import os
import re
from datetime import datetime
import groq
from audio import listen, speak
from dotenv import load_dotenv
load_dotenv()


NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ---- CONFIGURATION ----

NEWS_ENDPOINT = "https://newsapi.org/v2/everything"
OUTPUT_DIR = "news_data"
MODEL_NAME = "llama3-70b-8192"

# ---- SETUP ----
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

client = groq.Groq(api_key=GROQ_API_KEY)

# ---- FETCH NEWS ----
def fetch_live_news(query=None, page_size=3): # Default page_size to 3
    params = {
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "pageSize": page_size, # Use the page_size parameter
        "sortBy": "publishedAt" # Sort by latest
    }
    # If no query, fetch top headlines instead of using 'latest' keyword
    if not query:
        params["endpoint"] = "top-headlines" # Use top-headlines endpoint
        # Remove 'q' if it exists from default params if no query provided
        params.pop("q", None)
        # Add country or category if desired for top headlines, e.g., 'us'
        # params["country"] = "us"
        news_fetch_url = "https://newsapi.org/v2/top-headlines" # URL for top headlines
    else:
        params["q"] = query
        news_fetch_url = NEWS_ENDPOINT # URL for everything endpoint

    try:
        # Use the determined URL
        response = requests.get(news_fetch_url, params=params)
        response.raise_for_status()
        articles = response.json().get("articles", [])
        # --- REMOVE THIS BLOCK ---
        # Keep filtering logic if a specific query was provided
        # if query:
        #     query_lower = query.lower()
        #     filtered_articles = []
        #     for article in articles:
        #         title = article.get('title', '').lower()
        #         description = article.get('description', '').lower()
        #         if query_lower in title or query_lower in description:
        #             filtered_articles.append(article)
        #     articles = filtered_articles # Overwrite with filtered list
        # --- END OF REMOVED BLOCK ---

        if not articles:
            if query:
                print(f"❌ No articles found specifically about '{query}'.")
            else:
                print("❌ No top headlines found.")
            return []

        # Ensure we only save up to the requested page_size (e.g., 3)
        articles = articles[:page_size]

        saved_files = []
        # Use min(len(articles), page_size) in case fewer than page_size articles were returned
        for idx, article in enumerate(articles, 1):
            title = article.get('title') or ''
            description = article.get('description') or ''
            content = article.get('content') or ''

            full_article_data = {
                "title": title,
                "description": description,
                "full_text": content,
                "url": article.get('url'),
                "publishedAt": article.get('publishedAt'),
                "source": article.get('source', {}).get('name'),
                "scraped_at": datetime.now().isoformat()
            }

            filename = f"{OUTPUT_DIR}/article_{idx}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(full_article_data, f, indent=2, ensure_ascii=False)
            saved_files.append(filename)
            print(f"✅ Saved: {filename}")

        return saved_files

    except Exception as e:
        print(f"❌ Error fetching news: {e}")
        return []

# ---- BUILD CONTEXT FOR ALL ARTICLES ----
def build_articles_context(articles):
    context = ""
    for idx, article in enumerate(articles, 1):
        title = article.get('title') or ''
        description = article.get('description') or ''
        full_text = article.get('full_text') or ''
        context += f"Article {idx}: {title}\n"
        context += f"Summary: {description[:500]}\n"
        context += f"Content: {full_text[:1000]}\n\n"
    return context

# ---- ANALYZE QUESTION WITH ALL ARTICLES ----
def analyze_with_groq(all_articles_context, question):
    prompt = f"""You are an intelligent news assistant.
Below are multiple news articles:

{all_articles_context}

Based on the above articles, answer the user's question:

QUESTION: {question}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Analysis failed: {str(e)}"

# ---- INTENT CHECK ----
def check_user_intent(user_input):
    prompt = f"""You are a control system.
Analyze the following user statement:

"{user_input}"

If the user wants to stop, exit, close the program, end the conversation, or terminate — respond ONLY with the single word: EXIT.
If the user wants to continue, respond ONLY with: CONTINUE.
NO extra words.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        decision = response.choices[0].message.content.strip()
        return decision
    except Exception as e:
        print(f"❌ Intent checking failed: {e}")
        return "CONTINUE"

# ---- DETECT IF FRESH NEWS NEEDED ----
def needs_new_fetch(user_question, articles_data):
    user_question_lower = user_question.lower()
    for article in articles_data:
        title = article.get('title', '').lower()
        if any(word in title for word in user_question_lower.split()):
            return False
    return True

# ---- CLEAN QUERY FROM USER SPEECH ----
def clean_query(raw_query):
    """Cleans user speech to extract the real search topic."""
    text = raw_query.lower()

    # Define phrases that indicate a request for news, to be removed
    request_phrases = [
        "what is the news about", "what's the news about", "what's new with",
        "tell me the news about", "tell me about", "find news about", "search for news about",
        "search for", "find", "news related to", "news on", "news about",
        "give me news about", "i want to know about", "i want to hear about",
        "what about", "get news on", "show me news about", "latest on",
        "i want listen a new topic", "give me news which is related to" # Added more specific phrase
    ]
    # Define common filler words to remove
    filler_words = ["okay", "please", "can you", "could you", "like", "uh", "um"]

    # Remove the longest matching request phrase first
    request_phrases.sort(key=len, reverse=True)
    for phrase in request_phrases:
        if text.startswith(phrase + " "):
            text = text[len(phrase):].strip()
            break # Stop after removing one starting phrase

    # Remove punctuation (allow letters, numbers, and spaces)
    text = re.sub(r'[^\w\s]', '', text)

    # Remove leading/trailing whitespace
    cleaned_query = text.strip()

    # Remove filler words from the beginning and end of the remaining query
    words = cleaned_query.split()
    # Remove leading filler words
    while words and words[0] in filler_words:
        words.pop(0)
    # Remove trailing filler words
    while words and words[-1] in filler_words:
        words.pop()

    cleaned_query = " ".join(words)

    # Handle potential duplicate words resulting from cleaning (like "sports sports")
    words = cleaned_query.split()
    cleaned_query = " ".join(sorted(set(words), key=words.index))

    # Fallback if cleaning results in empty string
    # If empty after cleaning, maybe return the original minus punctuation?
    # Or just return empty and let the calling function handle it.
    # Let's return empty for now, fetch_live_news handles empty query by getting top headlines.
    return cleaned_query if cleaned_query else ""

# ---- MAIN ----
def news_mode():
    print("📡 Welcome to Voice NewsBot 2.0!")
    speak("Fetching the latest top 3 news headlines for you.")

    # Initial fetch for top 3 news (no query)
    json_files = fetch_live_news(page_size=3) # Explicitly fetch 3

    if not json_files:
        speak("Sorry, I couldn't fetch the top news right now. Please try again later.")
        return # Exit news_mode if initial fetch fails

    articles_data = []
    for file in json_files:
        with open(file, 'r', encoding='utf-8') as f:
            articles_data.append(json.load(f))

    print("\n📰 Top 3 News Headlines:")
    speak("Here are the top 3 news headlines:")
    for idx, article in enumerate(articles_data, 1):
        speak(f"{idx}. {article.get('title')}")

    # Build initial context
    all_articles_context = build_articles_context(articles_data)
    current_topic = "Top Headlines" # Keep track of the current context

    # Conversation loop
    while True:
        print(f"\n🎤 Ask about '{current_topic}', request news on a new topic, or say 'quit'.")
        #speak(f"Ask about '{current_topic}', request news on a new topic, or say 'quit'.") # Re-enabled prompt
        user_question = listen()

        if not user_question:
            continue

        # Check for exit intent first
        decision = check_user_intent(user_question)
        if decision == "EXIT":
            print("\n👋 Exit intent detected. Leaving news mode.")
            speak("Okay, leaving news mode now. Goodbye!")
            return # Exit the news_mode function

        # Try to extract a specific topic from the user's request
        cleaned_topic_query = clean_query(user_question)
        print(f"DEBUG: Cleaned query for new topic: '{cleaned_topic_query}'")

        # Decide if a new fetch is needed
        # Simpler logic: Fetch if the cleaned query is not empty AND
        # it's different from the current topic (or if current topic is still the default).
        needs_fetch = (bool(cleaned_topic_query) and
                       (current_topic == "Top Headlines" or cleaned_topic_query != current_topic.lower()))

        if needs_fetch:
            print(f"\n🔄 Fetching news related to: '{cleaned_topic_query}'...")
            speak(f"Okay, looking for news about {cleaned_topic_query}.")
            # Pass the cleaned query to the API
            new_json_files = fetch_live_news(query=cleaned_topic_query, page_size=3)

            if new_json_files:
                # Update context if new articles were found
                articles_data = []
                for file in new_json_files:
                    with open(file, 'r', encoding='utf-8') as f:
                        articles_data.append(json.load(f))
                all_articles_context = build_articles_context(articles_data)
                # Use the cleaned query as the new topic name
                current_topic = cleaned_topic_query # Update the current topic

                print("\n📰 New Headlines:")
                speak(f"Here are the latest headlines about {current_topic}:")
                for idx, article in enumerate(articles_data, 1):
                    speak(f"{idx}. {article.get('title')}")

                # Analyze the original question against the NEW context
                # It might be better to just present the headlines and wait for the next question
                # instead of immediately analyzing the request that triggered the fetch.
                # Let's comment out the immediate analysis after fetch for now.
                # print("\n🤖 Analyzing your question against new articles...")
                # answer = analyze_with_groq(all_articles_context, user_question)
                answer = f"Presented the latest headlines about {current_topic}" # Placeholder answer after fetch

            else:
                # If fetch failed or returned no results for the topic
                speak(f"Sorry, I couldn't find specific news articles about {cleaned_topic_query}. We can continue discussing '{current_topic}'.")
                continue # Go back to the start of the loop to prompt the user again
        else:
            # If not a new topic request (cleaned query was empty or same as current topic),
            # analyze the question against current articles
            print("\n🤖 Analyzing your question against current articles...")
            answer = analyze_with_groq(all_articles_context, user_question) # Use original question

        # Speak the answer (either the analysis result or the placeholder after fetch)
        print("\n🧠 Answer:", answer)
        speak(answer)

        # Loop continues
