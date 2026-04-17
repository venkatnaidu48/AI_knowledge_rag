#!/usr/bin/env python
"""Quick test of complete RAG pipeline"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import logging
logging.disable(logging.CRITICAL)

import pytest
from src.rag_pipeline_improved import ImprovedRAGPipeline


@pytest.fixture(scope="module")
def rag_pipeline():
    """Initialize RAG pipeline for testing"""
    pipeline = ImprovedRAGPipeline(verbose=False)
    yield pipeline
    pipeline.close()


@pytest.mark.unit
def test_rag_pipeline_production_2024(rag_pipeline):
    """Test RAG pipeline with production 2024 query"""
    query = "production 2024"
    response = rag_pipeline.process_query(query)
    assert response is not None
    assert response.answer is not None
    assert len(response.answer) > 0


@pytest.mark.unit
def test_rag_pipeline_net_zero_emission(rag_pipeline):
    """Test RAG pipeline with net zero emission query"""
    query = "net zero emission 2039"
    response = rag_pipeline.process_query(query)
    assert response is not None
    assert response.answer is not None
    assert len(response.answer) > 0


@pytest.mark.unit
def test_rag_pipeline_iima_policies(rag_pipeline):
    """Test RAG pipeline with IIMA policies query"""
    query = "IIMA policies"
    response = rag_pipeline.process_query(query)
    assert response is not None
    assert response.answer is not None
    assert len(response.answer) > 0


@pytest.mark.unit
def test_rag_pipeline_unrelated_query(rag_pipeline):
    """Test RAG pipeline with unrelated query"""
    query = "pizza recipe"
    response = rag_pipeline.process_query(query)
    assert response is not None
    assert response.answer is not None
