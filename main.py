from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv
import logging

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

# Request/Response Models
class SupportQuery(BaseModel):
    """Customer support query model"""
    query: str
    customer_id: Optional[str] = None
    context: Optional[dict] = None

class SupportResponse(BaseModel):
    """Support response model"""
    response: str
    status: str
    customer_id: Optional[str] = None
    suggested_actions: Optional[list] = None
    confidence_score: Optional[float] = None

# Import your backend function (update the import path accordingly)
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
            "suggested_actions": ["Check booking", "Update preferences"]
        }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Airline Customer Support API",
        "version": "1.0.0",
        "docs": "/docs",
        "backend_status": "connected" if BACKEND_AVAILABLE else "mock"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "backend": "available" if BACKEND_AVAILABLE else "mock"
    }

@app.post("/support/query", response_model=SupportResponse)
async def handle_support_query(request: SupportQuery):
    """
    Process customer support query through the AI workflow.
    
    - **query**: Customer's question or issue
    - **customer_id**: Optional customer identifier
    - **context**: Optional additional context (e.g., booking info)
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        logger.info(f"Processing support query from customer: {request.customer_id}")
        
        # Call the backend support workflow
        result = await process_customer_support_query(
            query=request.query,
            customer_id=request.customer_id,
            context=request.context
        )
        
        # Validate and format the response
        return SupportResponse(
            response=result.get("response", ""),
            status=result.get("status", "success"),
            customer_id=request.customer_id,
            suggested_actions=result.get("suggested_actions"),
            confidence_score=result.get("confidence_score")
        )
    
    except Exception as e:
        logger.error(f"Error processing support query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/support/batch")
async def handle_batch_queries(requests_list: list[SupportQuery]):
    """
    Process multiple support queries in a single request.
    """
    try:
        results = []
        for req in requests_list:
            result = await process_customer_support_query(
                query=req.query,
                customer_id=req.customer_id,
                context=req.context
            )
            results.append({
                "customer_id": req.customer_id,
                "query": req.query,
                "response": result.get("response"),
                "status": result.get("status")
            })
        
        return {
            "total_processed": len(results),
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Error processing batch queries: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch processing error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000))
    )
