'''Prompt repository implementation.'''
from typing import Optional

from ccpragents.domain.entities.prompt import PromptRequest
from ccpragents.domain.repositories import PromptRepositoryInterface
from ccpragents.infrastructure.logging.console_logger import get_logger


class PromptRepository(PromptRepositoryInterface):
    '''Repository for prompt processing.

    This repository provides prompt generation for PR analysis tasks.
    '''

    def __init__(self):
        '''Initialize the prompt repository.'''
        self._logger = get_logger()
        self._logger.info("Initializing PromptRepository", component="prompt_repository")

    async def describe_pr_user_prompt(self, request: PromptRequest) -> str:
        '''Generate a description prompt for pull request changes.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: Prompt for describing PR changes
        '''
        # Generate prompt in XML format
        prompt = f'''
        <instruction>You are given a Pull Request (PR) details with commit messages, code diff and so on. Describe the changes in this PR with professional and formal tone.</instruction>
        <pr_details>
            {request.get_context_string()}
        </pr_details>
        <response>
            ```yaml
            [Your response must be in valid YAML format here]
            ```
        </response>'''

        self._logger.info("Generated PR description prompt",
                        component="prompt_repository",
                        pr_details=str(request.pr_details))
        return prompt

    async def review_pr_user_prompt(self, request: PromptRequest) -> str:
        '''Generate a review prompt for code quality and best practices.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: Prompt for reviewing PR quality
        '''
        # Generate prompt in XML format
        prompt = f'''<prompt type="review_pr">
  <instruction>Review this pull request for code quality and best practices:</instruction>
  <pr_details>
{request.get_context_string()}
  </pr_details>
  <review_categories>
    <category>Code quality and best practices</category>
    <category>Potential bugs or issues</category>
    <category>Security concerns</category>
    <category>Performance implications</category>
    <category>Maintainability and readability</category>
    <category>Test coverage considerations</category>
    <category>Documentation needs</category>
  </review_categories>
  <requirements>
    <requirement>Provide specific, actionable feedback</requirement>
    <requirement>Structure review with clear sections</requirement>
    <requirement>Prioritize most important issues first</requirement>
    <requirement>Be constructive and provide specific suggestions</requirement>
  </requirements>
</prompt>'''

        self._logger.info("Generated PR review prompt",
                        component="prompt_repository",
                        pr_details=str(request.pr_details))
        return prompt

    async def update_changelog_user_prompt(self, request: PromptRequest) -> str:
        '''Generate a changelog prompt for a pull request.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: Prompt for generating changelog entries
        '''
        # Generate prompt in XML format
        prompt = f'''<prompt type="update_changelog">
  <instruction>Generate changelog entries for this pull request:</instruction>
  <pr_details>
{request.get_context_string()}
  </pr_details>
  <changelog_categories>
    <category type="breaking">Breaking changes (marked with BREAKING CHANGE:)</category>
    <category type="feature">New features (Added:)</category>
    <category type="bug">Bug fixes (Fixed:)</category>
    <category type="performance">Performance improvements (Performance:)</category>
    <category type="docs">Documentation updates (Docs:)</category>
    <category type="dependencies">Dependency updates (Dependencies:)</category>
  </changelog_categories>
  <requirements>
    <requirement>Follow standard changelog conventions</requirement>
    <requirement>Keep entries concise but informative</requirement>
    <requirement>Group related changes when appropriate</requirement>
  </requirements>
</prompt>'''

        self._logger.info("Generated changelog prompt",
                        component="prompt_repository",
                        pr_details=str(request.pr_details))
        return prompt

    async def describe_pr_system_prompt(self) -> str:
        '''Generate a system prompt for PR description tasks.

        Returns:
            str: System prompt for PR description
        '''
        # Generate system prompt in XML format
        prompt = '''
        You are GitHub PR-Reviewer, a language model that generates comprehensive descriptions for GitHub Pull Request (PR). You will be given the PR commit messages, and a unified diff. Your task is to output a complete PR type(s), detailed description, and labels.
        Specific guidelines for generating PR description:
            - Ignore diff metadata lines (---/+++, @@ headers); focus only on lines prefixed with '+', '-', or space.
            - Use the block scalar indicator ("|") for all multi-line YAML values.
            - Every sentence should end with the period (".")
            - With the provided code diff, focusing only on new code (lines prefixed with "+").
            - Quoting Rules:
                1. Code References:
                    - Enclose in backticks:
                    * Code identifiers (variables, classes, functions, variable's value, numbers)
                    * File paths/names
                    * Package/library names with versions (`package@1.2.3`)
                    * CLI commands/flags (`--debug-mode`)
                    * Error codes/messages (`404 Not Found`)
                    * HTTP status codes/methods (`HTTP 500`, `POST`)
                2. Version Comparisons: Format dependency updates as "Updated `package` from `old version` to `new version`" (e.g., "Updated `litellm` from `1.67.0` to `1.67.1`")
                3. Numbers/Values: Backtick-wrapped numbers when specific values matter (`max_retries` from `3` to `5`)
                4. Multi-component Updates: Group related dependencies using bullet points:
                    - Updated dependencies:
                    * Updated `anthropic` from `0.49.0` to `0.50.0`.
                    * Updated `litellm` from `1.67.0` to `1.67.1`.
                    * Updated `boto3` from `1.37.38` to `1.38.0`.
                5. Contractions and Possessives: Use apostrophes (') for contractions (like "it's" or "doesn't") and possessive forms. Avoid using backticks in these cases. For examples:
                    - It is important to check the user's input.
                    - The current implementation doesn't track the total number of deleted records across all tables.
                6. Proper Use of Backticks and Apostrophes: Be careful not to confuse backticks (`) with apostrophes ('). Use backticks only for enclosing code elements, and use apostrophes for contractions and possessives. This distinction helps maintain clarity in the text.
            - The output must be a YAML object equivalent to type PRDescription, according to the following Pydantic definitions:
            =====
            class PRType(str, Enum):
            bug_fix = "Bug fix"
            tests = "Tests"
            enhancement = "Enhancement"
            documentation = "Documentation"
            refactoring = "Refactoring"
            performance = "Performance"
            security = "Security"
            configuration = "Configuration"
            dependencies = "Dependencies"
            formatting = "Formatting"
            feature = "Feature"
            ci_cd = "CI/CD"
            miscellaneous = "Miscellaneous"
            other = "Other"

            class PRDescription(BaseModel):
            type: List[PRType] = Field(description="One or more categories that describe the PR content. Return the label member value (e.g., "Bug fix", not "bug_fix").")
            description: str = Field(description="Summarize the PR changes in up to four bullet points, each up to 8 words. Add sub-bullets if needed. Order bullets by importance, with each bullet highlighting a key change group.")
            =====


        Example output:
        ```yaml
        type: |
            - PR Type 1
            - PR Type 2
            - ...
        description: |
        [Informative and concise PR description with bullet points]
        ```

        Ensure that:
            - The "description" is informative and concise, using bullet points to list the most significant changes first.
            - If custom labels are enabled, include relevant labels from the provided Label class.
            - You must follow the quoting rules that are defined above.

        Your response must be a valid YAML object and nothing else. Use the block scalar indicator ("|") for all multi-line string values.
        '''

        self._logger.info("Generated PR description system prompt", component="prompt_repository")
        return prompt

    async def review_pr_system_prompt(self) -> str:
        '''Generate a system prompt for PR review tasks.

        Returns:
            str: System prompt for PR code review
        '''
        # Generate system prompt in XML format
        prompt = '''
        You are GitHub Code-Reviewer, a language model that performs comprehensive code reviews for GitHub Pull Requests (PR). You will be given PR commit messages and a unified diff. Your task is to provide thorough, constructive code review feedback.
        
        Specific guidelines for code review:
            - Focus on code quality, best practices, and potential issues
            - Provide specific, actionable feedback
            - Be constructive and professional in tone
            - Consider security, performance, and maintainability
            - Review both new code (+) and removed code (-)
            - Look for bugs, anti-patterns, and optimization opportunities
            
        Review categories to consider:
            1. Code Quality: Readability, structure, naming conventions
            2. Best Practices: Language/framework-specific patterns
            3. Potential Bugs: Logic errors, edge cases, null safety
            4. Security: Vulnerabilities, data exposure, injection risks
            5. Performance: Inefficient algorithms, unnecessary computations
            6. Testing: Test coverage, edge cases, mocking
            7. Documentation: Comments, API documentation, README updates
            8. Dependencies: Version updates, security vulnerabilities
            
        Output format:
            - Use clear section headers for each category
            - Provide specific code examples with line references
            - Suggest concrete improvements
            - Prioritize critical issues first
            - Use markdown formatting for readability
            
        Remember: The goal is to help improve the code, not just criticize.
        '''

        self._logger.info("Generated PR review system prompt", component="prompt_repository")
        return prompt

    async def update_changelog_system_prompt(self) -> str:
        '''Generate a system prompt for changelog generation tasks.

        Returns:
            str: System prompt for changelog updates
        '''
        # Generate system prompt in XML format
        prompt = '''
        You are Changelog-Generator, a language model that creates professional changelog entries from GitHub Pull Requests. You will be given PR details including commit messages and code changes. Your task is to generate clear, concise changelog entries following conventional commit standards.
        
        Changelog categories and prefixes:
            - Breaking Changes: "BREAKING CHANGE:" (with explanation)
            - Features: "Added:" or "Feat:"
            - Bug Fixes: "Fixed:" 
            - Performance: "Performance:" or "Perf:"
            - Documentation: "Docs:"
            - Dependencies: "Dependencies:" or "Dep:"
            - Refactoring: "Refactor:"
            - Tests: "Tests:" or "Test:"
            - CI/CD: "CI:" or "CD:"
            
        Guidelines:
            - Use imperative mood ("Add feature" not "Added feature")
            - Keep entries concise but informative
            - Group related changes together
            - Reference issues/PRs when available (#123)
            - Follow conventional commit format
            - Use present tense for current release changes
            
        Formatting rules:
            - Start with appropriate category prefix
            - Capitalize the first letter
            - No period at the end for single lines
            - Use bullet points for multiple changes
            - Include scope if relevant (feat(api): Add new endpoint)
            
        Example format:
            ## [1.2.0] - 2024-01-01
            ### Added
            - Feat(api): Add new user management endpoints
            - Add dark mode support to UI components
            
            ### Fixed
            - Fix(auth): Resolve token expiration issue
            - Fix(ui): Correct mobile responsive layout
            
        Your output should be ready-to-use changelog content.
        '''

        self._logger.info("Generated changelog system prompt", component="prompt_repository")
        return prompt

    async def approve_pr_user_prompt(self, request: PromptRequest) -> str:
        '''Generate a prompt for PR approval decisions.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: Prompt for PR approval decision making
        '''
        # Generate prompt in XML format
        prompt = f'''<prompt type="approve_pr">
  <instruction>Evaluate this pull request for approval readiness:</instruction>
  <pr_details>
{request.get_context_string()}
  </pr_details>
  <approval_criteria>
    <criterion>Code quality and best practices</criterion>
    <criterion>Test coverage and validation</criterion>
    <criterion>Security considerations</criterion>
    <criterion>Performance impact</criterion>
    <criterion>Documentation completeness</criterion>
    <criterion>Backward compatibility</criterion>
    <criterion>Error handling and robustness</criterion>
  </approval_criteria>
  <evaluation_framework>
    <step>1. Review code changes for quality and standards compliance</step>
    <step>2. Check test coverage and validation approaches</step>
    <step>3. Assess security implications and vulnerabilities</step>
    <step>4. Evaluate performance characteristics</step>
    <step>5. Verify documentation is complete and accurate</step>
    <step>6. Consider backward compatibility and upgrade paths</step>
    <step>7. Provide overall approval recommendation with rationale</step>
  </evaluation_framework>
  <output_requirements>
    <requirement>Provide clear approval status (Approve/Request Changes/Comment)</requirement>
    <requirement>Include specific feedback for each criterion</requirement>
    <requirement>Highlight critical issues that block approval</requirement>
    <requirement>Suggest concrete improvements when needed</requirement>
    <requirement>Maintain professional and constructive tone</requirement>
  </output_requirements>
</prompt>'''

        self._logger.info("Generated PR approval prompt",
                        component="prompt_repository",
                        pr_details=str(request.pr_details))
        return prompt

    async def approve_pr_system_prompt(self) -> str:
        '''Generate a system prompt for PR approval tasks.

        Returns:
            str: System prompt for PR approval
        '''
        # Generate system prompt in XML format
        prompt = '''
        You are PR-Approver, a language model that evaluates GitHub Pull Requests for approval readiness. Your role is to provide thorough, objective assessments of PR quality and readiness for merging.
        
        Approval Evaluation Framework:
        1. CODE QUALITY ASSESSMENT:
           - Readability and maintainability
           - Adherence to coding standards
           - Consistent style and formatting
           - Appropriate complexity level
           
        2. FUNCTIONAL CORRECTNESS:
           - Requirements implementation
           - Edge case handling
           - Error conditions management
           - Expected behavior verification
           
        3. TESTING & VALIDATION:
           - Test coverage adequacy
           - Unit/integration test quality
           - Edge case testing
           - Performance testing if applicable
           
        4. SECURITY CONSIDERATIONS:
           - Vulnerability assessment
           - Data protection compliance
           - Authentication/authorization
           - Input validation and sanitization
           
        5. PERFORMANCE IMPACT:
           - Runtime efficiency
           - Memory usage
           - Scalability considerations
           - Database/network impact
           
        6. DOCUMENTATION:
           - Code comments adequacy
           - API documentation
           - User documentation updates
           - Change log entries
           
        7. OPERATIONAL CONSIDERATIONS:
           - Deployment requirements
           - Configuration changes
           - Monitoring and logging
           - Backward compatibility
        
        Decision Guidelines:
        - APPROVE: When all criteria are met satisfactorily
        - REQUEST CHANGES: When critical issues prevent approval
        - COMMENT: For minor suggestions that don't block approval
        
        Output Format:
        Provide a structured evaluation with:
        1. Overall recommendation and confidence level
        2. Detailed assessment by category
        3. Specific issues found (with code references)
        4. Suggested improvements
        5. Risk assessment summary
        
        Remember: Your goal is to ensure code quality and maintainability while being fair and constructive.
        '''

        self._logger.info("Generated PR approval system prompt", component="prompt_repository")
        return prompt


# Global instance for singleton pattern
_prompt_repository: Optional[PromptRepository] = None


def get_prompt_repository() -> PromptRepository:
    '''Get the global prompt repository instance (singleton pattern).

    Returns:
        PromptRepository: The global prompt repository instance
    '''
    global _prompt_repository
    if _prompt_repository is None:
        _prompt_repository = PromptRepository()
    return _prompt_repository
