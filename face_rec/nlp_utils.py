from transformers import pipeline
from better_profanity import profanity

nlp_pipeline = pipeline("text-classification", model="unitary/toxic-bert")

def is_offensive(text):
    if not text:
        return False
    if profanity.contains_profanity(text):
        return True
    result = nlp_pipeline(text[:512])[0]
    return result['label'].lower() in ["toxic", "insult", "threat", "obscene"] and result['score'] > 0.8
