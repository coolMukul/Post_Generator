"""Shared Pydantic models and enums for the worker and API layers."""
from enum import Enum
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job lifecycle states."""
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class SearchMode(str, Enum):
    """Search strategy modes."""
    HYBRID = "hybrid"
    VECTOR = "vector"
    KEYWORD = "keyword"


class SearchRequest(BaseModel):
    """Incoming search job payload."""
    query: str = Field(..., min_length=1, description="Search query text")
    search_mode: SearchMode = Field(default=SearchMode.HYBRID)
    limit: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    vector_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    document_id: Optional[str] = None


class SearchResult(BaseModel):
    """Single search result returned to the UI."""
    id: str
    documentId: str
    documentTitle: Optional[str] = None
    chunkIndex: int
    content: str
    contextSummary: Optional[str] = None
    score: float
    rankSource: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Full response payload stored as the job result."""
    success: bool
    query: str
    searchMode: str
    resultsCount: int
    results: List[SearchResult]


class JobRecord(BaseModel):
    """Stored state of a background job."""
    job_id: str
    job_type: str
    status: JobStatus
    data: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
