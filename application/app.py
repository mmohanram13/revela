"""
Revela Streamlit App
A clean, minimal UI for AI-powered chart and table analysis.
"""
import streamlit as st
from PIL import Image
import io

from config import config
from ollama_client import ollama_client


# Page configuration
st.set_page_config(
    page_title="Revela - AI Insights",
    page_icon="images/logo.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for minimal, clean UI
st.markdown("""
    <style>
    /* Main container */
    .main {
        padding-top: 2rem;
    }
    
    /* Header styling */
    h1 {
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    /* Alert box styling */
    .alert-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        margin-bottom: 1.5rem;
    }
    
    .alert-box-success {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #28a745;
        margin-bottom: 1.5rem;
    }
    
    /* Button styling */
    .stButton > button {
        width: 100%;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    
    /* Text area styling */
    .stTextArea > div > div > textarea {
        border-radius: 0.5rem;
    }
    
    /* File uploader styling */
    .stFileUploader {
        border-radius: 0.5rem;
    }
    
    /* Remove extra padding */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)


def check_extension_installed() -> bool:
    """
    Check if Revela extension is installed.
    This is a placeholder - actual detection would require JavaScript bridge.
    """
    # Check session state for manual confirmation
    if "extension_confirmed" in st.session_state:
        return st.session_state.extension_confirmed
    return False


def display_extension_alert():
    """Display alert if extension is not installed."""
    st.markdown("""
        <div class="alert-box">
            <strong>⚠️ Extension Not Detected</strong><br>
            Please install the <strong>Revela Chrome Extension</strong> to get AI insights 
            directly on any chart or table while browsing.
            <br><br>
            <a href="chrome://extensions/" target="_blank">Manage Chrome Extensions →</a>
        </div>
    """, unsafe_allow_html=True)
    
    # Manual confirmation button
    if st.button("✓ I have installed the extension"):
        st.session_state.extension_confirmed = True
        st.rerun()


def display_extension_confirmed():
    """Display success message when extension is confirmed."""
    st.markdown("""
        <div class="alert-box-success">
            <strong>✓ Extension Detected</strong><br>
            You're all set! Use the extension while browsing or analyze images below.
        </div>
    """, unsafe_allow_html=True)


def process_image(uploaded_file) -> Image.Image:
    """Process uploaded file and return PIL Image."""
    try:
        image = Image.open(uploaded_file)
        return image
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None


def main():
    """Main application function."""
    
    # Header
    st.title("🔍 Revela")
    st.caption("AI-powered chart and table analysis")
    
    # Check Ollama connection
    if not ollama_client.check_health():
        st.error("⚠️ Cannot connect to Ollama service. Please check your configuration.")
        st.stop()
    
    # Extension detection
    st.markdown("---")
    extension_installed = check_extension_installed()
    
    if extension_installed:
        display_extension_confirmed()
    else:
        display_extension_alert()
    
    st.markdown("---")
    
    # Main input section
    st.subheader("Analyze Chart or Table")
    
    # User prompt
    prompt = st.text_area(
        "Enter your question or analysis request:",
        placeholder="e.g., What trends do you see in this chart? Summarize this table data...",
        height=100,
        key="user_prompt"
    )
    
    # Image input section
    st.markdown("### Add Image (Optional)")
    
    # Create two columns for different input methods
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Upload Image**")
        uploaded_file = st.file_uploader(
            "Choose an image",
            type=["png", "jpg", "jpeg"],
            label_visibility="collapsed"
        )
    
    with col2:
        st.markdown("**Paste Image**")
        st.caption("Use Ctrl+V in the file uploader above")
    
    # Display uploaded image
    image = None
    if uploaded_file:
        image = process_image(uploaded_file)
        if image:
            st.image(image, caption="Uploaded Image", use_container_width=True)
    
    # Submit button
    st.markdown("---")
    if st.button("🚀 Analyze", type="primary"):
        if not prompt:
            st.warning("Please enter a question or analysis request.")
        else:
            # Show spinner while processing
            with st.spinner("Analyzing..."):
                # Create a placeholder for streaming response
                response_placeholder = st.empty()
                full_response = ""
                
                try:
                    # Stream response from Ollama
                    for chunk in ollama_client.generate(prompt, image=image):
                        full_response += chunk
                        response_placeholder.markdown(full_response)
                    
                    # Success message
                    st.success("Analysis complete!")
                    
                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.caption(f"Running in **{config.environment}** mode | Model: **{config.ollama_model}**")


if __name__ == "__main__":
    main()
