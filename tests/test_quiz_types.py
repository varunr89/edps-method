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
