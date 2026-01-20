from pydantic import BaseModel, Field


class PRDiff(BaseModel):
    """Domain entity representing a pull request diff content.

    This entity contains the essential diff content for PR analysis.
    Simplified to provide only the diff content field.
    """

    diff_content: str = Field(
        default="", description="Combined diff content for all files"
    )

    @property
    def has_content(self) -> bool:
        """Check if the PR diff has any content.

        Returns:
            bool: True if there is diff content
        """
        return bool(self.diff_content and self.diff_content.strip())
