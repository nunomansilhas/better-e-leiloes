"""
Tests for Input Validation Module
"""

import pytest
from pydantic import ValidationError


class TestPaginationParams:
    """Tests for PaginationParams validator"""

    def test_valid_defaults(self):
        from validators import PaginationParams
        params = PaginationParams()
        assert params.page == 1
        assert params.limit == 50

    def test_valid_custom_values(self):
        from validators import PaginationParams
        params = PaginationParams(page=5, limit=100)
        assert params.page == 5
        assert params.limit == 100

    def test_rejects_page_zero(self):
        from validators import PaginationParams
        with pytest.raises(ValidationError):
            PaginationParams(page=0)

    def test_rejects_negative_page(self):
        from validators import PaginationParams
        with pytest.raises(ValidationError):
            PaginationParams(page=-1)

    def test_rejects_limit_over_500(self):
        from validators import PaginationParams
        with pytest.raises(ValidationError):
            PaginationParams(limit=501)

    def test_rejects_limit_zero(self):
        from validators import PaginationParams
        with pytest.raises(ValidationError):
            PaginationParams(limit=0)


class TestRefreshRequest:
    """Tests for RefreshRequest validator"""

    def test_valid_reference_lo(self):
        from validators import RefreshRequest
        req = RefreshRequest(reference="LO-123456")
        assert req.reference == "LO-123456"

    def test_valid_reference_np(self):
        from validators import RefreshRequest
        req = RefreshRequest(reference="NP-789012")
        assert req.reference == "NP-789012"

    def test_normalizes_to_uppercase(self):
        from validators import RefreshRequest
        req = RefreshRequest(reference="lo-123456")
        assert req.reference == "LO-123456"

    def test_strips_whitespace(self):
        from validators import RefreshRequest
        req = RefreshRequest(reference="  LO-123456  ")
        assert req.reference == "LO-123456"

    def test_rejects_invalid_format(self):
        from validators import RefreshRequest
        with pytest.raises(ValidationError):
            RefreshRequest(reference="invalid")

    def test_rejects_empty_string(self):
        from validators import RefreshRequest
        with pytest.raises(ValidationError):
            RefreshRequest(reference="")

    def test_default_refresh_type(self):
        from validators import RefreshRequest
        req = RefreshRequest(reference="LO-123456")
        assert req.refresh_type == "price"

    def test_valid_refresh_type_full(self):
        from validators import RefreshRequest
        req = RefreshRequest(reference="LO-123456", refresh_type="full")
        assert req.refresh_type == "full"

    def test_rejects_invalid_refresh_type(self):
        from validators import RefreshRequest
        with pytest.raises(ValidationError):
            RefreshRequest(reference="LO-123456", refresh_type="invalid")


class TestBatchRefreshRequest:
    """Tests for BatchRefreshRequest validator"""

    def test_valid_batch(self):
        from validators import BatchRefreshRequest
        req = BatchRefreshRequest(references=["LO-123456", "NP-789012"])
        assert len(req.references) == 2

    def test_normalizes_all_references(self):
        from validators import BatchRefreshRequest
        req = BatchRefreshRequest(references=["lo-123", "np-456"])
        assert all(ref.isupper() for ref in req.references)

    def test_rejects_empty_list(self):
        from validators import BatchRefreshRequest
        with pytest.raises(ValidationError):
            BatchRefreshRequest(references=[])

    def test_rejects_too_many_references(self):
        from validators import BatchRefreshRequest
        refs = [f"LO-{i}" for i in range(101)]
        with pytest.raises(ValidationError):
            BatchRefreshRequest(references=refs)

    def test_rejects_invalid_reference_in_batch(self):
        from validators import BatchRefreshRequest
        with pytest.raises(ValidationError):
            BatchRefreshRequest(references=["LO-123456", "invalid"])


class TestNotificationRuleRequest:
    """Tests for NotificationRuleRequest validator"""

    def test_valid_rule(self):
        from validators import NotificationRuleRequest
        rule = NotificationRuleRequest(
            name="Test Rule",
            rule_type="price_change"
        )
        assert rule.name == "Test Rule"
        assert rule.active is True  # default

    def test_valid_rule_types(self):
        from validators import NotificationRuleRequest
        valid_types = ["new_event", "price_change", "ending_soon", "watch_event"]
        for rule_type in valid_types:
            rule = NotificationRuleRequest(name="Test", rule_type=rule_type)
            assert rule.rule_type == rule_type

    def test_rejects_invalid_rule_type(self):
        from validators import NotificationRuleRequest
        with pytest.raises(ValidationError):
            NotificationRuleRequest(name="Test", rule_type="invalid")

    def test_rejects_preco_min_greater_than_max(self):
        from validators import NotificationRuleRequest
        with pytest.raises(ValidationError):
            NotificationRuleRequest(
                name="Test",
                rule_type="price_change",
                preco_min=100000,
                preco_max=50000
            )

    def test_accepts_valid_price_range(self):
        from validators import NotificationRuleRequest
        rule = NotificationRuleRequest(
            name="Test",
            rule_type="price_change",
            preco_min=10000,
            preco_max=100000
        )
        assert rule.preco_min == 10000
        assert rule.preco_max == 100000

    def test_sanitizes_name(self):
        from validators import NotificationRuleRequest
        rule = NotificationRuleRequest(
            name="  Test Rule  ",
            rule_type="price_change"
        )
        assert rule.name == "Test Rule"

    def test_strips_html_from_name(self):
        from validators import NotificationRuleRequest
        rule = NotificationRuleRequest(
            name="<script>alert('xss')</script>Test",
            rule_type="price_change"
        )
        assert "<script>" not in rule.name


class TestEventFilterParams:
    """Tests for EventFilterParams validator"""

    def test_valid_distrito(self):
        from validators import EventFilterParams
        params = EventFilterParams(distrito="Lisboa")
        assert params.distrito == "Lisboa"

    def test_sanitizes_distrito_whitespace(self):
        from validators import EventFilterParams
        params = EventFilterParams(distrito="  Porto  ")
        assert params.distrito == "Porto"

    def test_accepts_portuguese_characters(self):
        from validators import EventFilterParams
        params = EventFilterParams(distrito="Évora")
        assert params.distrito == "Évora"

    def test_accepts_hyphenated_names(self):
        from validators import EventFilterParams
        params = EventFilterParams(distrito="Vila-Nova")
        assert params.distrito == "Vila-Nova"

    def test_rejects_special_characters(self):
        from validators import EventFilterParams
        with pytest.raises(ValidationError):
            EventFilterParams(distrito="<script>")


class TestUtilityFunctions:
    """Tests for utility validation functions"""

    def test_validate_reference(self):
        from validators import validate_reference
        assert validate_reference("lo-123") == "LO-123"
        assert validate_reference("NP-456") == "NP-456"

    def test_validate_reference_invalid(self):
        from validators import validate_reference
        with pytest.raises(ValueError):
            validate_reference("invalid")

    def test_validate_tipo_id_valid(self):
        from validators import validate_tipo_id
        for i in range(1, 7):
            assert validate_tipo_id(i) == i

    def test_validate_tipo_id_invalid(self):
        from validators import validate_tipo_id
        with pytest.raises(ValueError):
            validate_tipo_id(0)
        with pytest.raises(ValueError):
            validate_tipo_id(7)

    def test_sanitize_string(self):
        from validators import sanitize_string
        assert sanitize_string("  test  ") == "test"
        assert sanitize_string("<b>bold</b>") == "bold"

    def test_sanitize_string_truncates(self):
        from validators import sanitize_string
        long_string = "a" * 300
        result = sanitize_string(long_string, max_length=100)
        assert len(result) == 100
