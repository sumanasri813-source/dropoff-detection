from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

from src.api.prediction_service import (
    FEATURE_KEYS,
    load_decision_threshold,
    load_model,
    load_risk_levels,
    predict_batch,
    predict_one,
    validate_payload,
)


st.set_page_config(
    page_title="Silent User Drop-Off Detection",
    page_icon="ML",
    layout="wide",
)


@st.cache_resource
def get_model() -> Any:
    return load_model("models/final_model.pkl")


@st.cache_data
def load_evaluation_metrics() -> Dict[str, Any]:
    metrics_path = Path("results/evaluation_metrics.json")
    if metrics_path.exists():
        return json.loads(metrics_path.read_text(encoding="utf-8"))
    return {}


@st.cache_data
def load_model_comparison() -> pd.DataFrame:
    path = Path("results/model_comparison.csv")
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data
def load_threshold_analysis() -> pd.DataFrame:
    path = Path("results/threshold_analysis.csv")
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def render_header() -> None:
    st.title("Detection of Silent User Drop-Off")
    st.caption("Machine Learning dashboard for risk scoring, evaluation tracking, and actionable retention insights.")


def render_sidebar_context() -> None:
    st.sidebar.header("Model Context")
    threshold = load_decision_threshold()
    st.sidebar.metric("Decision Threshold", f"{threshold:.2f}")

    risk_levels = load_risk_levels()
    st.sidebar.write("Risk bands")
    st.sidebar.write(
        {
            "high >=": risk_levels["high"],
            "medium >=": risk_levels["medium"],
            "low >=": risk_levels["low"],
        }
    )

    eval_payload = load_evaluation_metrics()
    metrics = eval_payload.get("metrics", {}) if isinstance(eval_payload, dict) else {}
    if metrics:
        st.sidebar.subheader("Latest Evaluation")
        st.sidebar.metric("ROC-AUC", f"{metrics.get('roc_auc', 0):.4f}")
        st.sidebar.metric("F1", f"{metrics.get('f1', 0):.4f}")
        st.sidebar.metric("Business Value", f"{metrics.get('business_value', 0):.0f}")


def render_single_prediction_tab(model: Any) -> None:
    st.subheader("Single User Prediction")

    with st.form("single_predict_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            days_signup_age = st.number_input("Days Since Signup", min_value=0.0, value=250.0)
            recency_days = st.number_input("Recency Days", min_value=0.0, value=45.0)
            frequency_total = st.number_input("Total Activity Count", min_value=0.0, value=9.0)
        with c2:
            session_duration_avg = st.number_input("Avg Session Duration (min)", min_value=0.0, value=6.5)
            feature_count_used = st.number_input("Feature Count Used", min_value=0.0, value=2.0)
        with c3:
            device_type = st.selectbox("Device Type", ["mobile", "desktop", "tablet"])
            os_type = st.selectbox("OS Type", ["android", "ios", "windows", "mac", "linux"])
            user_segment = st.selectbox("User Segment", ["free", "trial", "premium"])
            region = st.selectbox("Region", ["north", "south", "east", "west"])

        submit = st.form_submit_button("Predict Drop-Off Risk")

    if submit:
        payload = {
            "days_signup_age": days_signup_age,
            "recency_days": recency_days,
            "frequency_total": frequency_total,
            "session_duration_avg": session_duration_avg,
            "feature_count_used": feature_count_used,
            "device_type": device_type,
            "os_type": os_type,
            "user_segment": user_segment,
            "region": region,
        }

        ok, message = validate_payload(payload)
        if not ok:
            st.error(message)
            return

        threshold = load_decision_threshold()
        risk_levels = load_risk_levels()
        result = predict_one(model, payload, threshold, risk_levels)

        m1, m2, m3 = st.columns(3)
        m1.metric("Drop-Off Probability", f"{result['dropoff_probability']:.4f}")
        m2.metric("Predicted Label", str(result["predicted_label"]))
        m3.metric("Risk Level", result["risk_level"].upper())

        if result["risk_level"] == "high":
            st.warning("High-risk user detected. Recommended action: immediate retention campaign.")
        elif result["risk_level"] == "medium":
            st.info("Medium-risk user detected. Recommended action: personalized in-app nudges.")
        else:
            st.success("Low-risk user detected. Recommended action: monitor and continue engagement.")


def render_batch_tab(model: Any) -> None:
    st.subheader("Batch Prediction (CSV)")
    st.write("Upload a CSV with required fields:")
    st.code(", ".join(FEATURE_KEYS), language="text")

    upload = st.file_uploader("Upload CSV", type=["csv"])
    if upload is None:
        return

    df = pd.read_csv(upload)
    st.write("Preview")
    st.dataframe(df.head(20), use_container_width=True)

    run_batch = st.button("Run Batch Scoring")
    if not run_batch:
        return

    records: List[Dict[str, Any]] = df.to_dict(orient="records") # pyright: ignore[reportAssignmentType]
    threshold = load_decision_threshold()
    risk_levels = load_risk_levels()

    result = predict_batch(model, records, threshold, risk_levels)

    st.write("Batch Summary")
    s1, s2, s3 = st.columns(3)
    s1.metric("Total Records", result["total_records"])
    s2.metric("Success", result["successful_predictions"])
    s3.metric("Failed", result["failed_predictions"])

    pred_df = pd.DataFrame(result["predictions"])
    if not pred_df.empty:
        st.write("Prediction Results")
        st.dataframe(pred_df, use_container_width=True)
        st.download_button(
            label="Download Predictions CSV",
            data=pred_df.to_csv(index=False).encode("utf-8"),
            file_name="predictions_output.csv",
            mime="text/csv",
        )

        chart = px.histogram(
            pred_df,
            x="risk_level",
            color="risk_level",
            title="Risk-Level Distribution",
            category_orders={"risk_level": ["low", "medium", "high"]},
        )
        st.plotly_chart(chart, use_container_width=True)

    err_df = pd.DataFrame(result["errors"])
    if not err_df.empty:
        st.write("Validation Errors")
        st.dataframe(err_df, use_container_width=True)


def render_metrics_tab() -> None:
    st.subheader("Model Evaluation Dashboard")

    comparison_df = load_model_comparison()
    if not comparison_df.empty:
        st.write("Model Comparison")
        st.dataframe(comparison_df, use_container_width=True)

        score_chart = px.bar(
            comparison_df,
            x="model",
            y=["roc_auc", "f1", "precision", "recall"],
            barmode="group",
            title="Model Performance Comparison",
        )
        st.plotly_chart(score_chart, use_container_width=True)

    threshold_df = load_threshold_analysis()
    if not threshold_df.empty:
        st.write("Threshold Analysis")
        st.dataframe(threshold_df, use_container_width=True)

        line = px.line(
            threshold_df.sort_values("threshold"),
            x="threshold",
            y=["f1", "precision", "recall", "business_value"],
            markers=True,
            title="Threshold vs Metrics",
        )
        st.plotly_chart(line, use_container_width=True)


def main() -> None:
    render_header()
    render_sidebar_context()

    try:
        model = get_model()
    except Exception as exc:
        st.error(f"Failed to load model: {exc}")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["Single Prediction", "Batch Prediction", "Metrics"])
    with tab1:
        render_single_prediction_tab(model)
    with tab2:
        render_batch_tab(model)
    with tab3:
        render_metrics_tab()


if __name__ == "__main__":
    main()
