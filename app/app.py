import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from prometheus_client import start_http_server, Gauge, Counter, REGISTRY

from model import predict_sentiment

# Start Prometheus metrics server only once
if "server_started" not in st.session_state:
    try:
        start_http_server(8001)  # Metrics available at port 8001
    except OSError:
        pass  # Avoid "Address already in use" error on reruns
    st.session_state.server_started = True

# Define a request counter
if "request_count_metric" not in st.session_state:
    try:
        st.session_state.request_count_metric = Counter("ml_model_requests_total", "Total number of prediction requests", registry=REGISTRY)
    except ValueError:
        # Metric already exists, retrieve it instead
        st.session_state.request_count_metric = REGISTRY._names_to_collectors["ml_model_requests_total"]

# Define the Prometheus Gauge only once
if "accuracy_metric" not in st.session_state:
    try:
        st.session_state.accuracy_metric = Gauge("ml_model_accuracy", "User-reported model accuracy", registry=REGISTRY)
    except ValueError:
        # Metric already exists, retrieve it instead
        st.session_state.request_count_metric = REGISTRY._names_to_collectors["ml_model_accuracy"]

# Initialize session state variables
if "accuracy_history" not in st.session_state:
    st.session_state.accuracy_history = []
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = None
if "prediction_result" not in st.session_state:
    st.session_state.prediction_result = None
if "yes_count" not in st.session_state:
    st.session_state.yes_count = 0
if "no_count" not in st.session_state:
    st.session_state.no_count = 0

st.title("📊 Sentiment Analysis & Model Monitoring")

# --- Section 1: Sentiment Prediction ---
st.header("💬 Try It Out!")

user_input = st.text_area("Enter a sentence:", "I love this!")

if st.button("Analyze Sentiment"):
    # Increment the request count each time a prediction is made
    st.session_state.request_count_metric.inc()

    label, confidence = predict_sentiment(user_input)
    emoji = "😊" if label == "POSITIVE" else "😡" if label == "NEGATIVE" else "😐"

    st.session_state.prediction_result = {
        "label": label,
        "confidence": confidence,
        "emoji": emoji
    }
    st.session_state.feedback_given = None  # Reset feedback state after new prediction

# Show prediction result if available
if st.session_state.prediction_result:
    label = st.session_state.prediction_result["label"]
    confidence = st.session_state.prediction_result["confidence"]
    emoji = st.session_state.prediction_result["emoji"]

    st.success(f"Predicted Sentiment: {label} {emoji}")
    st.info(f"Confidence: {confidence:.2f}")

    # Show buttons only if no feedback has been given yet
    if st.session_state.feedback_given is None:
        st.write("### Was this prediction correct?")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Yes", key="yes_button"):
                st.session_state.accuracy_history.append((time.time(), 1))  # Correct prediction
                st.session_state.feedback_given = "yes"
                st.session_state.yes_count += 1  # Update Yes count

        with col2:
            if st.button("❌ No", key="no_button"):
                st.session_state.accuracy_history.append((time.time(), 0))  # Incorrect prediction
                st.session_state.feedback_given = "no"
                st.session_state.no_count += 1  # Update No count

# Show feedback message if feedback was given
if st.session_state.feedback_given == "yes":
    st.success("🙂 Yeah!")
elif st.session_state.feedback_given == "no":
    st.error("😞 We are sorry")

# Update Prometheus metric
if len(st.session_state.accuracy_history) > 0:
    avg_accuracy = sum(acc[1] for acc in st.session_state.accuracy_history) / len(st.session_state.accuracy_history)
    # Update accuracy based on user feedback
    st.session_state.accuracy_metric.set(avg_accuracy)
    st.success(f"📈 Model Accuracy: {avg_accuracy:.2%}")

# --- Section 2: Accuracy Trend Over Time ---
st.header("📊 Accuracy Monitoring")

if len(st.session_state.accuracy_history) > 1:
    # Convert timestamp to human-readable UTC datetime
    df = pd.DataFrame(st.session_state.accuracy_history, columns=["timestamp", "accuracy"])
    df["datetime_utc"] = pd.to_datetime(df["timestamp"], unit='s')

    # Plotly Line Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["datetime_utc"],
        y=df["accuracy"],
        mode='lines+markers',
        line=dict(color='blue'),
        marker=dict(size=8),
        name="Accuracy"
    ))
    fig.update_layout(
        title="Model Accuracy Over Time",
        xaxis_title="Date & UTC Time",
        yaxis_title="Accuracy",
        xaxis_tickformat='%Y-%m-%d %H:%M:%S',
        xaxis_tickangle=-45,
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Provide some feedback to see the accuracy trend.")

# --- Section 3: Yes vs. No Feedback Count ---
st.header("📊 Yes vs. No Feedback Count")

if st.session_state.yes_count > 0 or st.session_state.no_count > 0:
    feedback_counts = {"Yes": st.session_state.yes_count, "No": st.session_state.no_count}

    # Plotly Bar Chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(feedback_counts.keys()),
        y=list(feedback_counts.values()),
        marker_color=['green', 'red'],
        text=list(feedback_counts.values()),
        textposition='auto'
    ))
    fig.update_layout(
        title="Yes vs. No Responses",
        yaxis_title="Count",
        xaxis_title="Feedback",
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No feedback data yet. Give responses to see the chart.")
