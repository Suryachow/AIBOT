import requests
import re
import os
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
# Note: sklearn import is needed to prevent DLL load failed error for torch/faiss on some Windows envs
import sklearn

import faiss
from sentence_transformers import SentenceTransformer, CrossEncoder

# ==========================================================
# CONFIG
# ==========================================================
# Load environment variables
load_dotenv('ppx.env')

BASE_URL = "https://neuraltrix-ai-v1.vercel.app/"
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

MAX_PAGES = 3
DEVICE = "cpu"

# ==========================================================
# FLASK APP
# ==========================================================
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

# ==========================================================
# WEB CRAWLER
# ==========================================================
def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s.,!?;:()\-]", " ", text)
    return text.strip()


def crawl_website(start_url):
    visited = set()
    pages = []

    queue = [start_url]

    while queue and len(visited) < MAX_PAGES:
        url = queue.pop(0)
        if url in visited:
            continue

        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            visited.add(url)

            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()

            text = clean_text(soup.get_text())
            if len(text) > 200:
                pages.append(text)

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith("/") or BASE_URL in href:
                    full = BASE_URL + href if href.startswith("/") else href
                    if full not in visited:
                        queue.append(full)

        except:
            continue

    return pages


# ==========================================================
# BUILD KNOWLEDGE BASE
# ==========================================================
print("🔍 Crawling website...")
documents = crawl_website(BASE_URL)
if not documents:
    print("⚠️ Crawling returned no content (SPA detected?). Using fallback data.")
    documents = [
        "NeuralTrix AI is a company located in Guntur, Andhra Pradesh, India (N-Block, VFSTR).",
        "It offers AI & LLM Solutions (Custom AI models, LLM integration), Engineering & Automation (Software development, automation systems), and Data & Cloud Services (Data analytics, BI dashboards, cloud migration).",
        "Contact NeuralTrix AI: info@neuraltrixai.com or +91 8142438759. The website is currently under development.",
        "Important Distinction: Neuralix AI is a DIFFERENT company based in Houston/Bangalore. NeuralTrix AI is the Guntur-based company.",
        "NeuralTrix AI specializes in custom AI models, large language model integration, software development, and automation systems."
    ]
print(f"🔎 Building embeddings for {len(documents)} documents...")
embedder = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
embeddings = embedder.encode(documents, normalize_embeddings=True)

index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(embeddings)

# ==========================================================
# INTENT HANDLER
# ==========================================================
def handle_user_query(query):
    q = query.lower().strip()

    # -------- BASIC INTENTS --------
    # Greetings - handle variations like "hiii", "helloo", etc.
    if q in ["hi", "hello", "hey"] or q.startswith(("hi", "hello", "hey")):
        return "Hi! 👋 How can I help you to know about Neuraltrix AI?"

    if "who are you" in q or "what are you" in q or "about neuraltrix" in q:
        return (
            "I'm **Neuraltrix AI**, your intelligent assistant! 🤖\n\n"
            "Neuraltrix AI is a Guntur-based IT services company specializing in "
            "AI, LLM solutions, automation, and digital transformation."
        )

    if "contact" in q or "email" in q or "phone" in q or "reach" in q:
        return (
            "You can contact Neuraltrix AI at:\n\n"
            "📧 **Email:** info@neuraltrixai.com\n"
            "📞 **Phone:** +91 8142438759"
        )

    # -------- SEMANTIC SEARCH --------
    query_vec = embedder.encode([query], normalize_embeddings=True)
    scores, ids = index.search(query_vec, 3)

    # Safely retrieve documents
    results = []
    for i in ids[0]:
        if 0 <= i < len(documents):
            results.append(documents[i])
            
    context = " ".join(results)

    # Call LLM (Perplexity)
    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "sonar",
                "messages": [
                    {
                        "role": "system", 
                        "content": (
                            "You are Neuraltrix AI assistant. Provide clear, concise, and professional responses. "
                            "Use the provided context to answer questions about Neuraltrix AI services, team, and contact information. "
                            "Make sure to distinguish 'NeuralTrix AI' (Guntur based) from 'Neuralix AI' (Houston/Bangalore based) if relevant. "
                            "Prioritize the provided context over external knowledge if there is a conflict. "
                            "Format your responses with markdown for better readability (use **bold** for emphasis, bullet points for lists). "
                            "Keep responses brief and to the point. Do NOT include citation numbers like [1], [2], etc."
                        )
                    },
                    {
                        "role": "user", 
                        "content": f"Context: {context}\n\nQuestion: {query}"
                    }
                ]
            },
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"Perplexity API Error: Status {response.status_code}, Response: {response.text}")
            return "I'm having trouble processing your request right now. Please try again or ask about Neuraltrix AI services."
            
    except Exception as e:
        print(f"Exception in handle_user_query: {str(e)}")
        return "I apologize, but I'm experiencing technical difficulties. Please try asking about Neuraltrix AI services, team, or contact information."

# ==========================================================
# API ENDPOINT
# ==========================================================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("question", "")

    if not question:
        return jsonify({"answer": "Please enter a question."})

    answer = handle_user_query(question)
    return jsonify({"answer": answer})


# ==========================================================
# RUN SERVER
# ==========================================================
if __name__ == "__main__":
    print("🚀 Neuraltrix AI backend running...")
    app.run(host="0.0.0.0", port=8000)
