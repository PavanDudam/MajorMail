from transformers import pipeline
from sentence_transformers import SentenceTransformer, util

# -----------------------------
# Load Models
# -----------------------------
try:
    summarizer = pipeline(
        "summarization",
        model="sshleifer/distilbart-cnn-12-6"
    )
    print("INFO: Summarization pipeline loaded successfully")
except Exception as e:
    print(f"ERROR: Failed to load summarization pipeline: {e}")
    summarizer = None

# Compact embedding model for semantic similarity
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# -----------------------------
# Summarization
# -----------------------------
def summarize_text(text: str) -> str:
    """Generates a summary for a given block of text."""
    if not summarizer:
        return "Summarization service is not available"
    
    if len(text) < 100:
        return text

    try:
        summary_list = summarizer(
            text[:1024],
            max_length=150,
            min_length=30,
            do_sample=False
        )
        return summary_list[0]['summary_text'] if summary_list else "Could not generate summary"
    except Exception as e:
        print(f"ERROR: Summarization failed: {e}")
        return "Error during summary generation."

# -----------------------------
# Categories (Semantic Classification)
# -----------------------------
CATEGORY_LABELS = {
    "Promotions": ["discount", "offer", "sale", "shopping"],
    "Updates": ["shipping update", "system alert", "policy change"],
    "Work": ["meeting", "project", "deadline", "report"],
    "Personal": ["family", "friend", "invitation", "holiday"],
    "Finance": ["bank", "invoice", "payment", "credit card"],
    "Social": ["facebook", "linkedin", "twitter", "instagram"],
    "Newsletters": ["newsletter", "digest", "weekly report"]
}

CATEGORY_EMBEDDINGS = {
    cat: embedding_model.encode(" ".join(words), convert_to_tensor=True)
    for cat, words in CATEGORY_LABELS.items()
}

def classify_email(text: str) -> str:
    """Semantic classification into categories."""
    email_embedding = embedding_model.encode(text, convert_to_tensor=True)
    best_category, best_score = "Uncategorized", -1
    for category, cat_embedding in CATEGORY_EMBEDDINGS.items():
        similarity = util.cos_sim(email_embedding, cat_embedding).item()
        if similarity > best_score:
            best_score = similarity
            best_category = category
    return best_category

# -----------------------------
# Priority Score
# -----------------------------
URGENCY_PROTOTYPES = embedding_model.encode(
    ["urgent matter", "as soon as possible", "immediate response required"],
    convert_to_tensor=True
)

def calculate_priority_score(email_data: dict, user_email: str) -> int:
    """Calculate semantic priority score."""
    text = f"{email_data.get('subject', '')} {email_data.get('body', '')}".lower()
    embedding = embedding_model.encode(text, convert_to_tensor=True)

    # Urgency similarity
    urgency_score = max(util.cos_sim(embedding, u).item() for u in URGENCY_PROTOTYPES)
    score = int(urgency_score * 20)  # scale 0–20

    # Directness (email not self-sent)
    sender = email_data.get("sender", "")
    if user_email.lower() not in sender.lower():
        score += 10

    # Question detection
    if "?" in text:
        score += 5

    return score

# -----------------------------
# Action Determination
# -----------------------------
ACTION_LABELS = {
    "Schedule Event": ["schedule meeting", "set up a call", "book appointment", "calendar invite"],
    "Reply Needed": ["please respond", "need your feedback", "can you confirm", "awaiting reply"],
    "For Your Information (FYI)": ["just so you know", "for your reference", "announcement", "fyi"],
    "No Action Needed": ["newsletter", "promotion", "thank you", "receipt"]
}

ACTION_EMBEDDINGS = {
    action: embedding_model.encode(" ".join(samples), convert_to_tensor=True)
    for action, samples in ACTION_LABELS.items()
}

def determine_action(text: str, category: str) -> str:
    """Suggest an action using semantic intent detection."""
    embedding = embedding_model.encode(text, convert_to_tensor=True)
    best_action, best_score = "No Action Needed", -1

    for action, act_embedding in ACTION_EMBEDDINGS.items():
        similarity = util.cos_sim(embedding, act_embedding).item()
        if similarity > best_score:
            best_score = similarity
            best_action = action

    # Fallback for important categories
    if best_score < 0.3 and category in ["Work", "Personal", "Finance"]:
        return "Reply Needed"

    return best_action

# -----------------------------
# Unified Email Processor
# -----------------------------
def process_email(email_data: dict, user_email: str) -> dict:
    """Run summarization, classification, priority scoring, and action detection in one step."""
    subject = email_data.get("subject", "") or ""
    body = email_data.get("body", "") or ""
    full_text = f"{subject} {body}"

    summary = summarize_text(full_text)
    category = classify_email(full_text)
    priority = calculate_priority_score(email_data, user_email)
    action = determine_action(full_text, category)

    return {
        "message_id": email_data.get("message_id"),
        "subject": subject,
        "sender": email_data.get("sender"),
        "summary": summary,
        "category": category,
        "priority_score": priority,
        "suggested_action": action,
        "received_at": email_data.get("received_at"),
    }
