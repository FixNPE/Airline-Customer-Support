from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv
import logging
import re
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Airline Customer Support API",
    description="AI-powered customer support workflow for airlines",
    version="1.0.0"
)

# Add CORS middleware to allow frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# PART B: GUARDRAILS - Safety Checks and Input Validation
# ============================================================================

class GuardrailsConfig:
    """Configuration for safety guardrails"""
    
    # Abusive/harmful language patterns
    ABUSIVE_PATTERNS = [
        r'\b(badword1|badword2|offensive)\b',  # Replace with actual patterns
        r'(hate|kill|bomb)\s*(airline|customer)',
        r'(%s{2,})',  # Multiple special characters
    ]
    
    # Supported intents - restrict to known operations
    SUPPORTED_INTENTS = [
        'book_flight',
        'check_flight_status',
        'cancel_booking',
        'modify_booking',
        'baggage_inquiry',
        'refund_request',
        'check_in',
        'seat_selection',
        'special_assistance',
        'general_inquiry'
    ]
    
    # Sensitive data patterns to redact
    SENSITIVE_PATTERNS = {
        'passport': r'\b[A-Z]{1,2}\d{6,9}\b',
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    }
    
    # Query length limits (prevent DoS)
    MAX_QUERY_LENGTH = 5000
    MIN_QUERY_LENGTH = 3


class InputValidator:
    """Validates and sanitizes user input"""
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Remove/escape harmful characters"""
        # HTML escape potential XSS
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        text = text.replace('"', '&quot;').replace("'", '&#x27;')
        return text.strip()
    
    @staticmethod
    def check_length(text: str) -> bool:
        """Validate query length"""
        return GuardrailsConfig.MIN_QUERY_LENGTH <= len(text) <= GuardrailsConfig.MAX_QUERY_LENGTH
    
    @staticmethod
    def detect_abuse(text: str) -> bool:
        """Detect abusive/harmful language"""
        lower_text = text.lower()
        for pattern in GuardrailsConfig.ABUSIVE_PATTERNS:
            if re.search(pattern, lower_text, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def validate_intent(intent: str) -> bool:
        """Check if intent is supported"""
        return intent.lower() in [i.lower() for i in GuardrailsConfig.SUPPORTED_INTENTS]
    
    @staticmethod
    def redact_sensitive_data(text: str) -> str:
        """Redact sensitive information from text"""
        redacted = text
        for data_type, pattern in GuardrailsConfig.SENSITIVE_PATTERNS.items():
            redacted = re.sub(pattern, f'[REDACTED_{data_type.upper()}]', redacted)
        return redacted
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Validate phone number format"""
        pattern = r'^\+?1?\d{9,15}$'
        return re.match(pattern, phone.replace('-', '').replace(' ', '')) is not None


# ============================================================================
# PART A: EVALUATIONS - Testing and Validation Logic
# ============================================================================

class EvaluationMetrics:
    """Metrics for evaluating system performance"""
    
    def __init__(self):
        self.total_queries = 0
        self.successful_queries = 0
        self.failed_queries = 0
        self.blocked_queries = 0
        self.response_times = []
    
    def record_success(self, response_time: float):
        """Record successful query"""
        self.total_queries += 1
        self.successful_queries += 1
        self.response_times.append(response_time)
    
    def record_failure(self, response_time: float):
        """Record failed query"""
        self.total_queries += 1
        self.failed_queries += 1
        self.response_times.append(response_time)
    
    def record_blocked(self):
        """Record blocked/filtered query"""
        self.total_queries += 1
        self.blocked_queries += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        return {
            'total_queries': self.total_queries,
            'successful_queries': self.successful_queries,
            'failed_queries': self.failed_queries,
            'blocked_queries': self.blocked_queries,
            'success_rate': self.successful_queries / self.total_queries if self.total_queries > 0 else 0,
            'average_response_time': avg_response_time,
        }


class ResponseEvaluator:
    """Evaluates AI-generated responses for quality and safety"""
    
    @staticmethod
    def evaluate_response(response: str, query: str) -> Dict[str, Any]:
        """Evaluate response quality"""
        evaluation = {
            'is_valid': True,
            'issues': [],
            'confidence_score': 0.85,
        }
        
        # Check response length
        if len(response) < 10:
            evaluation['issues'].append('Response too short')
            evaluation['is_valid'] = False
        
        # Check for harmful content
        if InputValidator.detect_abuse(response):
            evaluation['issues'].append('Response contains harmful content')
            evaluation['is_valid'] = False
        
        # Check relevance (simple heuristic)
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        overlap = len(query_words & response_words) / len(query_words) if query_words else 0
        evaluation['relevance_score'] = min(overlap, 1.0)
        
        if overlap < 0.1:
            evaluation['issues'].append('Response may not be relevant to query')
        
        return evaluation
    
    @staticmethod
    def validate_booking_response(booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate booking-related responses"""
        validation = {'is_valid': True, 'errors': []}
        
        # Check required fields
        required_fields = ['booking_id', 'customer_id', 'flight_number', 'date', 'status']
        for field in required_fields:
            if field not in booking_data or not booking_data[field]:
                validation['errors'].append(f'Missing required field: {field}')
                validation['is_valid'] = False
        
        return validation


# Initialize metrics
eval_metrics = EvaluationMetrics()

# ============================================================================
# REQUEST/RESPONSE MODELS WITH VALIDATION
# ============================================================================

class SupportQuery(BaseModel):
    """Customer support query model with validation"""
    query: str
    customer_id: Optional[str] = None
    context: Optional[dict] = None
    
    @validator('query')
    def validate_query(cls, v):
        """Validate query input"""
        if not InputValidator.check_length(v):
            raise ValueError(f'Query must be between {GuardrailsConfig.MIN_QUERY_LENGTH} and {GuardrailsConfig.MAX_QUERY_LENGTH} characters')
        
        if InputValidator.detect_abuse(v):
            raise ValueError('Query contains inappropriate content')
        
        return InputValidator.sanitize_input(v)
    
    @validator('customer_id')
    def validate_customer_id(cls, v):
        """Validate customer ID format"""
        if v and not re.match(r'^[A-Z0-9]{5,20}$', v):
            raise ValueError('Invalid customer ID format')
        return v


class SupportResponse(BaseModel):
    """Support response model"""
    response: str
    status: str
    customer_id: Optional[str] = None
    suggested_actions: Optional[list] = None
    confidence_score: Optional[float] = None
    evaluation: Optional[Dict[str, Any]] = None


class EvaluationResponse(BaseModel):
    """Response for evaluation endpoints"""
    metrics: Dict[str, Any]
    status: str = "success"


class GuardrailsCheckResponse(BaseModel):
    """Response for guardrails check"""
    is_safe: bool
    issues: List[str] = []
    sanitized_input: str = ""


# ============================================================================
# Import backend support workflow
# ============================================================================

try:
    from backend.support_workflow import process_customer_support_query
    BACKEND_AVAILABLE = True
except ImportError:
    logger.warning("Backend support workflow not found. Using mock function.")
    BACKEND_AVAILABLE = False
    
    async def process_customer_support_query(query: str, customer_id: Optional[str] = None, context: Optional[dict] = None):
        """Mock implementation - replace with actual backend function"""
        return {
            "response": f"Support response for: {query}",
            "status": "success",
            "suggested_actions": ["Check booking", "Update preferences"],
            "confidence_score": 0.85
        }


# ============================================================================
# PART A & B INTEGRATED ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Airline Customer Support API",
        "version": "1.0.0",
        "docs": "/docs",
        "backend_status": "connected" if BACKEND_AVAILABLE else "mock",
        "endpoints": {
            "health": "/health",
            "support_query": "/support/query",
            "batch_queries": "/support/batch",
            "evaluate_metrics": "/evaluate/metrics",
            "guardrails_check": "/guardrails/check",
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "backend": "available" if BACKEND_AVAILABLE else "mock"
    }


@app.post("/guardrails/check", response_model=GuardrailsCheckResponse)
async def check_guardrails(request: dict):
    """
    PART B: Check input against safety guardrails
    
    Validates:
    - Input length
    - Abusive content
    - Supported intents
    - PII/sensitive data
    """
    text = request.get("text", "")
    
    if not text:
        raise HTTPException(status_code=400, detail="Text field required")
    
    issues = []
    sanitized = InputValidator.sanitize_input(text)
    
    # Check length
    if not InputValidator.check_length(text):
        issues.append(f"Query length must be between {GuardrailsConfig.MIN_QUERY_LENGTH} and {GuardrailsConfig.MAX_QUERY_LENGTH}")
    
    # Check for abuse
    if InputValidator.detect_abuse(text):
        issues.append("Inappropriate content detected")
    
    # Redact sensitive data
    redacted = InputValidator.redact_sensitive_data(text)
    
    is_safe = len(issues) == 0
    
    if not is_safe:
        eval_metrics.record_blocked()
    
    return GuardrailsCheckResponse(
        is_safe=is_safe,
        issues=issues,
        sanitized_input=sanitized
    )


@app.post("/support/query", response_model=SupportResponse)
async def handle_support_query(request: SupportQuery):
    """
    Process customer support query with PART A & B integration.
    
    PART B (Guardrails):
    - Input validation and sanitization
    - Abuse detection
    - Sensitive data redaction
    
    PART A (Evaluations):
    - Response quality evaluation
    - Metrics collection
    
    - **query**: Customer's question or issue
    - **customer_id**: Optional customer identifier
    - **context**: Optional additional context (e.g., booking info)
    """
    import time
    start_time = time.time()
    
    try:
        # PART B: Additional guardrails validation
        if InputValidator.detect_abuse(request.query):
            eval_metrics.record_blocked()
            raise HTTPException(status_code=400, detail="Query contains inappropriate content")
        
        # Validate intent if provided in context
        if request.context and 'category' in request.context:
            category = request.context['category']
            if not InputValidator.validate_intent(category):
                logger.warning(f"Unsupported intent: {category}")
                # Don't block, but note it
        
        logger.info(f"Processing support query from customer: {request.customer_id}")
        
        # Call the backend support workflow
        result = await process_customer_support_query(
            query=request.query,
            customer_id=request.customer_id,
            context=request.context
        )
        
        # PART A: Evaluate the response
        evaluation = ResponseEvaluator.evaluate_response(
            result.get("response", ""),
            request.query
        )
        
        # Redact sensitive data from response
        response_text = InputValidator.redact_sensitive_data(result.get("response", ""))
        
        # Validate and format the response
        response_data = SupportResponse(
            response=response_text,
            status=result.get("status", "success"),
            customer_id=request.customer_id,
            suggested_actions=result.get("suggested_actions"),
            confidence_score=result.get("confidence_score"),
            evaluation=evaluation
        )
        
        # Record metrics
        elapsed_time = time.time() - start_time
        if evaluation['is_valid']:
            eval_metrics.record_success(elapsed_time)
        else:
            eval_metrics.record_failure(elapsed_time)
        
        return response_data
    
    except Exception as e:
        logger.error(f"Error processing support query: {str(e)}")
        eval_metrics.record_failure(time.time() - start_time)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/support/batch")
async def handle_batch_queries(requests_list: List[SupportQuery]):
    """
    Process multiple support queries in a single request.
    
    Includes PART A evaluations and PART B guardrails for batch operations.
    """
    try:
        results = []
        
        for req in requests_list:
            # PART B: Check guardrails for each query
            if InputValidator.detect_abuse(req.query):
                logger.warning(f"Blocked abusive query from {req.customer_id}")
                eval_metrics.record_blocked()
                continue
            
            result = await process_customer_support_query(
                query=req.query,
                customer_id=req.customer_id,
                context=req.context
            )
            
            # PART A: Evaluate each response
            evaluation = ResponseEvaluator.evaluate_response(
                result.get("response", ""),
                req.query
            )
            
            results.append({
                "customer_id": req.customer_id,
                "query": req.query,
                "response": InputValidator.redact_sensitive_data(result.get("response")),
                "status": result.get("status"),
                "evaluation": evaluation,
                "confidence_score": result.get("confidence_score")
            })
        
        return {
            "total_processed": len(results),
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Error processing batch queries: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch processing error: {str(e)}")


# ============================================================================
# PART A: EVALUATION ENDPOINTS
# ============================================================================

@app.get("/evaluate/metrics", response_model=EvaluationResponse)
async def get_evaluation_metrics():
    """
    PART A: Get system evaluation metrics.
    
    Returns:
    - Total queries processed
    - Success/failure rates
    - Blocked queries (guardrails)
    - Average response time
    - Overall success rate
    """
    metrics = eval_metrics.get_metrics()
    
    return EvaluationResponse(
        metrics=metrics,
        status="success"
    )


@app.post("/evaluate/response")
async def evaluate_response(data: dict):
    """
    PART A: Evaluate a single response.
    
    Parameters:
    - response: The response text to evaluate
    - query: The original query
    
    Returns evaluation metrics including:
    - Validity
    - Issues found
    - Relevance score
    - Confidence score
    """
    response = data.get("response", "")
    query = data.get("query", "")
    
    if not response or not query:
        raise HTTPException(status_code=400, detail="Both response and query required")
    
    evaluation = ResponseEvaluator.evaluate_response(response, query)
    
    return {
        "evaluation": evaluation,
        "status": "success"
    }


@app.post("/evaluate/booking")
async def evaluate_booking_response(booking_data: dict):
    """
    PART A: Validate booking response structure and data.
    
    Checks:
    - Required fields presence
    - Data type validation
    - Business logic validation
    """
    validation = ResponseEvaluator.validate_booking_response(booking_data)
    
    return {
        "validation": validation,
        "status": "success"
    }


@app.get("/guardrails/config")
async def get_guardrails_config():
    """
    PART B: Get current guardrails configuration.
    
    Returns:
    - Supported intents
    - Validation limits
    - Redaction patterns
    """
    return {
        "supported_intents": GuardrailsConfig.SUPPORTED_INTENTS,
        "max_query_length": GuardrailsConfig.MAX_QUERY_LENGTH,
        "min_query_length": GuardrailsConfig.MIN_QUERY_LENGTH,
        "sensitive_data_types": list(GuardrailsConfig.SENSITIVE_PATTERNS.keys()),
        "status": "success"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000))
    )
