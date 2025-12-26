"""LLM Council for multi-model evaluation."""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from edps.core.llm import LLMClient


@dataclass
class CouncilResult:
    """Result of council evaluation."""
    stage1: dict[str, str] = field(default_factory=dict)
    stage2: dict[str, str] = field(default_factory=dict)
    final_answer: str = ""
    total_tokens: int = 0


class Council:
    """Multi-model council for evaluation tasks."""

    def __init__(
        self,
        models: list[str],
        chair: str,
        stages: int = 3,
    ):
        self.models = models
        self.chair = chair
        self.stages = stages

    def run(self, prompt: str, client: "LLMClient") -> CouncilResult:
        """Run the council evaluation."""
        result = CouncilResult()
        total_tokens = 0

        # Stage 1: Independent answers
        for model in self.models:
            response = client.complete(
                prompt=f"You are participating in a council evaluation.\n\n{prompt}",
                model=model,
            )
            result.stage1[model] = response.content
            total_tokens += response.input_tokens + response.output_tokens

        if self.stages < 2:
            result.final_answer = result.stage1.get(self.chair, "")
            result.total_tokens = total_tokens
            return result

        # Stage 2: Cross-review
        for model in self.models:
            other_answers = {m: a for m, a in result.stage1.items() if m != model}
            review_prompt = (
                "Review the following answers and identify strengths and weaknesses:\n\n"
                + "\n\n".join(f"**{m}**: {a}" for m, a in other_answers.items())
            )
            response = client.complete(prompt=review_prompt, model=model)
            result.stage2[model] = response.content
            total_tokens += response.input_tokens + response.output_tokens

        if self.stages < 3:
            result.final_answer = result.stage1.get(self.chair, "")
            result.total_tokens = total_tokens
            return result

        # Stage 3: Chair synthesis
        synthesis_prompt = (
            "As the chair, synthesize the best final answer based on:\n\n"
            "## Original Prompt\n" + prompt + "\n\n"
            "## Answers\n" + "\n".join(f"**{m}**: {a}" for m, a in result.stage1.items()) + "\n\n"
            "## Reviews\n" + "\n".join(f"**{m}**: {r}" for m, r in result.stage2.items()) + "\n\n"
            "Provide the final, synthesized answer:"
        )
        response = client.complete(prompt=synthesis_prompt, model=self.chair)
        result.final_answer = response.content
        total_tokens += response.input_tokens + response.output_tokens

        result.total_tokens = total_tokens
        return result
