"""
ModelAdvisor Backend - FastAPI Application

An intelligent AI model recommendation system that understands user queries,
extracts constraints, and recommends the best-fit AI models.
"""
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models.schemas import (
    AdvisorQuery, AdvisorResponse, FollowUpQuery, Constraints,
    SystemDesignQuery, SystemDesignResponse, CodeSample
)
from agents import ConstraintExtractor, Planner, SystemDesignExpert
from logger import logger
from metrics import metrics


# Session storage (in-memory, replace with Redis for production)
sessions: Dict[str, Dict] = {}


def cleanup_old_sessions():
    """Remove sessions older than 24 hours."""
    cutoff = datetime.now() - timedelta(hours=24)
    expired = [
        sid for sid, data in sessions.items() 
        if data.get("created_at", datetime.now()) < cutoff
    ]
    for sid in expired:
        del sessions[sid]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.log_agent_step("system", "startup", success=True)
    print("🚀 ModelAdvisor API starting...")
    yield
    # Shutdown
    logger.log_agent_step("system", "shutdown", success=True)
    print("👋 ModelAdvisor API shutting down...")
    sessions.clear()


app = FastAPI(
    title="ModelAdvisor API",
    description="Intelligent AI model recommendation system",
    version="1.0.0",
    lifespan=lifespan
)


# Logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all HTTP requests with timing."""
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]
    
    # Process request
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Log request
        logger.log_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id
        )
        
        # Record metrics
        metrics.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        return response
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.log_request(
            method=request.method,
            path=request.url.path,
            status_code=500,
            duration_ms=duration_ms,
            request_id=request_id,
            error=str(e)
        )
        metrics.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=500,
            duration_ms=duration_ms
        )
        raise


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents
constraint_extractor = ConstraintExtractor()
planner = Planner()
system_design_expert = SystemDesignExpert()


class HealthResponse(BaseModel):
    status: str
    version: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="1.0.0")


@app.post("/api/advisor", response_model=AdvisorResponse)
async def get_recommendation(query: AdvisorQuery):
    """
    Get AI model recommendation based on natural language query.
    
    - Extracts constraints from the query
    - Searches for matching models
    - Returns comprehensive recommendation with trade-offs and code
    """
    try:
        # Generate or use existing session ID
        session_id = query.session_id or str(uuid.uuid4())
        
        # Extract constraints from query
        constraints = await constraint_extractor.extract(query.query)
        
        # Execute recommendation workflow
        response = await planner.execute(constraints, session_id)
        
        # Store session for follow-up queries
        sessions[session_id] = {
            "created_at": datetime.now(),
            "constraints": constraints.model_dump(),
            "last_response": response.model_dump(),
            "query_history": [query.query]
        }
        
        # Cleanup old sessions periodically
        if len(sessions) > 100:
            cleanup_old_sessions()
        
        return response
        
    except Exception as e:
        print(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/advisor/followup", response_model=AdvisorResponse)
async def followup_query(query: FollowUpQuery):
    """
    Handle follow-up query with session context.
    
    Examples: "make it smaller", "what about mobile?", "cheaper option?"
    """
    try:
        # Get existing session
        session = sessions.get(query.session_id)
        if not session:
            raise HTTPException(
                status_code=404, 
                detail="Session not found. Please start a new query."
            )
        
        # Get previous constraints
        prev_constraints = Constraints(**session["constraints"])
        
        # Refine constraints based on follow-up
        refined_constraints = await constraint_extractor.refine(
            prev_constraints, 
            query.query
        )
        
        # Execute with refined constraints
        response = await planner.execute(refined_constraints, query.session_id)
        
        # Update session
        session["constraints"] = refined_constraints.model_dump()
        session["last_response"] = response.model_dump()
        session["query_history"].append(query.query)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing follow-up: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session information including query history."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "created_at": session["created_at"].isoformat(),
        "query_count": len(session.get("query_history", [])),
        "constraints": session.get("constraints", {}),
    }


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


# ============ System Design Expert Endpoints ============

@app.post("/api/advisor/system-design", response_model=SystemDesignResponse)
async def ask_system_design_expert(query: SystemDesignQuery):
    """
    Ask the ML system design expert a question.
    
    Requires an active session with a model recommendation.
    Examples: "How to deploy on Modal?", "Best vector DB for my use case?"
    """
    try:
        session = sessions.get(query.session_id)
        if not session:
            raise HTTPException(
                status_code=404, 
                detail="Session not found. Get a recommendation first."
            )
        
        # Build context from session
        context = {
            "constraints": session["constraints"],
            "best_match": session["last_response"].get("best_match", {}),
            "hardware_specs": query.hardware_specs
        }
        
        # Get response from expert
        response_dict = await system_design_expert.answer(query.question, context)
        
        # Track in session history
        session.setdefault("expert_history", []).append({
            "question": query.question,
            "answer": response_dict.get("answer", "")
        })
        
        # Convert code samples to proper format
        code_samples = []
        for sample in response_dict.get("code_samples", []):
            code_samples.append(CodeSample(
                language=sample.get("language", "text"),
                code=sample.get("code", ""),
                filename=sample.get("filename"),
                description=sample.get("description", "")
            ))
        
        return SystemDesignResponse(
            answer=response_dict.get("answer", ""),
            code_samples=code_samples,
            tradeoffs=response_dict.get("tradeoffs", []),
            alternatives=response_dict.get("alternatives", []),
            resources=response_dict.get("resources", []),
            suggested_followups=response_dict.get("suggested_followups", []),
            context_summary=response_dict.get("context_summary", "")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in system design expert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/advisor/system-design/suggestions")
async def get_expert_suggestions(session_id: str):
    """
    Get suggested questions for the system design expert based on session context.
    """
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    context = {
        "constraints": session["constraints"],
        "best_match": session["last_response"].get("best_match", {})
    }
    
    suggestions = await system_design_expert.suggest_questions(context)
    
    return {
        "session_id": session_id,
        "suggestions": suggestions
    }


# ============ Logging and Metrics Endpoints ============

@app.get("/api/metrics")
async def get_metrics_endpoint():
    """Get current application metrics."""
    return metrics.get_metrics()


@app.get("/api/logs")
async def get_logs_endpoint(
    count: int = Query(default=100, le=500, description="Number of logs to retrieve"),
    level: Optional[str] = Query(default=None, description="Filter by log level"),
    category: Optional[str] = Query(default=None, description="Filter by category (request, llm, agent, tool)")
):
    """Get recent application logs."""
    return {
        "logs": logger.get_recent_logs(count=count, level=level, category=category),
        "count": count,
        "filters": {"level": level, "category": category}
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

