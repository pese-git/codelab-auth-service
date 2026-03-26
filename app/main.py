"""Main FastAPI application"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from app.core.config import logger, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting Auth Service...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Version: {settings.version}")
    
    # Startup logic
    try:
        # Load RSA keys
        from app.core.security import rsa_key_manager
        rsa_key_manager.load_keys()
        logger.info("✓ RSA keys loaded")
        
        # Initialize database
        from app.models import init_db
        await init_db()
        logger.info("✓ Database initialized")
        
        # Seed default data
        from app.core.seed import seed_default_data
        await seed_default_data()
        logger.info("✓ Default data seeded")
        
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        raise
    
    yield
    
    # Shutdown logic
    logger.info("Shutting down Auth Service...")
    from app.models import close_db
    await close_db()


# Create FastAPI application
app = FastAPI(
    title="CodeLab Auth Service",
    description="OAuth2 Authorization Server for CodeLab Platform",
    version=settings.version,
    docs_url="/docs" if settings.enable_swagger_ui else None,
    redoc_url="/redoc" if settings.enable_swagger_ui else None,
    lifespan=lifespan,
)

# Add OpenAPI security scheme for Bearer token
original_openapi = app.openapi

def custom_openapi():
    """
    Customize OpenAPI schema to include authentication.
    
    Adds security schemes for Bearer token authentication.
    Security is applied only to endpoints that require authentication.
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Bearer token (JWT access token)",
        },
    }
    
    # FastAPI will automatically apply security to endpoints that use Depends(security)
    # No need to apply security globally
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Override OpenAPI schema generator
app.openapi = custom_openapi  # type: ignore[assignment]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structured logging middleware
from app.middleware import RateLimitMiddleware, StructuredLoggingMiddleware

app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        content={
            "status": "healthy",
            "version": settings.version,
            "environment": settings.environment,
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse(
        content={
            "service": "CodeLab Auth Service",
            "version": settings.version,
            "docs": "/docs" if settings.is_development else None,
        }
    )


# Include routers
from app.api.v1 import jwks, oauth, register, password_reset, sessions

app.include_router(oauth.router, prefix="/api/v1/oauth", tags=["OAuth2"])
app.include_router(sessions.router, prefix="/api/v1/oauth/sessions", tags=["Sessions"])
app.include_router(register.router, prefix="/api/v1", tags=["Registration"])
app.include_router(password_reset.router, prefix="/api/v1", tags=["Password Reset"])
app.include_router(jwks.router, prefix="/.well-known", tags=["JWKS"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
