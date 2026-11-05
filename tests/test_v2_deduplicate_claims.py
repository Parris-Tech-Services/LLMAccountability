"""L07: real deterministic claim extraction must not inflate metrics."""
import unittest
from v2.parsers.claim_extractor import ClaimExtractor
from v2.policy.engine import PolicyEngine
from v2.recipes.base import RecipeResult, Verdict


class DedupClaimsTests(unittest.TestCase):
    def test_historical_verified_complete_wording_requires_evidence(self):
        claims = ClaimExtractor.extract("VERIFIED COMPLETE", report_id="historical")
        self.assertEqual([c["type"] for c in claims], ["fully-complete"])
        self.assertNotEqual(PolicyEngine.evaluate(claims, {})["final_verdict"], Verdict.PASS)

    def test_empty_or_unsupported_report_never_passes(self):
        for text in ("", "Everything is done; deployed successfully", "Reviewed project goals."):
            with self.subTest(text=text):
                claims = ClaimExtractor.extract(text)
                self.assertEqual(PolicyEngine.evaluate(claims, {})["final_verdict"], Verdict.INCONCLUSIVE)

    def test_real_supported_claim_with_recipe_result_still_passes(self):
        claims = ClaimExtractor.extract("All tests passed", report_id="positive")
        result = RecipeResult(Verdict.PASS, {"observed": True})
        self.assertEqual(PolicyEngine.evaluate(claims, {claims[0]['id']: result})["final_verdict"], Verdict.PASS)

    def test_overlapping_test_patterns_produce_only_one_claim(self):
        claims = ClaimExtractor.extract("The automated tests passed", report_id="observed")
        self.assertEqual([c["type"] for c in claims], ["tests-pass"])

    def test_repeated_phrase_only_one_per_family(self):
        claims = ClaimExtractor.extract(
            "The automated tests passed. All tests passed. tests pass.",
            report_id="observed")
        self.assertEqual(sum(c["type"] == "tests-pass" for c in claims), 1)

    def test_other_claim_families_not_lost(self):
        claims = ClaimExtractor.extract(
            "The automated tests passed; pushed to main; fully complete.",
            report_id="observed")
        self.assertEqual({c["type"] for c in claims},
                         {"tests-pass", "pushed", "fully-complete"})
        self.assertEqual(len(claims), 3)

    def test_deterministic_id_and_report_bound(self):
        a = ClaimExtractor.extract("The automated tests passed", report_id="A")
        b = ClaimExtractor.extract("The automated tests passed", report_id="A")
        c = ClaimExtractor.extract("The automated tests passed", report_id="B")
        self.assertEqual(a, b)
        self.assertNotEqual(a[0]["id"], c[0]["id"])

    def test_known_existing_ids_are_preserved(self):
        # Locked values computed from original pre-fix extractor, not from the
        # current function. A precedence/hash change must fail this regression.
        overlapping = ClaimExtractor.extract(
            "The automated tests passed", report_id="observed")
        self.assertEqual(overlapping[0]["raw_text"], "tests pass")
        self.assertEqual(overlapping[0]["id"], "a9f969170f2959d8")

        unaffected = ClaimExtractor.extract("pushed to main", report_id="R")
        self.assertEqual(unaffected[0]["raw_text"], "pushed to")
        self.assertEqual(unaffected[0]["id"], "b520214b44587c0d")

    def test_no_checkable_claim_does_not_fabricate_one(self):
        self.assertEqual(ClaimExtractor.extract("Reviewed project goals.", report_id="R"), [])

    def test_repeated_words_with_separate_groups_dont_duplicate(self):
        claims = ClaimExtractor.extract(
            "pushed to main; pushed to main; secure and authentication is secure; fully complete.",
            report_id="R")
        types = [c["type"] for c in claims]
        self.assertEqual(types.count("pushed"), 1)
        self.assertEqual(types.count("security-reviewed"), 1)
        self.assertEqual(types.count("fully-complete"), 1)


if __name__ == "__main__":
    unittest.main()
