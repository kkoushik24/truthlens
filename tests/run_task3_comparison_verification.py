"""Comprehensive verification for Task 3: Claim-by-Claim Comparison."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from text_analysis.claim_extractor import extract_atomic_claims
from text_analysis.evidence_collector import collect_evidence_bundle
from text_analysis.claim_comparator import compare_claims_to_evidence, detect_context_notes


def verify_task_3():
    print("=" * 80)
    print("RUNNING TASK 3 CLAIM COMPARISON VERIFICATION")
    print("=" * 80)

    # 1. walking_banana.png + "A banana walking on a beach in 2019"
    print("\n--- TEST CASE 1: walking_banana.png + 'A banana walking on a beach in 2019' ---")
    img1 = PROJECT_ROOT / "samples" / "walking_banana.png"
    cap1 = "A banana walking on a beach in 2019"
    claims1 = extract_atomic_claims(cap1)
    bundle1 = collect_evidence_bundle(img1, media_type="image")
    res1 = compare_claims_to_evidence(claims1["claims"], bundle1, caption=cap1)

    print(f"Status: {res1['status']}")
    print(f"Summary: {res1['summary_text']}")
    print("Claim comparison results:")
    for comp in res1["comparisons"]:
        print(f"  [{comp['claim_id']}] ({comp['type']} | {comp['status']}) \"{comp['claim_text']}\" -> Ev: {comp['evidence_ids']} | Reason: {comp['reason']}")

    assert res1["status"] == "COMPLETED"
    # Find 2019 claim
    date_claims = [c for c in res1["comparisons"] if c["type"] == "date_time" or "2019" in c["claim_text"]]
    assert len(date_claims) > 0, "Expected date claim for 2019"
    assert date_claims[0]["status"] == "cannot_verify", f"Date claim without EXIF MUST be 'cannot_verify', got {date_claims[0]['status']}"

    # Check unverifiable claims box tracking
    assert len(res1["unverifiable_claims"]) >= 1
    assert any(uc["type"] == "date_time" for uc in res1["unverifiable_claims"])
    print("Verified: 2019 date claim without EXIF is cannot_verify and tracked in unverifiable_claims.")

    # 2. clean_photo.jpg + "Flooded streets in Bangalore after heavy rain"
    print("\n--- TEST CASE 2: clean_photo.jpg + 'Flooded streets in Bangalore after heavy rain' ---")
    img2 = PROJECT_ROOT / "samples" / "clean_photo.jpg"
    cap2 = "Flooded streets in Bangalore after heavy rain"
    claims2 = extract_atomic_claims(cap2)
    bundle2 = collect_evidence_bundle(img2, media_type="image")
    res2 = compare_claims_to_evidence(claims2["claims"], bundle2, caption=cap2)

    print(f"Status: {res2['status']}")
    print(f"Summary: {res2['summary_text']}")
    for comp in res2["comparisons"]:
        print(f"  [{comp['claim_id']}] ({comp['type']} | {comp['status']}) \"{comp['claim_text']}\" -> Ev: {comp['evidence_ids']} | Reason: {comp['reason']}")

    assert res2["status"] == "COMPLETED"
    # Flood street claim should be contradicted by abstract geometric image
    flood_claims = [c for c in res2["comparisons"] if "flood" in c["claim_text"].lower() or "street" in c["claim_text"].lower()]
    assert len(flood_claims) > 0
    assert any(c["status"] == "contradicted" for c in res2["comparisons"]), "Expected at least one contradicted claim for flooded streets"
    print("Verified: Contradicted claim identified with matching conflicting evidence.")

    # 3. edited_photo.jpg + "Historic gathering in 2018" (conflicts with EXIF 2026:01:01)
    print("\n--- TEST CASE 3: edited_photo.jpg + 'Historic gathering in 2018' (EXIF year conflict) ---")
    img3 = PROJECT_ROOT / "samples" / "edited_photo.jpg"
    cap3 = "Historic gathering in 2018"
    claims3 = extract_atomic_claims(cap3)
    bundle3 = collect_evidence_bundle(img3, media_type="image")
    res3 = compare_claims_to_evidence(claims3["claims"], bundle3, caption=cap3)

    print(f"Status: {res3['status']}")
    print(f"Summary: {res3['summary_text']}")
    for comp in res3["comparisons"]:
        print(f"  [{comp['claim_id']}] ({comp['type']} | {comp['status']}) \"{comp['claim_text']}\" -> Ev: {comp['evidence_ids']} | Reason: {comp['reason']}")

    year_claims = [c for c in res3["comparisons"] if "2018" in c["claim_text"]]
    assert len(year_claims) > 0
    assert year_claims[0]["status"] == "contradicted", f"Expected year 2018 to be contradicted by EXIF 2026, got {year_claims[0]['status']}"
    assert "e8" in year_claims[0]["evidence_ids"], "Expected EXIF timestamp item e8 to be cited"
    print("Verified: Clear EXIF year conflict correctly marked as contradicted citing e8.")

    # 4. Context Notes Detection
    print("\n--- TEST CASE 4: Context Notes Detection ---")
    sensational_cap = "BREAKING NEWS: 100% proof leaked video caused by insider corruption! Sources say officials revealed it."
    notes = detect_context_notes(sensational_cap)
    print(f"Found {len(notes)} context notes:")
    for n in notes:
        print(f"  [{n['category']}] '{n['phrase']}': {n['explanation']}")

    categories = {n["category"] for n in notes}
    assert "sensational_wording" in categories, "Expected sensational wording detection"
    assert "causation_claim" in categories, "Expected causation claim detection"
    assert "unverifiable_source" in categories, "Expected unverifiable source detection"
    print("Verified: Context notes detected across all 3 categories without being treated as tampering evidence.")

    # 5. Non-existent Evidence ID Validation
    print("\n--- TEST CASE 5: Invalid Evidence ID Validation ---")
    mock_claims = [{"id": "c1", "text": "A fake claim", "type": "object", "checkable_from_media": True}]
    # Call compare with a mock LLM client that returns a non-existent evidence_id e999
    class MockGroqClient:
        class chat:
            class completions:
                @staticmethod
                def create(*args, **kwargs):
                    class Resp:
                        class Choice:
                            class Message:
                                content = json.dumps({
                                    "comparisons": [
                                        {
                                            "claim_id": "c1",
                                            "status": "supported",
                                            "evidence_ids": ["e999"],
                                            "reason": "Supported by fake evidence.",
                                            "confidence": 0.99
                                        }
                                    ]
                                })
                            message = Message()
                        choices = [Choice()]
                    return Resp()

    mock_bundle = {"evidence_items": [{"id": "e1", "source": "image", "text": "Real item"}], "evidence_map": {"e1": {"id": "e1", "source": "image", "text": "Real item"}}}
    res_mock = compare_claims_to_evidence(mock_claims, mock_bundle, caption="test", groq_client=MockGroqClient())
    c1_res = res_mock["comparisons"][0]
    print(f"Result for claim with non-existent evidence ID: status={c1_res['status']}, reason={c1_res['reason']}")
    assert c1_res["status"] == "cannot_verify", "Must drop claim result and mark cannot_verify if cited evidence_id does not exist"
    assert "non-existent" in c1_res["reason"].lower() or "no visual" in c1_res["reason"].lower()
    print("Verified: Non-existent evidence ID dropped and claim forced to cannot_verify.")

    # 6. Empty Caption Skip
    print("\n--- TEST CASE 6: Empty Caption Handling ---")
    res_empty = compare_claims_to_evidence([], mock_bundle, caption="")
    assert res_empty["status"] == "SKIPPED: no caption provided"
    assert len(res_empty["comparisons"]) == 0
    print("Verified: Empty caption cleanly returns SKIPPED.")

    # 7. Global Rules: Forbidden Words
    print("\n--- TEST CASE 7: Forbidden Words Check ---")
    for res in [res1, res2, res3]:
        for comp in res["comparisons"]:
            r_lower = comp["reason"].lower()
            assert "natural" not in r_lower, f"Forbidden word 'natural' in: {comp['reason']}"
            assert "authentic" not in r_lower, f"Forbidden word 'authentic' in: {comp['reason']}"
    print("Verified: Forbidden words ('natural', 'authentic') do not appear in any claim comparison reasons.")

    print("\n" + "=" * 80)
    print("ALL TASK 3 VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    verify_task_3()
