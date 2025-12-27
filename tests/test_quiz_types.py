"""Tests for quiz question type definitions."""

class TestMCQTypes:
    """Tests for multiple choice question types."""

    def test_mcq_can_have_multiple_answers(self):
        """MCQ should support multiple correct answers."""
        from edps.quiz_types import MCQuestion, MCOption

        q = MCQuestion(
            question_id="mcq1",
            number=1,
            question="Which assumptions does Smith's argument depend on?",
            options=[
                MCOption("A", "Humans are rational", True),
                MCOption("B", "Exchange is possible", True),
                MCOption("C", "Government enforces contracts", False),
                MCOption("D", "Surplus is feasible", True),
            ],
            answer_type="multiple",
        )
        assert q.answer_type == "multiple"
        assert q.correct_count() == 3
        assert q.correct_letters() == {"A", "B", "D"}

    def test_mcq_can_have_no_answer(self):
        """MCQ should support none-correct option."""
        from edps.quiz_types import MCQuestion, MCOption

        q = MCQuestion(
            question_id="mcq2",
            number=2,
            question="Which would disprove Smith's thesis?",
            options=[
                MCOption("A", "Option that doesn't disprove", False),
                MCOption("B", "Another non-disproof", False),
                MCOption("C", "Still not a disproof", False),
                MCOption("D", "Nope", False),
            ],
            answer_type="none",
        )
        assert q.answer_type == "none"
        assert q.correct_count() == 0

    def test_mcoption_validates_letter(self):
        """MCOption should validate letter is A-H."""
        from edps.quiz_types import MCOption
        import pytest

        with pytest.raises(ValueError):
            MCOption("Z", "Invalid letter", True)

    def test_mcq_validates_answer_type(self):
        """MCQuestion should validate answer_type matches options."""
        from edps.quiz_types import MCQuestion, MCOption
        import pytest

        # answer_type="one" but 2 correct answers
        with pytest.raises(ValueError):
            MCQuestion(
                question_id="mcq_bad",
                number=1,
                question="Bad question",
                options=[
                    MCOption("A", "Correct 1", True),
                    MCOption("B", "Correct 2", True),
                ],
                answer_type="one",
            )


class TestMCQScoring:
    """Tests for MCQ F1-based partial credit scoring."""

    def test_score_mcq_perfect_multiple(self):
        """Perfect match on multiple-answer MCQ should score 1.0."""
        from edps.quiz_types import score_mcq_answer

        gold = {"A", "B", "D"}  # Correct answers
        selected = {"A", "B", "D"}  # Student selected
        score = score_mcq_answer(gold, selected)
        assert score == 1.0

    def test_score_mcq_partial_credit(self):
        """Partial match should use F1 formula."""
        from edps.quiz_types import score_mcq_answer

        gold = {"A", "B", "D"}  # 3 correct
        selected = {"A", "B"}  # 2 selected, both correct
        # Precision = 2/2 = 1.0, Recall = 2/3 = 0.667
        # F1 = 2 * 1.0 * 0.667 / (1.0 + 0.667) = 0.8
        score = score_mcq_answer(gold, selected)
        assert abs(score - 0.8) < 0.01

    def test_score_mcq_with_wrong_selection(self):
        """Wrong selections should reduce precision."""
        from edps.quiz_types import score_mcq_answer

        gold = {"A", "B"}  # 2 correct
        selected = {"A", "C"}  # 1 right, 1 wrong
        # Precision = 1/2 = 0.5, Recall = 1/2 = 0.5
        # F1 = 2 * 0.5 * 0.5 / (0.5 + 0.5) = 0.5
        score = score_mcq_answer(gold, selected)
        assert abs(score - 0.5) < 0.01

    def test_score_mcq_none_correct_type(self):
        """'None of the above' case: selecting nothing is correct."""
        from edps.quiz_types import score_mcq_answer

        gold = set()  # No correct answers
        selected = set()  # Student correctly selected none
        score = score_mcq_answer(gold, selected)
        assert score == 1.0

    def test_score_mcq_none_but_selected(self):
        """'None' type but student selected something: 0."""
        from edps.quiz_types import score_mcq_answer

        gold = set()  # No correct answers
        selected = {"A"}  # Student wrongly selected A
        score = score_mcq_answer(gold, selected)
        assert score == 0.0

    def test_score_mcq_single_answer(self):
        """Single-answer MCQ: 1 if correct, 0 otherwise."""
        from edps.quiz_types import score_mcq_answer

        gold = {"B"}
        assert score_mcq_answer(gold, {"B"}) == 1.0
        assert score_mcq_answer(gold, {"A"}) == 0.0
        assert score_mcq_answer(gold, {"A", "B"}) < 1.0  # Over-selected
