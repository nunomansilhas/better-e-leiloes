#!/usr/bin/env python3
"""
Test script to verify scraper improvements logic
Tests dynamic wait time calculation and regex parsing
"""

import re


def test_image_counter_parsing():
    """Test parsing of image counter from various formats"""

    test_cases = [
        ("1/7", 7),          # Standard format
        ("3/12", 12),        # Double digits
        ("📷 7", 7),         # Emoji format
        ("📷 15", 15),       # Emoji with double digits
        ("📷  9", 9),        # Emoji with extra space
        ("5/5", 5),          # Same current/total
        ("1/1", 1),          # Single image
    ]

    pattern = r'(\d+)/(\d+)|📷\s*(\d+)'

    print("🧪 Testing Image Counter Parsing\n")
    print("Pattern:", pattern)
    print("-" * 50)

    all_passed = True

    for text, expected_total in test_cases:
        match = re.search(pattern, text)

        if match:
            # Extract total: group(2) for "X/Y" format, group(3) for "📷 Y" format
            total_images = int(match.group(2) if match.group(2) else match.group(3))

            passed = total_images == expected_total
            status = "✅ PASS" if passed else "❌ FAIL"

            print(f"{status} | Text: '{text:10}' | Expected: {expected_total:2} | Got: {total_images:2}")

            if not passed:
                all_passed = False
        else:
            print(f"❌ FAIL | Text: '{text:10}' | NO MATCH")
            all_passed = False

    print("-" * 50)
    print(f"\n{'✅ All tests passed!' if all_passed else '❌ Some tests failed!'}\n")
    return all_passed


def test_wait_time_calculation():
    """Test wait time calculation: (total_images × 2.5) + 1"""

    print("🧪 Testing Wait Time Calculation\n")
    print("Formula: (total_images × 2.5) + 1")
    print("-" * 50)

    test_cases = [
        (1, 3.5),      # 1 image: (1 × 2.5) + 1 = 3.5s
        (7, 18.5),     # 7 images: (7 × 2.5) + 1 = 18.5s
        (10, 26.0),    # 10 images: (10 × 2.5) + 1 = 26.0s
        (15, 38.5),    # 15 images: (15 × 2.5) + 1 = 38.5s
        (20, 51.0),    # 20 images: (20 × 2.5) + 1 = 51.0s
    ]

    all_passed = True

    for total_images, expected_wait in test_cases:
        wait_time = (total_images * 2.5) + 1

        passed = wait_time == expected_wait
        status = "✅ PASS" if passed else "❌ FAIL"

        print(f"{status} | {total_images:2} images → {wait_time:5.1f}s (expected {expected_wait:5.1f}s)")

        if not passed:
            all_passed = False

    print("-" * 50)
    print(f"\n{'✅ All tests passed!' if all_passed else '❌ Some tests failed!'}\n")
    return all_passed


def test_edge_cases():
    """Test edge cases and error conditions"""

    print("🧪 Testing Edge Cases\n")
    print("-" * 50)

    edge_cases = [
        ("No numbers here", None, "Should not match"),
        ("", None, "Empty string"),
        ("100/200", 200, "Large numbers"),
        ("0/0", 0, "Zero images"),
        ("foo 5/10 bar", 10, "Counter in middle of text"),
    ]

    pattern = r'(\d+)/(\d+)|📷\s*(\d+)'
    all_passed = True

    for text, expected, description in edge_cases:
        match = re.search(pattern, text)

        if expected is None:
            if match:
                print(f"❌ FAIL | '{text:20}' | {description} - Should not match but got match")
                all_passed = False
            else:
                print(f"✅ PASS | '{text:20}' | {description} - Correctly no match")
        else:
            if match:
                total = int(match.group(2) if match.group(2) else match.group(3))
                if total == expected:
                    print(f"✅ PASS | '{text:20}' | {description} - Got {total}")
                else:
                    print(f"❌ FAIL | '{text:20}' | {description} - Expected {expected}, got {total}")
                    all_passed = False
            else:
                print(f"❌ FAIL | '{text:20}' | {description} - Should match but didn't")
                all_passed = False

    print("-" * 50)
    print(f"\n{'✅ All tests passed!' if all_passed else '❌ Some tests failed!'}\n")
    return all_passed


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SCRAPER IMPROVEMENTS - LOGIC VERIFICATION")
    print("=" * 60 + "\n")

    test1 = test_image_counter_parsing()
    print()

    test2 = test_wait_time_calculation()
    print()

    test3 = test_edge_cases()
    print()

    print("=" * 60)
    if test1 and test2 and test3:
        print("✅ ALL TESTS PASSED - Logic is correct!")
    else:
        print("❌ SOME TESTS FAILED - Review implementation")
    print("=" * 60 + "\n")
