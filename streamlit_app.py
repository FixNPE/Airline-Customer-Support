"""
Streamlit UI for Airline Customer Support System

This module provides a user-friendly web interface for interacting with 
the airline customer support backend. Users can enter queries, get responses,
and view customer context information.
"""

import streamlit as st
import requests
import json
from typing import Optional, Dict, Any
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Airline Customer Support",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Styling
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        padding: 20px 0;
    }
    .query-input {
        margin: 20px 0;
    }
    .response-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 8px;
        margin: 15px 0;
        border-left: 5px solid #1f77b4;
    }
    .success-box {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #28a745;
        margin: 10px 0;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #dc3545;
        margin: 10px 0;
    }
    .info-box {
        background-color: #e7f3ff;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #0066cc;
        margin: 10px 0;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #ddd;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)


class AirlineSupportClient:
    """Client for interacting with the Airline Support API"""
    
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.session = requests.Session()
    
    def health_check(self) -> bool:
        """Check if the backend is available"""
        try:
            response = self.session.get(
                f"{self.api_base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def send_query(
        self,
        query: str,
        customer_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a support query to the backend"""
        try:
            payload = {
                "query": query,
                "customer_id": customer_id,
                "context": context
            }
            
            response = self.session.post(
                f"{self.api_base_url}/support/query",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}",
                    "details": response.text
                }
        except requests.Timeout:
            return {
                "success": False,
                "error": "Request timeout",
                "details": "The backend took too long to respond. Please try again."
            }
        except requests.ConnectionError:
            return {
                "success": False,
                "error": "Connection Error",
                "details": f"Could not connect to {self.api_base_url}. Make sure the backend is running."
            }
        except Exception as e:
            return {
                "success": False,
                "error": "Unexpected Error",
                "details": str(e)
            }
    
    def send_batch_queries(
        self,
        queries: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Send multiple queries for batch processing"""
        try:
            response = self.session.post(
                f"{self.api_base_url}/support/batch",
                json=queries,
                timeout=60
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}",
                    "details": response.text
                }
        except Exception as e:
            return {
                "success": False,
                "error": "Batch processing error",
                "details": str(e)
            }


def initialize_session_state():
    """Initialize Streamlit session state"""
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "api_client" not in st.session_state:
        st.session_state.api_client = None
    if "backend_status" not in st.session_state:
        st.session_state.backend_status = False
    if "customer_id" not in st.session_state:
        st.session_state.customer_id = ""


def display_header():
    """Display the main header and title"""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("<h1 class='main-header'>✈️ Airline Customer Support System</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>AI-Powered Support Interface</p>", unsafe_allow_html=True)
    with col2:
        st.markdown("", unsafe_allow_html=True)


def display_sidebar_config() -> str:
    """Display sidebar configuration and return API URL"""
    st.sidebar.markdown("## ⚙️ Configuration")
    
    # API URL configuration
    default_url = st.secrets.get("api_base_url", "http://localhost:8000") if "api_base_url" in st.secrets else "http://localhost:8000"
    api_url = st.sidebar.text_input(
        "Backend API URL",
        value=default_url,
        help="URL of the FastAPI backend server"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 📚 Quick Guide")
    st.sidebar.markdown("""
    **How to use:**
    1. Enter your customer ID (optional)
    2. Type your question or issue
    3. Click 'Send Query' to get a response
    4. View the conversation history
    
    **Example Queries:**
    - How do I change my flight date?
    - What's your baggage policy?
    - Can I get a refund?
    - How do I check in?
    - What are your meal preferences?
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🔧 Features")
    st.sidebar.markdown("""
    - **Real-time responses** from AI-powered backend
    - **Conversation history** tracking
    - **Customer context** awareness
    - **Batch processing** for multiple queries
    - **Response analytics** with confidence scores
    """)
    
    return api_url


def display_backend_status(client: AirlineSupportClient, api_url: str):
    """Display backend health status"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if client.health_check():
            st.success("✅ Backend Connected")
            st.session_state.backend_status = True
        else:
            st.error("❌ Backend Offline")
            st.session_state.backend_status = False
    
    with col2:
        st.info(f"🔗 API: {api_url}")
    
    with col3:
        st.metric("Status", "Ready" if st.session_state.backend_status else "Unavailable")


def display_customer_info_section():
    """Display customer information input section"""
    st.markdown("### 👤 Customer Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        customer_id = st.text_input(
            "Customer ID (optional)",
            value=st.session_state.customer_id,
            placeholder="e.g., CUST123",
            help="Your unique customer identifier for personalized responses"
        )
        st.session_state.customer_id = customer_id
    
    with col2:
        booking_id = st.text_input(
            "Booking ID (optional)",
            placeholder="e.g., BK12345",
            help="Your flight booking reference"
        )
    
    return {
        "customer_id": customer_id,
        "booking_id": booking_id
    }


def display_query_input_section() -> tuple[str, Dict]:
    """Display query input section"""
    st.markdown("### 💬 Your Query")
    
    # Text area for query input
    query_text = st.text_area(
        "Enter your question or issue:",
        placeholder="e.g., How can I change my flight date? I need to reschedule my trip.",
        height=100,
        help="Type your airline-related question or issue here"
    )
    
    # Query category selector
    query_category = st.selectbox(
        "Query Category (for context)",
        [
            "General Inquiry",
            "Booking/Reservation",
            "Flight Status",
            "Baggage & Policies",
            "Refunds & Cancellations",
            "Seat Selection",
            "Check-in",
            "Special Assistance",
            "Other"
        ]
    )
    
    context = {
        "category": query_category,
        "timestamp": datetime.now().isoformat()
    }
    
    return query_text, context


def display_response(response_data: Dict[str, Any]):
    """Display the API response in a user-friendly format"""
    st.markdown("### 📋 Response")
    
    if not response_data.get("success"):
        st.markdown(f"""
        <div class='error-box'>
            <strong>❌ Error: {response_data.get('error', 'Unknown error')}</strong><br>
            {response_data.get('details', 'No additional details available')}
        </div>
        """, unsafe_allow_html=True)
        return
    
    data = response_data.get("data", {})
    
    # Display main response
    st.markdown(f"""
    <div class='response-box'>
        <strong>Support Agent Response:</strong><br>
        {data.get('response', 'No response available')}
    </div>
    """, unsafe_allow_html=True)
    
    # Display status
    status = data.get('status', 'unknown')
    if status == 'success':
        st.markdown(f"""
        <div class='success-box'>
            ✅ <strong>Status:</strong> {status.upper()}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='info-box'>
            ℹ️ <strong>Status:</strong> {status}
        </div>
        """, unsafe_allow_html=True)
    
    # Display suggested actions if available
    if data.get('suggested_actions'):
        st.markdown("#### 🎯 Suggested Next Steps:")
        for action in data.get('suggested_actions', []):
            st.markdown(f"- {action}")
    
    # Display confidence score if available
    if data.get('confidence_score'):
        confidence = data.get('confidence_score', 0)
        st.progress(min(confidence, 1.0))
        st.markdown(f"Confidence Score: **{confidence:.0%}**")


def display_conversation_history():
    """Display conversation history"""
    if not st.session_state.conversation_history:
        st.info("No conversation history yet. Start by entering a query above.")
        return
    
    st.markdown("### 📜 Conversation History")
    
    for i, message in enumerate(st.session_state.conversation_history, 1):
        with st.expander(f"Query {i} - {message.get('timestamp', 'N/A')}"):
            st.markdown(f"**Query:** {message.get('query', 'N/A')}")
            
            if message.get('customer_id'):
                st.markdown(f"**Customer ID:** {message.get('customer_id')}")
            
            if message.get('category'):
                st.markdown(f"**Category:** {message.get('category')}")
            
            st.markdown(f"**Response:** {message.get('response', 'N/A')}")
            
            if message.get('confidence_score'):
                st.markdown(f"**Confidence:** {message.get('confidence_score'):.0%}")


def display_batch_processor():
    """Display batch query processor"""
    st.markdown("## 📦 Batch Query Processor")
    
    with st.expander("Process Multiple Queries", expanded=False):
        st.info("Upload or enter multiple customer support queries for batch processing")
        
        # Sample batch queries
        sample_queries = """[
    {"query": "How do I check my booking status?", "customer_id": "CUST001"},
    {"query": "What is your baggage allowance?", "customer_id": "CUST002"},
    {"query": "Can I change my seat?", "customer_id": "CUST003"}
]"""
        
        batch_input = st.text_area(
            "Enter queries as JSON array",
            value=sample_queries,
            height=150,
            help="Queries should be a JSON array with 'query' and optional 'customer_id'"
        )
        
        if st.button("Process Batch", key="batch_button"):
            if not st.session_state.backend_status:
                st.error("Backend is not available. Please check the connection.")
                return
            
            try:
                queries = json.loads(batch_input)
                
                with st.spinner("Processing batch queries..."):
                    result = st.session_state.api_client.send_batch_queries(queries)
                
                if result.get('success'):
                    st.success("✅ Batch processing completed!")
                    
                    batch_data = result.get('data', {})
                    st.markdown(f"**Total Processed:** {batch_data.get('total_processed', 0)}")
                    
                    # Display results in a table
                    results = batch_data.get('results', [])
                    if results:
                        st.markdown("#### Results:")
                        for idx, res in enumerate(results, 1):
                            with st.expander(f"Result {idx} - {res.get('customer_id', 'N/A')}"):
                                st.markdown(f"**Query:** {res.get('query')}")
                                st.markdown(f"**Response:** {res.get('response')}")
                                st.markdown(f"**Status:** {res.get('status')}")
                else:
                    st.error(f"Error: {result.get('error')}")
                    st.markdown(result.get('details'))
            
            except json.JSONDecodeError:
                st.error("Invalid JSON format. Please check your input.")


def main():
    """Main application function"""
    # Initialize session state
    initialize_session_state()
    
    # Display header
    display_header()
    
    # Get API configuration from sidebar
    api_url = display_sidebar_config()
    
    # Initialize API client
    if st.session_state.api_client is None or st.session_state.api_client.api_base_url != api_url:
        st.session_state.api_client = AirlineSupportClient(api_url)
    
    # Display backend status
    display_backend_status(st.session_state.api_client, api_url)
    
    if not st.session_state.backend_status:
        st.warning("⚠️ The backend server is not available. Please ensure the FastAPI server is running.")
        st.info(f"Start the backend with: `python main.py` or `uvicorn main:app --reload`")
        st.stop()
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["💬 Support Chat", "📦 Batch Processing", "ℹ️ Info"])
    
    with tab1:
        st.markdown("---")
        
        # Customer information section
        customer_info = display_customer_info_section()
        
        st.markdown("---")
        
        # Query input section
        query_text, context = display_query_input_section()
        context.update(customer_info)
        
        st.markdown("---")
        
        # Submit button
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🚀 Send Query", use_container_width=True):
                if not query_text.strip():
                    st.error("Please enter a query before submitting.")
                else:
                    with st.spinner("Processing your query..."):
                        response = st.session_state.api_client.send_query(
                            query=query_text,
                            customer_id=customer_info.get('customer_id'),
                            context=context
                        )
                        
                        # Display response
                        display_response(response)
                        
                        # Add to conversation history
                        if response.get('success'):
                            data = response.get('data', {})
                            st.session_state.conversation_history.append({
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'query': query_text,
                                'customer_id': customer_info.get('customer_id'),
                                'category': context.get('category'),
                                'response': data.get('response'),
                                'confidence_score': data.get('confidence_score')
                            })
        
        with col2:
            if st.button("🔄 Clear History", use_container_width=True):
                st.session_state.conversation_history = []
                st.success("Conversation history cleared!")
                st.rerun()
        
        st.markdown("---")
        
        # Display conversation history
        display_conversation_history()
    
    with tab2:
        display_batch_processor()
    
    with tab3:
        st.markdown("""
        ## 📖 About This System
        
        This is an AI-powered airline customer support interface built with:
        - **Streamlit**: User-friendly web interface
        - **FastAPI**: Backend API server
        - **Python**: Core implementation
        
        ### Features
        
        ✨ **Interactive Chat Interface**
        - Real-time responses from AI-powered support system
        - Customer context awareness
        - Personalized recommendations
        
        📊 **Response Analytics**
        - Confidence scores for each response
        - Suggested next actions
        - Conversation history tracking
        
        📦 **Batch Processing**
        - Process multiple queries efficiently
        - Bulk customer support handling
        
        ### Supported Query Types
        
        - Flight booking and modifications
        - Baggage and luggage inquiries
        - Refunds and cancellations
        - Seat selection and upgrades
        - Check-in procedures
        - Special assistance requests
        - Airline policies and procedures
        - General customer service
        
        ### How to Get Started
        
        1. **Configure Backend URL** in the sidebar (default: http://localhost:8000)
        2. **Enter Customer ID** (optional) for personalized responses
        3. **Type Your Question** in the query input area
        4. **Click Send Query** to get an AI-powered response
        5. **View History** to review previous interactions
        
        ### Architecture
        
        ```
        Streamlit UI ──(HTTP)──> FastAPI Backend ──> AI Workflow
        ```
        
        ### Tips for Best Results
        
        - Be specific and detailed in your queries
        - Include relevant information (booking ID, flight date, etc.)
        - Use the category selector to provide context
        - Check the conversation history for previous answers
        
        ---
        
        **Version:** 1.0.0  
        **Built with:** ✈️ FastAPI + Streamlit
        """)


if __name__ == "__main__":
    main()
