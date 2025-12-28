"""Tests for council integration in generate command."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from edps.config import EdpsConfig, CouncilConfig, ModelsConfig
from edps.commands.generate import _generate_content, _generate_ai_book_content


class TestGenerateCouncilIntegration:
    """Test that generate commands respect council configuration."""

    def test_generate_content_uses_council_when_task_enabled(self):
        """Council is used when task is in config.council.tasks."""
        mock_client = MagicMock()
        mock_client.default_model = "test-model"
        mock_client.preview.return_value = MagicMock(
            input_tokens=100,
            cost=0.01,
        )

        config = EdpsConfig(
            council=CouncilConfig(
                enabled=True,
                tasks=["quiz"],
                member_roles=["summary", "quiz"],
                chair_role="quiz",
                stages=1,
            ),
            models=ModelsConfig(
                summary="model-a",
                quiz="model-b",
            ),
        )

        with patch("edps.commands.generate.load_prompt") as mock_load_prompt, \
             patch("edps.commands.generate.render_prompt") as mock_render_prompt, \
             patch("edps.commands.generate.Council") as MockCouncil:

            mock_load_prompt.return_value = "template"
            mock_render_prompt.return_value = "rendered prompt"

            mock_council_instance = MagicMock()
            mock_council_instance.run.return_value = MagicMock(
                final_answer="council answer",
                total_tokens=500,
            )
            MockCouncil.return_value = mock_council_instance

            section_dir = MagicMock(spec=Path)
            summary_path = MagicMock()
            summary_path.exists.return_value = True
            summary_path.read_text.return_value = "summary content"
            section_dir.__truediv__ = lambda self, x: summary_path

            result = _generate_content(
                client=mock_client,
                config=config,
                gen_type="quiz",
                section={"id": "001", "title": "Test"},
                source_text="source text",
                meta={"title": "Book", "author": "Author"},
                section_dir=section_dir,
                skip_confirm=True,
            )

            # Verify council was instantiated with correct params
            MockCouncil.assert_called_once_with(
                models=["model-a", "model-b"],
                chair="model-b",
                stages=1,
            )
            mock_council_instance.run.assert_called_once()
            assert result == "done"

    def test_generate_content_skips_council_when_task_not_enabled(self):
        """Single model is used when task is not in config.council.tasks."""
        mock_client = MagicMock()
        mock_client.default_model = "test-model"
        mock_client.preview.return_value = MagicMock(input_tokens=100, cost=0.01)
        mock_client.complete.return_value = MagicMock(
            content="single model answer",
            input_tokens=100,
            output_tokens=200,
            cost=0.02,
            provider="test",
        )

        config = EdpsConfig(
            council=CouncilConfig(
                enabled=True,
                tasks=["evaluation"],  # quiz not in list
            ),
        )

        with patch("edps.commands.generate.load_prompt") as mock_load_prompt, \
             patch("edps.commands.generate.render_prompt") as mock_render_prompt, \
             patch("edps.commands.generate.Council") as MockCouncil:

            mock_load_prompt.return_value = "template"
            mock_render_prompt.return_value = "rendered prompt"

            section_dir = MagicMock(spec=Path)
            summary_path = MagicMock()
            summary_path.exists.return_value = True
            summary_path.read_text.return_value = "summary content"
            section_dir.__truediv__ = lambda self, x: summary_path

            result = _generate_content(
                client=mock_client,
                config=config,
                gen_type="quiz",
                section={"id": "001", "title": "Test"},
                source_text="source text",
                meta={"title": "Book", "author": "Author"},
                section_dir=section_dir,
                skip_confirm=True,
            )

            # Verify council was NOT used
            MockCouncil.assert_not_called()
            # Verify single model was used
            mock_client.complete.assert_called_once()
            assert result == "done"

    def test_generate_content_skips_council_when_disabled(self):
        """Single model is used when council is disabled."""
        mock_client = MagicMock()
        mock_client.default_model = "test-model"
        mock_client.preview.return_value = MagicMock(input_tokens=100, cost=0.01)
        mock_client.complete.return_value = MagicMock(
            content="single model answer",
            input_tokens=100,
            output_tokens=200,
            cost=0.02,
            provider="test",
        )

        config = EdpsConfig(
            council=CouncilConfig(
                enabled=False,  # Disabled
                tasks=["quiz"],  # Even though quiz is listed
            ),
        )

        with patch("edps.commands.generate.load_prompt") as mock_load_prompt, \
             patch("edps.commands.generate.render_prompt") as mock_render_prompt, \
             patch("edps.commands.generate.Council") as MockCouncil:

            mock_load_prompt.return_value = "template"
            mock_render_prompt.return_value = "rendered prompt"

            section_dir = MagicMock(spec=Path)
            summary_path = MagicMock()
            summary_path.exists.return_value = True
            summary_path.read_text.return_value = "summary content"
            section_dir.__truediv__ = lambda self, x: summary_path

            result = _generate_content(
                client=mock_client,
                config=config,
                gen_type="quiz",
                section={"id": "001", "title": "Test"},
                source_text="source text",
                meta={"title": "Book", "author": "Author"},
                section_dir=section_dir,
                skip_confirm=True,
            )

            # Verify council was NOT used
            MockCouncil.assert_not_called()
            mock_client.complete.assert_called_once()
