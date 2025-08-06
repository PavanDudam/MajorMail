from transformers import pipeline


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