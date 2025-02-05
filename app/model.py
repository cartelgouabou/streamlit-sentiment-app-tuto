from transformers import pipeline

# Load sentiment analysis model
sentiment_pipeline = pipeline("sentiment-analysis")

def predict_sentiment(text):
    """Predict sentiment using a pre-trained NLP model."""
    result = sentiment_pipeline(text)[0]
    return result['label'], result['score']
