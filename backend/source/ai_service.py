from transformers import pipeline
from email.utils import getaddresses

try:
    summarizer = pipeline(
        "summarization",
        model="sshleifer/distilbart-cnn-12-6"
    )
    print("INFO:        Summarization pipeline loaded successfully")
except Exception as e:
    print(f"ERROR:     Failed to load summarization pipeline:{e}")
    summarizer = None

def summarize_text(text:str)-> str:
    """
    Generates a summary for a given block of text.
    """
    if not summarizer:
        print("ERROR:       Summarizer not available")
        return "Summarization service is not available"
    

    max_chunk_size = 1024

    if len(text) < 100:
        return text

    try:
        summary_list = summarizer(
            text[:max_chunk_size],
            max_length = 150,
            min_length=30,
            do_sample=False
        )
        if summary_list:
            return summary_list[0]['summary_text']
        else:
            return "Could not generate summary"        
    except Exception as e:
        print(f"ERROR:    An error occurred during summarization: {e}")
        return "Error during summary generation."
    
# Define keywords for each category. This can be expanded and improved over time.
KEYWORD_CATEGORIES = {
    "Promotions": [
        "sale", "discount", "offer", "unsubscribe", "coupon", "deal", 
        "limited time", "free shipping", "shop now", "view collection", "save now"
    ],
    "Updates": [
        "update", "notification", "alert", "shipping", "delivery", "order", 
        "confirmation", "receipt", "invoice", "statement", "policy change"
    ],
    "Work": [
        "meeting", "report", "project", "deadline", "task", "agenda",
        "team", "collaboration", "document", "presentation", "feedback", "zoom"
    ],
    "Personal": [
        "happy birthday", "congratulations", "invitation", "family", "friend",
        "trip", "vacation", "photos", "event", "party"
    ],
    "Finance": [
        "bank", "payment", "invoice", "receipt", "statement", "due date",
        "credit card", "investment", "stock", "market update", "bill"
    ],
    "Social": [
        "linkedin", "facebook", "twitter", "instagram", "mentioned you", 
        "new post", "tagged you", "friend request", "new connection"
    ],
    "Newsletters": [
        "newsletter", "digest", "weekly", "daily", "monthly", "subscribe",
        "edition", "latest issue", "top stories"
    ]
}

def classify_email(text: str) -> str:
    """
    Classifies email text into a category based on keyword matching.
    """
    scores = {category: 0 for category in KEYWORD_CATEGORIES}
    
    # Convert text to lowercase for case-insensitive matching
    lower_text = text.lower()

    for category, keywords in KEYWORD_CATEGORIES.items():
        for keyword in keywords:
            if keyword in lower_text:
                scores[category] += 1
    
    # Find the category with the highest score
    # If no keywords are matched, the score for all will be 0
    max_score = 0
    best_category = "Uncategorized" # Default category
    for category, score in scores.items():
        if score > max_score:
            max_score = score
            best_category = category
            
    return best_category

HIGH_PRIORITY_KEYWORDS = ["urgent", "important", "action required", "response needed", "asap"]
LOW_PRIORITY_KEYWORDS = ["unsubscribe", "newsletter", "promotional", "advertisement", "sale"]

def calculate_priority_score(email_data: dict, user_email: str) -> int:
    """
    Calculates a priority score for an email based on a set of rules.
    """
    score = 0
    
    # Combine subject and body for keyword analysis
    subject = email_data.get("subject", "") or ""
    body = email_data.get("body", "") or ""
    full_text = f"{subject} {body}".lower()

    # Rule 1: High-priority keywords
    if any(keyword in full_text for keyword in HIGH_PRIORITY_KEYWORDS):
        score += 15

    # Rule 2: Low-priority keywords
    if any(keyword in full_text for keyword in LOW_PRIORITY_KEYWORDS):
        score -= 10
    
    # Rule 3: Was the user directly addressed?
    # The 'sender' field from our parser actually contains 'To', 'Cc', etc.
    # We need to parse it properly.
    sender_header = email_data.get("sender", "") or ""
    # getaddresses can parse headers like 'To', 'From', 'Cc'
    # We check if the user's email is in the list of recipients.
    # Note: The 'sender' from our parser is actually the 'From' header.
    # A more robust implementation would parse 'To' and 'Cc' headers separately.
    # For now, we'll simulate this by checking if the user's email is NOT the sender.
    # This is a proxy for "was this email sent TO me?".
    
    # A better approach requires parsing 'To' and 'Cc' headers in gmail_service.py
    # For now, we'll keep it simple. If the email is from someone else, give it points.
    if user_email.lower() not in sender_header.lower():
        score += 10

    # Rule 4: Does the email ask a question?
    if "?" in body:
        score += 5
        
    return score

ACTION_KEYWORDS = {
    "Schedule Event": ["schedule", "meeting", "call", "appointment", "zoom link", "calendar", "confirm a time"],
    # NOTE: We removed the generic "?" to make this more accurate
    "Reply Needed": ["feedback", "your thoughts", "let me know", "confirm", "are you available", "question is"],
    "For Your Information (FYI)": ["update", "fyi", "just so you know", "heads up", "announcement", "receipt", "confirmation"]
}

def determine_action(text: str, category: str) -> str | None:
    """
    Determines a suggested action for an email based on its category and keywords.
    """
    # Step 1: Use the category to exclude emails that don't need action.
    if category in ["Promotions", "Newsletters", "Social", "Updates"]:
        return "No Action Needed"

    lower_text = text.lower()

    # Step 2: Check for specific, high-confidence actions first.
    if any(keyword in lower_text for keyword in ACTION_KEYWORDS["Schedule Event"]):
        return "Schedule Event"
        
    if any(keyword in lower_text for keyword in ACTION_KEYWORDS["Reply Needed"]):
        return "Reply Needed"

    if any(keyword in lower_text for keyword in ACTION_KEYWORDS["For Your Information (FYI)"]):
        return "For Your Information (FYI)"

    # Step 3: If it's a Work or Personal email with no other keywords, it likely needs a reply.
    if category in ["Work", "Personal", "Finance"]:
        return "Reply Needed"

    return None
