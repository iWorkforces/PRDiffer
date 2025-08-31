from pydantic import BaseModel


class PRDetails(BaseModel):
    """Domain entity representing PR identification details.

    This entity encapsulates the basic information needed to identify a PR
    for prompt processing, following the Clean Architecture pattern.
    """
    repo_owner: str
    repo_name: str
    pr_number: int

    def __str__(self) -> str:
        return f"{self.repo_owner}/{self.repo_name}#{self.pr_number}"


class PromptRequest(BaseModel):
    """Domain entity representing a prompt processing request.

    Contains all the information needed for AI-powered prompt processing,
    including PR details and relevant content.
    """
    pr_details: PRDetails
    pr_commit_messages: str
    pr_diff: str

    def get_context_string(self) -> str:
        """Generate a unified context string combining all relevant information in XML format."""
        return f"""<pull_request>
  <repository>
    <owner>{self.pr_details.repo_owner}</owner>
    <name>{self.pr_details.repo_name}</name>
    <pr_number>{self.pr_details.pr_number}</pr_number>
  </repository>
  <commit_messages>
{self._format_xml_content(self.pr_commit_messages)}
  </commit_messages>
  <diff_content>
{self._format_xml_content(self.pr_diff)}
  </diff_content>
</pull_request>"""

    def _format_xml_content(self, content: str) -> str:
        """Format content for XML by escaping special characters and indenting."""
        # Escape XML special characters
        escaped = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        escaped = escaped.replace('"', '&quot;').replace("'", '&apos;')

        # Split into lines and indent each line
        lines = escaped.split('\n')
        indented_lines = [f'    {line}' for line in lines]
        return '\n'.join(indented_lines)
