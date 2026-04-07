import pytest
from app.services.nlp import classify_domain_category, extract_aspects


def test_classify_support_keywords():
    cat, sub = classify_domain_category('customer support did not respond to my complaint')
    assert cat.lower() == 'support'
    assert 'response' in sub.lower() or 'resolution' in sub.lower()


def test_extract_customer_support_aspects_negative():
    aspects = extract_aspects('Customer support was useless and no response from support team')
    assert 'customer_support' in aspects or 'support' in aspects
    assert aspects.get('customer_support') == 'negative'


def test_extract_delivery_time_aspect():
    aspects = extract_aspects('Delivery was late by 2 hours, took too long')
    assert aspects.get('delivery_time') == 'negative'
