# Contributing Guide

Thank you for your interest in contributing to the RAG Application! This document provides guidelines and procedures for contributing to the project.

## Code of Conduct

- Be respectful and professional
- Follow project conventions
- Test your changes before submitting
- Provide clear commit messages and descriptions

## Getting Started

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd ragapplication

# Run setup script
./setup.sh          # Linux/macOS
# or
setup.bat           # Windows

# Or manually:
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

## Development Standards

### Code Style

- **Python**: Follow PEP 8
- **Line length**: Max 120 characters
- **Docstrings**: Use Google style docstrings
- **Type hints**: Use for function signatures

### Example:

```python
def process_document(file_path: str, chunk_size: int = 512) -> List[str]:
    """
    Process a document and return chunks.
    
    Args:
        file_path: Path to the document file
        chunk_size: Size of each chunk in characters
    
    Returns:
        List of document chunks
    
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If chunk_size is invalid
    """
    pass
```

### Formatting

```bash
# Format code with black
make format
# or
black src/ tests/ --line-length=120

# Lint with flake8
make lint
# or
flake8 src/ tests/ --max-line-length=120
```

### Testing

```bash
# Run all tests
make test
# or
pytest

# Run specific test category
make test-unit
make test-integration
make test-performance

# Run with coverage
pytest --cov=src tests/
```

## Adding New Features

### 1. New LLM Provider

1. Create provider class in `src/generation/providers.py`:

```python
from src.generation.base import LLMProvider, LLMConfig

class MyLLMProvider(LLMProvider):
    """Custom LLM Provider implementation"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        # Initialize provider
    
    async def generate(self, prompt: str, context: str = "") -> str:
        """Generate response"""
        # Implementation
    
    async def validate_response(self, response: str) -> bool:
        """Validate response"""
        # Implementation
```

2. Register in `src/generation/manager.py`

3. Add tests in `tests/unit/`

### 2. New Validator

1. Create validator in `src/validation/validators.py`:

```python
from src.validation.base import ResponseValidator, ValidationResult

class MyValidator(ResponseValidator):
    """Custom response validator"""
    
    async def validate(self, response: str, context: str = "") -> ValidationResult:
        """Validate response"""
        # Implementation
        return ValidationResult(
            validator_name=self.name,
            is_valid=True,
            score=0.95,
            feedback="Validation passed"
        )
```

2. Register in `src/validation/manager.py`

3. Add tests in `tests/unit/`

### 3. New API Endpoint

1. Create route in appropriate file under `src/api/routes/`:

```python
from fastapi import APIRouter, HTTPException
from src.api.dependencies import get_service

router = APIRouter(prefix="/api/v1/my-feature", tags=["MyFeature"])

@router.post("/endpoint")
async def my_endpoint(request: MyRequest) -> MyResponse:
    """
    Endpoint description
    """
    pass
```

2. Register router in `src/main.py`

3. Add tests in `tests/integration/`

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `test`: Test additions/updates
- `docs`: Documentation
- `perf`: Performance improvements
- `chore`: Build, dependencies, etc.

**Example**:
```
feat(generation): add Claude provider support

Add support for Claude API as an LLM provider with automatic fallback.

Closes #123
```

## Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make Changes**
   - Follow code style guidelines
   - Add tests for new functionality
   - Update documentation

3. **Test Locally**
   ```bash
   make test
   make lint
   make format
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

5. **Push Branch**
   ```bash
   git push origin feature/your-feature
   ```

6. **Create Pull Request**
   - Clear description of changes
   - Link related issues
   - Include test results

7. **Address Review Comments**
   - Make requested changes
   - Push updates to the same branch
   - Ask questions if unclear

## Testing Requirements

### New Feature
- ✅ Unit tests for core logic
- ✅ Integration tests for API endpoints
- ✅ Documentation/docstrings
- ✅ Pass existing tests

### Bug Fix
- ✅ Test that reproduces the bug
- ✅ Test that verifies the fix
- ✅ Passes all existing tests

### Minimum Coverage
- **Target**: 80% code coverage
- **Critical paths**: 95%+ coverage

### Run Tests

```bash
# All tests
pytest

# With coverage report
pytest --cov=src tests/ --cov-report=html
# View in: htmlcov/index.html
```

## Documentation

### Required Documentation

1. **Code Comments**: Explain "why" not "what"
   ```python
   # Good
   # Retry up to 3 times because some providers have transient failures
   for attempt in range(3):
   
   # Bad
   # Try 3 times
   for attempt in range(3):
   ```

2. **Docstrings**: For all public functions/classes
   ```python
   def my_function(param: str) -> bool:
       """
       Brief description.
       
       Longer description if needed.
       
       Args:
           param: Description
       
       Returns:
           Description
       
       Raises:
           ExceptionType: When/why
       """
   ```

3. **Update README.md** if adding public features

4. **Update/create docs** if adding major features

## Debugging Tips

### Enable Debug Logging

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

### Run Single Test

```bash
pytest tests/unit/test_validators.py::test_relevance_validator -v
```

### Interactive Debugger

```python
import pdb; pdb.set_trace()
```

### View API Docs While Running

```bash
python -m uvicorn src.main:app --reload
# Open http://localhost:8000/docs
```

## Performance Considerations

- Avoid blocking operations in async code
- Cache expensive operations (embeddings, API calls)
- Use connection pooling for databases
- Profile performance-critical paths

### Profiling

```bash
pytest tests/performance/ -v
```

## Security Considerations

- Never commit `.env` files or secrets
- Validate all user inputs
- Use prepared statements for SQL
- Sanitize external data
- Check OWASP Top 10

## Versioning

This project follows [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking API changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes

## Release Process

(Handled by maintainers)

1. Update version in `config/settings.py`
2. Update `CHANGELOG.md`
3. Create git tag
4. Create release on GitHub

## Questions or Issues?

1. Check documentation in `docs/`
2. Search existing issues
3. Create a new issue with:
   - Clear description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Environment info

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Pydantic](https://pydantic-docs.helpmanual.io/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Python PEP 8](https://pep8.org/)

## Recognition

Contributors will be recognized in:
- `CONTRIBUTORS.md`
- Release notes
- Project documentation

Thank you for contributing! 🎉

---

**Last Updated**: March 2, 2026  
**Status**: Active Development
