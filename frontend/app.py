import streamlit as st
import requests
import os
from dotenv import load_dotenv
import time

load_dotenv()

st.set_page_config(
    page_title="Free PDF Summarizer",
    page_icon="📄",
    layout="wide"
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def main():
    st.title("📄 Free AI PDF Summarizer")
    st.markdown("**100% Free & Open Source** - Upload a PDF and get instant AI-powered summaries with page references.")
    
    # Sidebar with free model info
    with st.sidebar:
        st.header("🆓 Free & Open Source")
        st.markdown("""
        **Powered by:**
        - 🤗 Hugging Face Models
        - 🦙 Ollama (Local)
        - 📚 Sentence Transformers
        
        **No API keys required!**
        **No usage limits!**
        **Completely free!**
        """)
        
        st.info("For best results, install Ollama locally for faster and better summaries.")
    
    # File upload
    st.subheader("Upload your PDF")
    uploaded_file = st.file_uploader(
        "Choose a PDF file", 
        type="pdf",
        help="Upload any PDF document"
    )
    
    if uploaded_file is not None:
        # Display file info
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Filename:** {uploaded_file.name}")
        with col2:
            st.write(f"**Size:** {uploaded_file.size / 1024:.1f} KB")
        
        # Summarize button
        if st.button("🚀 Generate Free Summary", type="primary"):
            with st.spinner("AI is analyzing your document with free models... This may take a bit longer."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    response = requests.post(f"{BACKEND_URL}/upload-pdf/", files=files, timeout=120)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        if result["success"]:
                            st.success(f"✅ Free summary generated from {result['total_pages']} pages!")
                            
                            # Display summary
                            st.subheader("📋 AI Summary (Free Model)")
                            st.markdown(result["summary"])
                            
                            # Download option
                            st.download_button(
                                label="📥 Download Summary",
                                data=result["summary"],
                                file_name=f"free_summary_{uploaded_file.name}.txt",
                                mime="text/plain"
                            )
                        else:
                            st.error(f"Error: {result.get('error', 'Unknown error')}")
                    else:
                        error_detail = response.json().get('detail', 'Unknown error')
                        st.error(f"Backend Error: {error_detail}")
                        
                except requests.exceptions.ConnectionError:
                    st.error("""
                    ❌ Cannot connect to backend server. 
                    
                    **To fix this:**
                    1. Make sure the backend is running: `uvicorn main:app --reload --port 8000`
                    2. Check if port 8000 is available
                    """)
                except requests.exceptions.Timeout:
                    st.warning("""
                    ⏳ Summary is taking longer than expected with free models. 
                    This is normal for open-source models.
                    """)
                except Exception as e:
                    st.error(f"❌ Unexpected error: {str(e)}")
    
    # Instructions for better performance
    with st.expander("🚀 For Better Performance (Optional)"):
        st.markdown("""
        **Install Ollama for local, faster summaries:**
        
        ```bash
        # On Mac/Linux
        curl -fsSL https://ollama.ai/install.sh | sh
        ollama pull llama2:7b
        
        # On Windows
        # Download from https://ollama.ai/download
        ```
        
        **Benefits of Ollama:**
        - Faster responses
        - No internet required
        - Better quality summaries
        - Complete privacy
        """)

# if __name__ == "__main__":
#     main()