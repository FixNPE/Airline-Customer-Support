from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv
import logging
import re
import json
import asyncio
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Airline Customer Support API - PART A & B",
    description="AI-powered airline support with LangChain, RAG, SQL, and Guardrails",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# PART A: CORE AIRLINE SUPPORT PIPELINE
# ============================================================================

# Import configuration and credentials
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "airline-policies")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")

# Database connection configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "airline_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "")
}


# ============================================================================
# PART A: INTENT CLASSIFICATION
# ============================================================================

class IntentClassifier:
    """Classify user queries into supported intent categories"""
    
    # Intent mappings with example keywords
    INTENT_MAPPINGS = {
        "flight_status": {
            "keywords": ["flight status", "where is", "on time", "delayed", "track"],
            "description": "Query about flight status, delay, or location",
            "requires_sql": True,
            "requires_rag": False
        },
        "booking_management": {
            "keywords": ["book", "booking", "reservation", "modify", "cancel", "change"],
            "description": "Booking-related queries and modifications",
            "requires_sql": True,
            "requires_rag": True
        },
        "baggage_inquiry": {
            "keywords": ["baggage", "luggage", "bag", "carry-on", "checked bag", "allowance"],
            "description": "Baggage policy and inquiries",
            "requires_sql": False,
            "requires_rag": True
        },
        "refund_cancellation": {
            "keywords": ["refund", "cancellation", "refund policy", "cancel flight", "money back"],
            "description": "Refund and cancellation policies",
            "requires_sql": False,
            "requires_rag": True
        },
        "check_in": {
            "keywords": ["check-in", "check in", "online check-in", "boarding", "gate"],
            "description": "Check-in procedures and boarding",
            "requires_sql": False,
            "requires_rag": True
        },
        "special_assistance": {
            "keywords": ["wheelchair", "assistance", "unaccompanied minor", "pregnant", "medical"],
            "description": "Special assistance requests",
            "requires_sql": False,
            "requires_rag": True
        },
        "fares_pricing": {
            "keywords": ["price", "fare", "cost", "charge", "fare rules", "ticket price"],
            "description": "Pricing and fare inquiries",
            "requires_sql": True,
            "requires_rag": True
        },
        "general_inquiry": {
            "keywords": ["hello", "hi", "help", "information", "general"],
            "description": "General questions and information",
            "requires_sql": False,
            "requires_rag": True
        }
    }
    
    @staticmethod
    def classify(query: str) -> Dict[str, Any]:
        """
        Classify user query into an intent category
        
        Returns:
            {
                "intent": str,
                "confidence": float (0-1),
                "requires_sql": bool,
                "requires_rag": bool,
                "description": str
            }
        """
        query_lower = query.lower()
        scores = {}
        
        # Calculate intent scores based on keyword matching
        for intent, config in IntentClassifier.INTENT_MAPPINGS.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in query_lower:
                    score += 1
            scores[intent] = score
        
        # Find best matching intent
        best_intent = max(scores, key=scores.get) if max(scores.values()) > 0 else "general_inquiry"
        confidence = scores[best_intent] / max(len(query.split()), 1)
        
        config = IntentClassifier.INTENT_MAPPINGS[best_intent]
        
        return {
            "intent": best_intent,
            "confidence": min(confidence, 1.0),
            "requires_sql": config["requires_sql"],
            "requires_rag": config["requires_rag"],
            "description": config["description"]
        }


# ============================================================================
# PART A: SQL PIPELINE - PostgreSQL Query Generation & Execution
# ============================================================================

class SQLQueryGenerator:
    """Generate SQL queries from natural language"""
    
    # SQL query templates for common flight queries
    QUERY_TEMPLATES = {
        "flight_status": """
            SELECT flight_id, flight_number, departure, arrival, departure_time, 
                   arrival_time, status, aircraft
            FROM flights
            WHERE flight_number = %s OR departure ILIKE %s OR arrival ILIKE %s
            ORDER BY departure_time DESC
            LIMIT 5
        """,
        
        "passenger_booking": """
            SELECT booking_id, passenger_name, flight_number, booking_date, 
                   booking_status, seat_assignment, price
            FROM bookings
            WHERE passenger_id = %s OR booking_id = %s
            ORDER BY booking_date DESC
            LIMIT 10
        """,
        
        "available_flights": """
            SELECT flight_id, flight_number, departure_time, arrival_time, 
                   available_seats, aircraft_type, price
            FROM flights
            WHERE departure = %s AND arrival = %s AND departure_date = %s
                   AND status = 'scheduled'
            ORDER BY departure_time
            LIMIT 20
        """,
        
        "fare_pricing": """
            SELECT flight_number, fare_type, base_price, taxes, total_price, 
                   availability, restrictions
            FROM fare_rules
            WHERE flight_number = %s OR route = %s
            ORDER BY total_price
            LIMIT 10
        """,
        
        "delay_history": """
            SELECT flight_number, scheduled_departure, actual_departure, 
                   delay_minutes, delay_reason
            FROM flight_history
            WHERE flight_number = %s
            ORDER BY scheduled_departure DESC
            LIMIT 5
        """
    }
    
    @staticmethod
    def generate_sql(intent: str, entities: Dict[str, Any]) -> Optional[str]:
        """
        Generate SQL query based on intent and extracted entities
        
        Args:
            intent: Classified intent
            entities: Extracted entities (flight_number, passenger_id, etc.)
        
        Returns:
            SQL query string or None
        """
        if intent not in SQLQueryGenerator.QUERY_TEMPLATES:
            return None
        
        return SQLQueryGenerator.QUERY_TEMPLATES[intent]


class SQLPipeline:
    """Execute SQL queries against PostgreSQL database"""
    
    @staticmethod
    async def execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results
        
        Note: In production, use connection pooling (psycopg2-pool, asyncpg)
        """
        try:
            # Placeholder for actual database connection
            # In production, use: import psycopg2 or asyncpg
            logger.info(f"Executing SQL query: {query[:100]}...")
            
            # Mock result for demonstration
            return [
                {
                    "flight_number": "AA123",
                    "departure": "NYC",
                    "arrival": "LAX",
                    "departure_time": "2026-06-15 10:00:00",
                    "status": "on-time"
                }
            ]
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            raise


# ============================================================================
# PART A: RAG PIPELINE - Pinecone Vector Database
# ============================================================================

class PineconeRAG:
    """Retrieve Augmented Generation using Pinecone"""
    
    def __init__(self):
        self.index_name = PINECONE_INDEX
        self.api_key = PINECONE_API_KEY
        # In production: import pinecone; self.index = pinecone.Index(self.index_name)
    
    @staticmethod
    async def embed_text(text: str) -> List[float]:
        """
        Convert text to embeddings using Grok API or OpenAI
        
        Returns:
            Vector embedding (768 dimensions for typical models)
        """
        try:
            # Placeholder for embedding generation
            # In production, use: from sentence_transformers import SentenceTransformer
            # or call Grok/OpenAI embedding API
            logger.info(f"Generating embedding for: {text[:50]}...")
            
            # Mock embedding (768-dim vector)
            return [0.1] * 768
        except Exception as e:
            logger.error(f"Embedding error: {str(e)}")
            raise
    
    async def query_policies(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant airline policies from Pinecone
        
        Returns:
            List of relevant policy documents with similarity scores
        """
        try:
            # Generate embedding for query
            query_embedding = await PineconeRAG.embed_text(query)
            
            # In production: results = self.index.query(query_embedding, top_k=top_k)
            
            logger.info(f"Retrieved {top_k} policy documents for: {query}")
            
            # Mock results
            return [
                {
                    "id": f"policy_{i}",
                    "content": f"Airline policy document {i}",
                    "similarity_score": 0.95 - (i * 0.05),
                    "category": "baggage",
                    "source": "airline_kb"
                }
                for i in range(top_k)
            ]
        except Exception as e:
            logger.error(f"RAG query error: {str(e)}")
            raise


# ============================================================================
# PART A: ENTITY EXTRACTION
# ============================================================================

class EntityExtractor:
    """Extract key entities from user queries"""
    
    ENTITY_PATTERNS = {
        "flight_number": r"[A-Z]{2}\d{3,4}",  # e.g., AA123, UA4567
        "passenger_id": r"[A-Z0-9]{6,10}",     # e.g., CUST123, BK12345
        "date": r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}",  # YYYY-MM-DD or MM/DD/YYYY
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\+?1?\d{9,15}",
        "city": r"\b(New York|Los Angeles|Chicago|Miami|Boston|LAX|NYC|JFK|ORD)\b"
    }
    
    @staticmethod
    def extract_entities(query: str) -> Dict[str, List[str]]:
        """
        Extract entities from query using regex patterns
        
        Returns:
            Dictionary mapping entity types to found values
        """
        entities = {}
        
        for entity_type, pattern in EntityExtractor.ENTITY_PATTERNS.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches
        
        return entities


# ============================================================================
# PART A: ORCHESTRATION ENGINE (LangGraph-like workflow)
# ============================================================================

class SupportWorkflowOrchestrator:
    """Orchestrate the complete support workflow"""
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.sql_generator = SQLQueryGenerator()
        self.sql_pipeline = SQLPipeline()
        self.rag_pipeline = PineconeRAG()
    
    async def process_query(self, user_query: str, customer_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete workflow:
        1. Classify intent
        2. Extract entities
        3. Parallel execution: SQL queries (if needed) + RAG retrieval (if needed)
        4. Synthesize response
        """
        
        logger.info(f"Processing query: {user_query}")
        
        # Step 1: Intent Classification
        intent_result = self.intent_classifier.classify(user_query)
        logger.info(f"Intent: {intent_result['intent']} (confidence: {intent_result['confidence']})")
        
        # Step 2: Entity Extraction
        entities = self.entity_extractor.extract_entities(user_query)
        logger.info(f"Extracted entities: {entities}")
        
        # Step 3: Parallel Processing
        sql_results = None
        rag_results = None
        
        if intent_result["requires_sql"]:
            sql_query = self.sql_generator.generate_sql(intent_result["intent"], entities)
            if sql_query:
                try:
                    sql_results = await self.sql_pipeline.execute_query(sql_query)
                except Exception as e:
                    logger.error(f"SQL execution failed: {str(e)}")
        
        if intent_result["requires_rag"]:
            try:
                rag_results = await self.rag_pipeline.query_policies(user_query)
            except Exception as e:
                logger.error(f"RAG retrieval failed: {str(e)}")
        
        # Step 4: Synthesize Response
        response = self.synthesize_response(
            user_query,
            intent_result,
            entities,
            sql_results,
            rag_results
        )
        
        return response
    
    def synthesize_response(
        self,
        query: str,
        intent: Dict[str, Any],
        entities: Dict[str, Any],
        sql_data: Optional[List[Dict]] = None,
        rag_data: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Synthesize final response from all pipeline outputs
        """
        
        response_text = f"I found information about {intent['description'].lower()}.\n\n"
        
        # Add SQL-retrieved flight data
        if sql_data:
            response_text += "**Flight Information:**\n"
            for item in sql_data[:3]:  # Show top 3 results
                response_text += f"- Flight: {item.get('flight_number', 'N/A')} "
                response_text += f"from {item.get('departure', 'N/A')} to {item.get('arrival', 'N/A')}\n"
        
        # Add RAG-retrieved policies
        if rag_data:
            response_text += "\n**Relevant Policies:**\n"
            for item in rag_data[:2]:  # Show top 2 policies
                response_text += f"- {item.get('content', 'Policy information')}\n"
        
        return {
            "response": response_text,
            "intent": intent["intent"],
            "intent_confidence": intent["confidence"],
            "entities": entities,
            "status": "success",
            "sql_results_count": len(sql_data) if sql_data else 0,
            "rag_results_count": len(rag_data) if rag_data else 0,
            "timestamp": datetime.now().isoformat()
        }


# Initialize orchestrator
orchestrator = SupportWorkflowOrchestrator()


# ============================================================================
# PART B: GUARDRAILS (Integrated from previous implementation)
# ============================================================================

class GuardrailsConfig:
    """Configuration for safety guardrails"""
    
    ABUSIVE_PATTERNS = [
        r'\b(badword1|badword2|offensive)\b',
        r'(hate|kill|bomb)\s*(airline|customer)',
        r'(%s{2,})',
    ]
    
    SUPPORTED_INTENTS = [
        'flight_status', 'booking_management', 'baggage_inquiry',
        'refund_cancellation', 'check_in', 'special_assistance',
        'fares_pricing', 'general_inquiry'
    ]
    
    SENSITIVE_PATTERNS = {
        'passport': r'\b[A-Z]{1,2}\d{6,9}\b',
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    }
    
    MAX_QUERY_LENGTH = 5000
    MIN_QUERY_LENGTH = 3


class InputValidator:
    """Validates and sanitizes user input"""
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Remove/escape harmful characters"""
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        text = text.replace('"', '&quot;').replace("'", '&#x27;')
        return text.strip()
    
    @staticmethod
    def detect_abuse(text: str) -> bool:
        """Detect abusive/harmful language"""
        lower_text = text.lower()
        for pattern in GuardrailsConfig.ABUSIVE_PATTERNS:
            if re.search(pattern, lower_text, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def redact_sensitive_data(text: str) -> str:
        """Redact sensitive information from text"""
        redacted = text
        for data_type, pattern in GuardrailsConfig.SENSITIVE_PATTERNS.items():
            redacted = re.sub(pattern, f'[REDACTED_{data_type.upper()}]', redacted)
        return redacted


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AirlineSupportQuery(BaseModel):
    """Customer support query with validation"""
    query: str
    customer_id: Optional[str] = None
    context: Optional[dict] = None
    
    @validator('query')
    def validate_query(cls, v):
        """Validate query input"""
        if not (GuardrailsConfig.MIN_QUERY_LENGTH <= len(v) <= GuardrailsConfig.MAX_QUERY_LENGTH):
            raise ValueError(f'Query must be between {GuardrailsConfig.MIN_QUERY_LENGTH} and {GuardrailsConfig.MAX_QUERY_LENGTH} characters')
        
        if InputValidator.detect_abuse(v):
            raise ValueError('Query contains inappropriate content')
        
        return InputValidator.sanitize_input(v)


class AirlineSupportResponse(BaseModel):
    """Support response model"""
    response: str
    intent: str
    intent_confidence: float
    entities: Dict[str, Any]
    status: str
    sql_results_count: int
    rag_results_count: int
    timestamp: str


# ============================================================================
# PART A & B INTEGRATED ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Airline Customer Support API - PART A & B",
        "version": "2.0.0",
        "features": {
            "part_a": [
                "Intent Classification (LangChain-like)",
                "SQL Pipeline (PostgreSQL flight data)",
                "RAG Pipeline (Pinecone vector DB)",
                "Entity Extraction",
                "Workflow Orchestration"
            ],
            "part_b": [
                "Input Validation & Sanitization",
                "Abuse Detection",
                "Sensitive Data Redaction",
                "Intent Guardrails"
            ]
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/support/query", response_model=AirlineSupportResponse)
async def handle_airline_support_query(request: AirlineSupportQuery):
    """
    PART A & B: Complete Airline Support Query Processing
    
    Workflow:
    1. Input Validation (PART B)
    2. Intent Classification (PART A)
    3. Entity Extraction (PART A)
    4. SQL Pipeline Execution (PART A)
    5. RAG Retrieval (PART A)
    6. Response Synthesis (PART A)
    """
    try:
        # PART B: Additional safety checks
        if InputValidator.detect_abuse(request.query):
            raise HTTPException(status_code=400, detail="Query contains inappropriate content")
        
        # PART A: Process through orchestrator
        result = await orchestrator.process_query(
            user_query=request.query,
            customer_id=request.customer_id
        )
        
        # Redact sensitive data from response
        result["response"] = InputValidator.redact_sensitive_data(result["response"])
        
        return AirlineSupportResponse(**result)
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/support/batch")
async def handle_batch_queries(requests_list: List[AirlineSupportQuery]):
    """Process multiple queries in batch"""
    try:
        results = []
        
        for req in requests_list:
            if InputValidator.detect_abuse(req.query):
                logger.warning(f"Blocked abusive query from {req.customer_id}")
                continue
            
            result = await orchestrator.process_query(req.query, req.customer_id)
            result["response"] = InputValidator.redact_sensitive_data(result["response"])
            results.append(result)
        
        return {
            "total_processed": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Batch processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch processing error: {str(e)}")


@app.get("/intents")
async def get_supported_intents():
    """Get all supported intents"""
    intents = []
    for intent_key, config in IntentClassifier.INTENT_MAPPINGS.items():
        intents.append({
            "intent": intent_key,
            "description": config["description"],
            "keywords": config["keywords"],
            "requires_sql": config["requires_sql"],
            "requires_rag": config["requires_rag"]
        })
    
    return {"intents": intents}


@app.post("/classify-intent")
async def classify_intent(data: dict):
    """Classify intent for a given query"""
    query = data.get("query", "")
    
    if not query:
        raise HTTPException(status_code=400, detail="Query field required")
    
    result = IntentClassifier.classify(query)
    
    return {
        "query": query,
        "classification": result,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/extract-entities")
async def extract_entities(data: dict):
    """Extract entities from a query"""
    query = data.get("query", "")
    
    if not query:
        raise HTTPException(status_code=400, detail="Query field required")
    
    entities = EntityExtractor.extract_entities(query)
    
    return {
        "query": query,
        "entities": entities,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000))
    )
