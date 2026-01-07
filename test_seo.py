#!/usr/bin/env python3
"""
SEO Validation Test Suite
Tests HTML output for SEO compliance according to CLAUDE.md requirements
"""

import json
import re
from pathlib import Path
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple


class SEOParser(HTMLParser):
    """Extract SEO-relevant elements from HTML"""

    def __init__(self):
        super().__init__()
        self.title = None
        self.meta_description = None
        self.og_tags = {}
        self.twitter_tags = {}
        self.h1_tags = []
        self.json_ld_scripts = []
        self.canonical = None
        self.lang = None
        self.in_script = False
        self.current_script = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == 'html':
            self.lang = attrs_dict.get('lang')

        elif tag == 'title':
            self.in_title = True

        elif tag == 'meta':
            name = attrs_dict.get('name', '').lower()
            property = attrs_dict.get('property', '').lower()
            content = attrs_dict.get('content', '')

            if name == 'description':
                self.meta_description = content
            elif property.startswith('og:'):
                self.og_tags[property] = content
            elif name.startswith('twitter:'):
                self.twitter_tags[name] = content

        elif tag == 'link':
            rel = attrs_dict.get('rel', '')
            if rel == 'canonical':
                self.canonical = attrs_dict.get('href')

        elif tag == 'h1':
            self.in_h1 = True

        elif tag == 'script':
            script_type = attrs_dict.get('type', '')
            if script_type == 'application/ld+json':
                self.in_script = True
                self.current_script = []

    def handle_data(self, data):
        if hasattr(self, 'in_title') and self.in_title:
            self.title = data.strip()
        elif hasattr(self, 'in_h1') and self.in_h1:
            self.h1_tags.append(data.strip())
        elif self.in_script:
            self.current_script.append(data)

    def handle_endtag(self, tag):
        if tag == 'title' and hasattr(self, 'in_title'):
            self.in_title = False
        elif tag == 'h1' and hasattr(self, 'in_h1'):
            self.in_h1 = False
        elif tag == 'script' and self.in_script:
            self.in_script = False
            script_content = ''.join(self.current_script).strip()
            if script_content:
                try:
                    self.json_ld_scripts.append(json.loads(script_content))
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON-LD: {e}")


class SEOValidator:
    """Validate SEO requirements"""

    def __init__(self, html_path: Path):
        self.html_path = html_path
        self.html_content = html_path.read_text(encoding='utf-8')
        self.parser = SEOParser()
        self.parser.feed(self.html_content)
        self.errors = []
        self.warnings = []

    def validate_all(self) -> Tuple[List[str], List[str]]:
        """Run all validations"""
        self.validate_html_basics()
        self.validate_metadata()
        self.validate_schema()
        return self.errors, self.warnings

    def validate_html_basics(self):
        """Validate basic HTML SEO requirements"""
        # Check language attribute
        if not self.parser.lang:
            self.errors.append("Missing <html lang> attribute")
        elif self.parser.lang != 'en':
            self.warnings.append(f"Language is '{self.parser.lang}', expected 'en'")

        # Check single H1
        if not self.parser.h1_tags:
            self.errors.append("No H1 tag found")
        elif len(self.parser.h1_tags) > 1:
            self.errors.append(f"Multiple H1 tags found: {self.parser.h1_tags}")

        # Check canonical
        if not self.parser.canonical:
            self.warnings.append("No canonical link found")

    def validate_metadata(self):
        """Validate meta tags"""
        # Check title
        if not self.parser.title:
            self.errors.append("No <title> tag found")
        else:
            title_len = len(self.parser.title)
            if title_len < 30:
                self.warnings.append(f"Title too short ({title_len} chars): '{self.parser.title}'")
            elif title_len > 60:
                self.warnings.append(f"Title too long ({title_len} chars): '{self.parser.title}'")

        # Check meta description
        if not self.parser.meta_description:
            self.errors.append("No meta description found")
        else:
            desc_len = len(self.parser.meta_description)
            if desc_len < 70:
                self.warnings.append(f"Meta description too short ({desc_len} chars)")
            elif desc_len > 160:
                self.warnings.append(f"Meta description too long ({desc_len} chars)")

        # Check OpenGraph
        required_og = ['og:title', 'og:description', 'og:url', 'og:image']
        for tag in required_og:
            if tag not in self.parser.og_tags:
                self.warnings.append(f"Missing OpenGraph tag: {tag}")

        # Check Twitter Cards
        if 'twitter:card' not in self.parser.twitter_tags:
            self.warnings.append("Missing Twitter Card type")

    def validate_schema(self):
        """Validate JSON-LD schema"""
        if not self.parser.json_ld_scripts:
            self.warnings.append("No JSON-LD schema found")
            return

        # Check for valid schema types
        found_types = set()
        for script in self.parser.json_ld_scripts:
            schema_type = script.get('@type')
            if schema_type:
                found_types.add(schema_type)

            # Validate schema structure
            if '@context' not in script:
                self.errors.append(f"Schema missing @context: {schema_type}")
            elif script['@context'] != 'https://schema.org':
                self.warnings.append(f"Schema @context should be 'https://schema.org', got '{script['@context']}'")

            # Type-specific validation
            if schema_type == 'Book':
                self.validate_book_schema(script)
            elif schema_type == 'FAQPage':
                self.validate_faq_schema(script)
            elif schema_type == 'Person':
                self.validate_person_schema(script)

    def validate_book_schema(self, schema: dict):
        """Validate Book schema"""
        required = ['name', 'author', 'description']
        for field in required:
            if field not in schema:
                self.errors.append(f"Book schema missing required field: {field}")

        # Check author is Person
        if 'author' in schema:
            author = schema['author']
            if isinstance(author, dict) and author.get('@type') != 'Person':
                self.warnings.append(f"Book author should be Person type, got {author.get('@type')}")

        # Check offers
        if 'offers' in schema:
            offers = schema['offers']
            if not isinstance(offers, list):
                offers = [offers]
            for offer in offers:
                if offer.get('@type') != 'Offer':
                    self.errors.append("Book offer must be type Offer")
                if 'url' not in offer:
                    self.errors.append("Book offer missing URL")

    def validate_faq_schema(self, schema: dict):
        """Validate FAQPage schema"""
        if 'mainEntity' not in schema:
            self.errors.append("FAQPage missing mainEntity")
            return

        questions = schema['mainEntity']
        if not isinstance(questions, list):
            self.errors.append("FAQPage mainEntity must be a list")
            return

        if len(questions) < 2:
            self.warnings.append(f"FAQPage has only {len(questions)} question(s), recommend at least 2")

        for i, q in enumerate(questions):
            if q.get('@type') != 'Question':
                self.errors.append(f"FAQ item {i} must be type Question")
            if 'name' not in q:
                self.errors.append(f"FAQ question {i} missing 'name'")
            if 'acceptedAnswer' not in q:
                self.errors.append(f"FAQ question {i} missing 'acceptedAnswer'")
            elif q['acceptedAnswer'].get('@type') != 'Answer':
                self.errors.append(f"FAQ question {i} acceptedAnswer must be type Answer")

    def validate_person_schema(self, schema: dict):
        """Validate Person schema"""
        required = ['name']
        for field in required:
            if field not in schema:
                self.errors.append(f"Person schema missing required field: {field}")

        # Check name structure
        if 'givenName' not in schema or 'familyName' not in schema:
            self.warnings.append("Person schema should include givenName and familyName")


def test_book_page():
    """Test book page SEO compliance"""
    print("\n=== Testing Book Page ===")
    book_page = Path("docs/winter-cdt-book/winter-cdt-book/index.html")

    if not book_page.exists():
        print(f"❌ FAIL: Book page not found at {book_page}")
        print("   Run 'make html' first")
        return False

    validator = SEOValidator(book_page)
    errors, warnings = validator.validate_all()

    # Book page specific tests
    expected_title = "A Wild Calling"
    if validator.parser.title and expected_title not in validator.parser.title:
        errors.append(f"Title should contain '{expected_title}', got: '{validator.parser.title}'")

    expected_desc_keywords = ["winter", "Continental Divide", "ski"]
    if validator.parser.meta_description:
        desc_lower = validator.parser.meta_description.lower()
        missing = [kw for kw in expected_desc_keywords if kw.lower() not in desc_lower]
        if missing:
            errors.append(f"Meta description missing keywords: {missing}")

    # Check for Book and FAQPage schemas
    schema_types = {s.get('@type') for s in validator.parser.json_ld_scripts}
    if 'Book' not in schema_types:
        errors.append("Book page missing Book schema")
    if 'FAQPage' not in schema_types:
        warnings.append("Book page missing FAQPage schema (recommended)")

    # Report results
    passed = len(errors) == 0
    print(f"\n{'✅ PASS' if passed else '❌ FAIL'}: Book Page")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  ❌ {error}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")

    if passed and not warnings:
        print("  All checks passed!")

    return passed


def test_author_page():
    """Test author bio page SEO compliance"""
    print("\n=== Testing Author Page ===")
    author_page = Path("docs/info/my-story/index.html")

    if not author_page.exists():
        print(f"❌ FAIL: Author page not found at {author_page}")
        return False

    validator = SEOValidator(author_page)
    errors, warnings = validator.validate_all()

    # Check for Person schema
    schema_types = {s.get('@type') for s in validator.parser.json_ld_scripts}
    if 'Person' not in schema_types:
        errors.append("Author page missing Person schema")

    # Report results
    passed = len(errors) == 0
    print(f"\n{'✅ PASS' if passed else '❌ FAIL'}: Author Page")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  ❌ {error}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")

    if passed and not warnings:
        print("  All checks passed!")

    return passed


def test_homepage():
    """Test homepage SEO compliance"""
    print("\n=== Testing Homepage ===")
    homepage = Path("docs/index.html")

    if not homepage.exists():
        print(f"❌ FAIL: Homepage not found at {homepage}")
        return False

    validator = SEOValidator(homepage)
    errors, warnings = validator.validate_all()

    # Homepage specific checks
    if validator.parser.title and len(validator.parser.title) < 10:
        warnings.append("Homepage title is very generic")

    # Report results
    passed = len(errors) == 0
    print(f"\n{'✅ PASS' if passed else '❌ FAIL'}: Homepage")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  ❌ {error}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")

    return passed


def main():
    """Run all SEO tests"""
    print("=" * 60)
    print("SEO Validation Test Suite")
    print("=" * 60)

    # Check if docs directory exists
    docs_dir = Path("docs")
    if not docs_dir.exists():
        print("\n❌ FAIL: docs/ directory not found")
        print("Run 'make html' to generate the site first")
        return 1

    # Run tests
    results = {
        'Book Page': test_book_page(),
        'Author Page': test_author_page(),
        'Homepage': test_homepage(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    exit(main())
