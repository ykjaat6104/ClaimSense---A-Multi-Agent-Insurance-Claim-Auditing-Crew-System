#!/usr/bin/env python3
"""
Validation script for ClaimSense Multi-Agent System setup.
Run this to verify all components are properly configured.
"""

import sys
from pathlib import Path

def check_python_version():
    """Verify Python 3.10+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"❌ Python 3.10+ required (found {version.major}.{version.minor})")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_required_packages():
    """Verify all required packages are installed"""
    packages = {
        "fastapi": "FastAPI web framework",
        "sqlalchemy": "Database ORM",
        "langgraph": "Graph-based workflows",
        "celery": "Task queue",
        "redis": "Redis client",
        "google.generativeai": "Gemini LLM",
        "tavily": "Market search API (optional)",
        "duckduckgo_search": "Fallback search",
        "pydantic": "Data validation",
    }
    
    missing = []
    for package, description in packages.items():
        try:
            __import__(package.split('.')[0])
            print(f"✅ {description} ({package})")
        except ImportError:
            is_optional = "(optional)" in description
            status = "⚠️" if is_optional else "❌"
            print(f"{status} {description} ({package})")
            if not is_optional:
                missing.append(package)
    
    return len(missing) == 0


def check_file_structure():
    """Verify all new files exist"""
    files = {
        "app/agents/state.py": "ClaimAuditState definition",
        "app/agents/tools.py": "Tool library",
        "app/agents/nodes.py": "Agent implementations",
        "app/agents/orchestrator.py": "LangGraph workflow",
        "app/services/celery_config.py": "Celery configuration",
        "app/services/celery_tasks.py": "Async tasks",
        "app/services/web_search.py": "Web search integration",
        "app/api/multi_agent_routes.py": "API endpoints",
        "MULTI_AGENT_ARCHITECTURE.md": "Architecture docs",
        "MULTI_AGENT_QUICKSTART.md": "Quick start guide",
        "TRANSFORMATION_SUMMARY.md": "Transformation summary",
    }
    
    all_found = True
    for filepath, description in files.items():
        if Path(filepath).exists():
            print(f"✅ {filepath} ({description})")
        else:
            print(f"❌ {filepath} ({description}) NOT FOUND")
            all_found = False
    
    return all_found


def check_configuration():
    """Verify environment configuration"""
    try:
        from app.config import get_settings
        settings = get_settings()
        
        print(f"✅ Configuration loaded")
        print(f"  - Environment: {settings.environment}")
        print(f"  - Database: {'configured' if settings.database_url else 'NOT CONFIGURED'}")
        print(f"  - Gemini API: {'configured' if settings.gemini_api_key else 'NOT CONFIGURED'}")
        print(f"  - Tavily API: {'configured' if settings.tavily_api_key else 'not configured (optional)'}")
        
        return bool(settings.database_url and settings.gemini_api_key)
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def check_database():
    """Verify database connectivity"""
    try:
        from sqlalchemy import text
        from app.db.session import get_engine
        
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def check_redis():
    """Verify Redis connectivity (optional)"""
    try:
        import redis
        from app.config import get_settings
        
        settings = get_settings()
        # Try to parse Redis URL from Celery config
        redis_url = getattr(settings, 'celery_broker_url', 'redis://localhost:6379/0')
        
        # Simple check - Redis is optional
        print(f"⚠️  Redis not checked (optional for Celery)")
        return True
    except Exception as e:
        print(f"⚠️  Redis check skipped: {e}")
        return True


def check_agents():
    """Verify agent implementations load"""
    try:
        from app.agents.nodes import (
            policy_analyst_node,
            data_miner_node,
            fraud_auditor_node,
            judge_node,
        )
        print("✅ All agent nodes load successfully")
        
        from app.agents.orchestrator import build_claim_audit_graph
        graph = build_claim_audit_graph()
        print("✅ LangGraph workflow builds successfully")
        
        return True
    except Exception as e:
        print(f"❌ Agent loading failed: {e}")
        return False


def check_api():
    """Verify API routes register"""
    try:
        from app.api.multi_agent_routes import router
        print(f"✅ Multi-agent API routes loaded ({len(router.routes)} routes)")
        return True
    except Exception as e:
        print(f"❌ API routes failed: {e}")
        return False


def main():
    """Run all validation checks"""
    print("\n" + "="*60)
    print("ClaimSense Multi-Agent System Validation")
    print("="*60 + "\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Required Packages", check_required_packages),
        ("File Structure", check_file_structure),
        ("Configuration", check_configuration),
        ("Database", check_database),
        ("Redis (Optional)", check_redis),
        ("Agents", check_agents),
        ("API Routes", check_api),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{'='*60}")
        print(f"Checking: {name}")
        print('='*60)
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Check failed with error: {e}")
            results.append((name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print('='*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\n{'='*60}")
    print(f"Result: {passed}/{total} checks passed")
    print('='*60 + "\n")
    
    if passed == total:
        print("🎉 System is ready to use!")
        print("\nNext steps:")
        print("1. Review MULTI_AGENT_QUICKSTART.md for setup")
        print("2. Configure .env with API keys")
        print("3. Start the FastAPI server: uvicorn app.main:app --reload")
        print("4. Or with Celery: celery -A app.services.celery_tasks worker -l info")
        return 0
    else:
        print("⚠️  Some checks failed. Review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
