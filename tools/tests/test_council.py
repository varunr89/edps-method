"""Tests for LLM Council."""
import pytest
from unittest.mock import MagicMock

from edps.core.council import Council, CouncilResult


class TestCouncil:
    def test_stage1_gets_independent_answers(self):
        mock_client = MagicMock()
        mock_client.complete.return_value = MagicMock(
            content="Answer",
            input_tokens=10,
            output_tokens=20,
            provider="vscode"
        )

        council = Council(
            models=["gpt-5", "claude-sonnet-4.5"],
            chair="gpt-5",
            stages=1,  # Just stage 1
        )

        result = council.run("Evaluate this", mock_client)

        assert len(result.stage1) == 2
        assert "gpt-5" in result.stage1
        assert "claude-sonnet-4.5" in result.stage1

    def test_full_council_runs_all_stages(self):
        mock_client = MagicMock()
        call_count = 0

        def mock_complete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock(
                content=f"Response {call_count}",
                input_tokens=10,
                output_tokens=20,
                provider="vscode"
            )

        mock_client.complete.side_effect = mock_complete

        council = Council(
            models=["m1", "m2", "m3"],
            chair="m1",
            stages=3,
        )

        result = council.run("Evaluate", mock_client)

        # Stage 1: 3 answers, Stage 2: 3 reviews, Stage 3: 1 synthesis = 7
        assert call_count == 7
        assert result.final_answer is not None
        assert result.final_answer != ""

    def test_two_stage_council(self):
        mock_client = MagicMock()
        call_count = 0

        def mock_complete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock(
                content=f"Response {call_count}",
                input_tokens=10,
                output_tokens=20,
            )

        mock_client.complete.side_effect = mock_complete

        council = Council(
            models=["m1", "m2"],
            chair="m1",
            stages=2,
        )

        result = council.run("Evaluate", mock_client)

        # Stage 1: 2 answers, Stage 2: 2 reviews = 4
        assert call_count == 4
        assert len(result.stage2) == 2

    def test_council_tracks_tokens(self):
        mock_client = MagicMock()
        mock_client.complete.return_value = MagicMock(
            content="Answer",
            input_tokens=100,
            output_tokens=50,
        )

        council = Council(
            models=["m1"],
            chair="m1",
            stages=1,
        )

        result = council.run("Evaluate", mock_client)

        assert result.total_tokens == 150  # 100 + 50
