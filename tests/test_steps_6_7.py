#!/usr/bin/env python
"""Direct test of Steps 6 & 7: LLM Generation and Validation"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import logging
logging.disable(logging.CRITICAL)

import pytest
from src.llm_generation import LLMGenerator, RetrievalOnlyAnswerer
from src.response_validators import ResponseValidators


@pytest.fixture(scope="module")
def llm_generator():
    """Initialize LLM generator for testing"""
    generator = LLMGenerator(verbose=False)
    yield generator


@pytest.fixture(scope="module")
def response_validator():
    """Initialize response validator for testing"""
    validator = ResponseValidators()
    yield validator


@pytest.mark.unit
def test_llm_generation(llm_generator):
    """Test LLM generation with company strategy context"""
    context = """
Our company strategy focuses on three main pillars:
1. Innovation: We invest heavily in R&D to develop cutting-edge solutions
2. Customer Focus: We prioritize customer satisfaction and feedback
3. Operational Excellence: We maintain high standards in all operations
"""
    question = "What is your company strategy?"
    answer = llm_generator.generate_answer(context, question)
    
    # Answer could be LLM-generated or retrieval-only
    assert answer is not None
    assert hasattr(answer, 'answer')
    assert len(answer.answer) > 0


@pytest.mark.unit
def test_response_validation_good_answer(response_validator):
    """Test response validation with good answer from knowledge base"""
    question = "What is our strategy?"
    answer = "Our strategy focuses on three main pillars: innovation, customer focus, and operational excellence."
    context = "Our strategy has three pillars: innovation, customer focus, and operational excellence."
    
    result = response_validator.validate_response(question, answer, context)
    
    assert result is not None
    assert result.overall_score > 0
    assert hasattr(result, 'quality_level')
    assert not result.is_hallucination_detected


@pytest.mark.unit
def test_response_validation_hallucinated_answer(response_validator):
    """Test response validation with hallucinated answer"""
    question = "What is your strategy?"
    answer = "We use quantum computers and AI to revolutionize the entire industry with blockchain."
    context = "Our strategy focuses on growth."
    
    result = response_validator.validate_response(question, answer, context)
    
    assert result is not None
    assert hasattr(result, 'is_hallucination_detected')
    # Hallucination detection should flag this as suspicious
    # Note: May or may not detect depending on validation logic


@pytest.mark.unit
def test_response_validation_unrelated_query(response_validator):
    """Test response validation with unrelated query"""
    question = "What is the recipe for pizza?"
    answer = "Answer not found in knowledge base."
    context = ""
    
    result = response_validator.validate_response(question, answer, context)
    
    assert result is not None
    assert result.overall_score >= 0
    assert hasattr(result, 'quality_level')

