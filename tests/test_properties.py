"""Property-based tests for scoring and parsing."""
from hypothesis import given, strategies as st, assume
from edps.quiz_types import score_mcq_answer


class TestMCQScoringProperties:
    """Property-based tests for MCQ scoring invariants."""

    @given(
        gold=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=0, max_size=4),
        selected=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=0, max_size=4),
    )
    def test_score_always_between_0_and_1(self, gold, selected):
        """Score should always be in [0, 1] range."""
        score = score_mcq_answer(set(gold), set(selected))
        assert 0.0 <= score <= 1.0

    @given(
        gold=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=1, max_size=4),
    )
    def test_perfect_match_scores_1(self, gold):
        """Selecting exactly the correct answers should score 1.0."""
        score = score_mcq_answer(set(gold), set(gold))
        assert score == 1.0

    @given(
        gold=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=1, max_size=4),
        wrong=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=1, max_size=4),
    )
    def test_no_overlap_scores_0(self, gold, wrong):
        """Selecting only wrong answers should score 0."""
        assume(not (gold & wrong))  # Ensure no overlap
        score = score_mcq_answer(set(gold), set(wrong))
        assert score == 0.0

    @given(
        gold=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=2, max_size=4),
    )
    def test_partial_selection_less_than_perfect(self, gold):
        """Selecting a subset of correct answers should score < 1.0."""
        partial = set(list(gold)[:-1])  # Remove one
        assume(len(partial) >= 1)
        score = score_mcq_answer(set(gold), partial)
        assert score < 1.0

    @given(
        gold=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=1, max_size=3),
    )
    def test_adding_correct_increases_score(self, gold):
        """Adding a correct answer should not decrease score."""
        gold_list = list(gold)
        for i in range(len(gold_list)):
            partial = set(gold_list[:i+1])
            next_partial = set(gold_list[:i+2]) if i+2 <= len(gold_list) else set(gold)
            score1 = score_mcq_answer(set(gold), partial)
            score2 = score_mcq_answer(set(gold), next_partial)
            assert score2 >= score1 - 0.001  # Allow tiny float error

    @given(
        gold=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=1, max_size=4),
    )
    def test_empty_selection_scores_0(self, gold):
        """Selecting nothing when there are correct answers should score 0."""
        score = score_mcq_answer(set(gold), set())
        assert score == 0.0

    @given(
        gold=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=1, max_size=4),
        selected=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=1, max_size=4),
    )
    def test_score_is_symmetric_in_calculation(self, gold, selected):
        """F1 score should be symmetric: swapping gold and selected should give same result."""
        # This tests F1's symmetry property: F1(gold, selected) = F1(selected, gold)
        # when both are non-empty
        score_normal = score_mcq_answer(set(gold), set(selected))
        score_swapped = score_mcq_answer(set(selected), set(gold))
        assert abs(score_normal - score_swapped) < 0.001


class TestSchemaMigrationProperties:
    """Property-based tests for schema migration invariants."""

    @given(
        num_answers=st.integers(min_value=1, max_value=10),
    )
    def test_migration_preserves_answer_count(self, num_answers):
        """Migration should preserve the number of answers."""
        from edps.evaluation import migrate_v0_to_v1

        v0_data = {
            "quiz": {
                "answers": [{"label": f"Q{i}", "correct": True, "note": "OK", "score": 1.0}
                            for i in range(num_answers)],
                "total_score": num_answers,
                "reasoning": "Good"
            }
        }

        v1_data = migrate_v0_to_v1(v0_data)
        assert len(v1_data["quiz"]["answers"]) == num_answers

    @given(
        original_note=st.text(min_size=1, max_size=100),
    )
    def test_migration_maps_note_to_explanation(self, original_note):
        """Migration should map note -> explanation for each answer."""
        from edps.evaluation import migrate_v0_to_v1

        v0_data = {
            "quiz": {
                "answers": [{"label": "Q1", "correct": True, "note": original_note, "score": 1.0}],
                "total_score": 1,
                "reasoning": "Good"
            }
        }

        v1_data = migrate_v0_to_v1(v0_data)
        assert v1_data["quiz"]["answers"][0]["explanation"] == original_note

    @given(
        original_score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    def test_migration_preserves_total_score(self, original_score):
        """Migration should preserve total_score value."""
        from edps.evaluation import migrate_v0_to_v1

        v0_data = {
            "quiz": {
                "answers": [{"label": "Q1", "correct": True, "note": "OK", "score": 1.0}],
                "total_score": original_score,
                "reasoning": "Good"
            }
        }

        v1_data = migrate_v0_to_v1(v0_data)
        assert v1_data["quiz"]["total_score"] == original_score

    @given(
        correct_values=st.lists(st.booleans(), min_size=1, max_size=8),
    )
    def test_migration_preserves_correct_flags(self, correct_values):
        """Migration should preserve the correct flag for each answer."""
        from edps.evaluation import migrate_v0_to_v1

        v0_data = {
            "quiz": {
                "answers": [
                    {"label": f"Q{i}", "correct": c, "note": "OK", "score": 1.0 if c else 0.0}
                    for i, c in enumerate(correct_values)
                ],
                "total_score": sum(correct_values),
                "reasoning": "Good"
            }
        }

        v1_data = migrate_v0_to_v1(v0_data)

        for i, expected in enumerate(correct_values):
            assert v1_data["quiz"]["answers"][i]["correct"] == expected

    @given(
        label=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    )
    def test_migration_preserves_label(self, label):
        """Migration should preserve the label field."""
        from edps.evaluation import migrate_v0_to_v1

        v0_data = {
            "quiz": {
                "answers": [{"label": label, "correct": True, "note": "OK", "score": 1.0}],
                "total_score": 1,
                "reasoning": "Good"
            }
        }

        v1_data = migrate_v0_to_v1(v0_data)
        assert v1_data["quiz"]["answers"][0]["label"] == label

    @given(
        reasoning_text=st.text(min_size=0, max_size=200),
    )
    def test_migration_preserves_reasoning(self, reasoning_text):
        """Migration should preserve the reasoning field."""
        from edps.evaluation import migrate_v0_to_v1

        v0_data = {
            "quiz": {
                "answers": [{"label": "Q1", "correct": True, "note": "OK", "score": 1.0}],
                "total_score": 1,
                "reasoning": reasoning_text
            }
        }

        v1_data = migrate_v0_to_v1(v0_data)
        assert v1_data["quiz"]["reasoning"] == reasoning_text

    def test_migration_adds_schema_version(self):
        """Migration should always add schema_version='v1'."""
        from edps.evaluation import migrate_v0_to_v1

        v0_data = {
            "quiz": {
                "answers": [{"label": "Q1", "correct": True, "note": "OK", "score": 1.0}],
                "total_score": 1,
                "reasoning": "Good"
            }
        }

        v1_data = migrate_v0_to_v1(v0_data)
        assert v1_data["quiz"]["schema_version"] == "v1"

    @given(
        num_answers=st.integers(min_value=1, max_value=10),
    )
    def test_migration_assigns_sequential_question_ids(self, num_answers):
        """Migration should assign sequential question_ids (q1, q2, ...)."""
        from edps.evaluation import migrate_v0_to_v1

        v0_data = {
            "quiz": {
                "answers": [{"label": f"Q{i}", "correct": True, "note": "OK", "score": 1.0}
                            for i in range(num_answers)],
                "total_score": num_answers,
                "reasoning": "Good"
            }
        }

        v1_data = migrate_v0_to_v1(v0_data)

        for i in range(num_answers):
            expected_id = f"q{i+1}"
            assert v1_data["quiz"]["answers"][i]["question_id"] == expected_id
