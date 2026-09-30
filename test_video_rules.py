from __future__ import annotations

import unittest

from phase2_video.rules import decide_video


class VideoRulesTests(unittest.TestCase):
    def base(self, **updates):
        values = {
            "importance": 70,
            "content_kind": "event",
            "phase1_verification_statuses": ["CONFIRMED_MULTI_SOURCE"],
            "phase2_verification_statuses": ["VERIFIED_MULTISOURCE"],
            "verified_fact_count": 1,
            "statement_count": 0,
            "verified_event_count": 1,
            "source_ids": ["reuters", "ap"],
            "operational_health": "healthy",
            "source_health": "healthy",
            "material_change": True,
            "new_event": True,
            "operational_impact": "CONTEXT",
            "traceability_complete": True,
            "factual_package_valid": True,
            "state_consistent": True,
            "has_future_data": False,
            "content_hash_valid": True,
            "duplicate_package": False,
        }
        values.update(updates)
        return values

    def test_importance_20_is_no_video(self):
        decision = decide_video(**self.base(importance=20))
        self.assertFalse(decision.video_recommended)
        self.assertIn("BELOW_VIDEO_THRESHOLD", decision.reason_codes)

    def test_importance_60_is_daily_only_when_material(self):
        event_decision = decide_video(**self.base(importance=60))
        daily = decide_video(**self.base(importance=60, content_kind="daily_summary"))
        self.assertFalse(event_decision.video_recommended)
        self.assertTrue(daily.video_recommended)
        self.assertEqual(daily.video_type, "daily_summary")

    def test_importance_70_is_explainer(self):
        decision = decide_video(**self.base(importance=70))
        self.assertTrue(decision.video_recommended)
        self.assertEqual(decision.video_type, "explainer")

    def test_importance_90_material_verified_is_breaking_candidate(self):
        decision = decide_video(**self.base(importance=90, operational_impact="MATERIAL"))
        self.assertTrue(decision.video_recommended)
        self.assertEqual(decision.video_type, "breaking")
        self.assertIn("BREAKING_CANDIDATE", decision.reason_codes)

    def test_single_source_cannot_be_breaking(self):
        decision = decide_video(**self.base(
            importance=90,
            phase1_verification_statuses=["SINGLE_SOURCE"],
            phase2_verification_statuses=[],
            verified_fact_count=0,
            source_ids=["reuters"],
            operational_impact="MATERIAL",
        ))
        self.assertFalse(decision.video_recommended)
        self.assertIn("SINGLE_SOURCE", decision.reason_codes)

    def test_declaration_only_cannot_be_breaking(self):
        decision = decide_video(**self.base(
            importance=90,
            phase1_verification_statuses=["DECLARATION_ONLY"],
            phase2_verification_statuses=[],
            verified_fact_count=0,
            statement_count=1,
            operational_impact="MATERIAL",
        ))
        self.assertFalse(decision.video_recommended)
        self.assertIn("ONLY_DECLARATIONS", decision.reason_codes)

    def test_conflict_blocks_all_video(self):
        decision = decide_video(**self.base(
            importance=90,
            phase1_verification_statuses=["CONFLICTING"],
            phase2_verification_statuses=[],
            verified_fact_count=0,
        ))
        self.assertFalse(decision.video_recommended)
        self.assertIn("UNRESOLVED_CONFLICT", decision.reason_codes)

    def test_stale_health_blocks_video(self):
        decision = decide_video(**self.base(operational_health="stale"))
        self.assertFalse(decision.video_recommended)
        self.assertIn("STALE_OPERATIONAL_CONTEXT", decision.reason_codes)

    def test_duplicate_does_not_regenerate(self):
        decision = decide_video(**self.base(duplicate_package=True))
        self.assertFalse(decision.video_recommended)
        self.assertIn("DUPLICATE_PACKAGE", decision.reason_codes)

    def test_same_input_is_identical_and_review_is_always_required(self):
        left = decide_video(**self.base())
        right = decide_video(**self.base())
        self.assertEqual(left, right)
        self.assertTrue(left.human_review_required)
        rejected = decide_video(**self.base(importance=20))
        self.assertTrue(rejected.human_review_required)


if __name__ == "__main__":
    unittest.main()
