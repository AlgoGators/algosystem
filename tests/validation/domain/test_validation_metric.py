from algosystem.validation.domain.validation_metric import LEGACY_ALIASES, ValidationMetricKey


def test_validation_metric_synonyms_are_legacy_aliases_not_enum_members():
    values = [metric.value for metric in ValidationMetricKey]

    assert "acf_1" not in values
    assert "min_track_record" not in values
    assert "prob_overfit" not in values
    assert LEGACY_ALIASES["acf_1"] is ValidationMetricKey.ACF1
    assert LEGACY_ALIASES["min_track_record"] is ValidationMetricKey.MIN_TRL
    assert LEGACY_ALIASES["prob_overfit"] is ValidationMetricKey.PBO
