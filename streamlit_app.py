from __future__ import annotations

import json

import requests
import streamlit as st

from app.core.config import get_settings

settings = get_settings()
endpoint_url = f"{settings.streamlit_backend_url.rstrip('/')}/v1/analyse-document"

st.set_page_config(page_title="KairoPact-assesment", layout="centered")
st.title("Document Analysis")
st.write("Upload a TXT or PDF document, ask a question, and inspect the structured JSON response.")

uploaded_file = st.file_uploader("Document", type=["pdf", "txt"])
query = st.text_input("Query", placeholder="What are the main risks in this document?")

if st.button("Analyse", type="primary"):
    if uploaded_file is None:
        st.warning("Upload a document before running the analysis.")
    elif not query.strip():
        st.warning("Enter a query before running the analysis.")
    else:
        with st.spinner("Calling FastAPI..."):
            response = requests.post(
                endpoint_url,
                files={
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type or "text/plain",
                    )
                },
                data={"query": query},
                timeout=120,
            )

        if response.ok:
            payload = response.json()
            print(json.dumps(payload, indent=2))

            st.subheader("Summary")
            st.write(payload["summary"])

            st.subheader("Flags")
            if payload["flags"]:
                for flag in payload["flags"]:
                    st.write(f"- {flag}")
            else:
                st.write("No flags returned.")

            with st.expander("Debug JSON"):
                st.json(payload)
        else:
            st.error(f"API error {response.status_code}: {response.text}")
