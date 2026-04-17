#!/usr/bin/env python
"""Test advanced Q&A system"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import logging
logging.disable(logging.CRITICAL)

import pytest
from src.qa_advanced_full import AdvancedQASystem


@pytest.fixture(scope="module")
def qa_system():
    """Initialize Q&A system for testing"""
    system = AdvancedQASystem()
    yield system
    system.close()


@pytest.mark.unit
def test_advanced_qa_production_2024(qa_system):
    """Test Q&A with production 2024 question"""
    question = "production 2024"
    threshold = 0.5
    answer = qa_system.get_answer(question, threshold=threshold)
    assert answer is not None
    assert len(answer) > 0
    assert isinstance(answer, str)


@pytest.mark.unit
def test_advanced_qa_net_zero_emission(qa_system):
    """Test Q&A with net zero emission question"""
    question = "net zero emission 2039"
    threshold = 0.5
    answer = qa_system.get_answer(question, threshold=threshold)
    assert answer is not None
    assert len(answer) > 0
    assert isinstance(answer, str)


@pytest.mark.unit
def test_advanced_qa_iima_policies(qa_system):
    """Test Q&A with IIMA policies question"""
    question = "IIMA policies"
    threshold = 0.6
    answer = qa_system.get_answer(question, threshold=threshold)
    assert answer is not None
    assert len(answer) > 0
    assert isinstance(answer, str)


@pytest.mark.unit
def test_advanced_qa_unrelated_query(qa_system):
    """Test Q&A with unrelated question"""
    question = "stock price Apple"
    threshold = 0.8
    answer = qa_system.get_answer(question, threshold=threshold)
    assert answer is not None
    assert isinstance(answer, str)
