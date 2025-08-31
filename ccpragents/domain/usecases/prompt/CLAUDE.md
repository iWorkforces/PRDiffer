# CLAUDE.md - Prompt Use Cases

This file provides guidance for working with the prompt use cases in CCPRAgents.

## Overview

This directory contains specialized use cases for AI-powered prompt generation tasks related to pull request analysis. These use cases follow the same Clean Architecture patterns as other domain use cases but focus specifically on prompt engineering and AI interaction.

## Prompt Use Case Components

### Prompt Use Case Pattern
All prompt use cases follow a consistent pattern:

```python
class PromptUseCase:
    def __init__(self, prompt_repository: PromptRepositoryInterface):
        self._prompt_repository = prompt_repository
    
    async def execute(self, pr_details: PRDetails, pr_commit_messages: str, pr_diff: str) -> str:
        request = PromptRequest(
            pr_details=pr_details,
            pr_commit_messages=pr_commit_messages,
            pr_diff=pr_diff
        )
        return await self._prompt_repository.method_name(request)
```

### Available Prompt Use Cases

#### DescribePRUserPromptUseCase (`describe_pr_user_prompt.py`)
Generates user prompts for AI-powered PR description generation.

**Responsibilities:**
- Creates prompt requests for PR description tasks
- Formats PR details, commit messages, and diff content
- Delegates to `PromptRepositoryInterface.describe_pr_user_prompt()`

#### ReviewPRUserPromptUseCase (`review_pr_user_prompt.py`)
Generates user prompts for AI-powered PR code review.

**Responsibilities:**
- Creates prompt requests for PR review tasks
- Formats code review context and change information
- Delegates to `PromptRepositoryInterface.review_pr_user_prompt()`

#### UpdateChangelogUserPromptUseCase (`update_changelog_user_prompt.py`)
Generates user prompts for AI-powered changelog updates.

**Responsibilities:**
- Creates prompt requests for changelog generation tasks
- Formats change information for release notes
- Delegates to `PromptRepositoryInterface.update_changelog_user_prompt()`

#### ApprovePRUserPromptUseCase (`approve_pr_user_prompt.py`)
Generates user prompts for AI-powered PR approval decisions.

**Responsibilities:**
- Creates prompt requests for PR approval tasks
- Formats approval criteria and evaluation framework
- Delegates to `PromptRepositoryInterface.approve_pr_user_prompt()`

#### DescribePRSystemPromptUseCase (`describe_pr_system_prompt.py`)
Generates system prompts for PR description tasks.

**Responsibilities:**
- Creates system-level prompts for AI context
- Defines role and behavior for the AI assistant
- Delegates to `PromptRepositoryInterface.describe_pr_system_prompt()`

#### ReviewPRSystemPromptUseCase (`review_pr_system_prompt.py`)
Generates system prompts for PR code review tasks.

**Responsibilities:**
- Creates system-level prompts for code review context
- Defines code review guidelines and quality standards
- Delegates to `PromptRepositoryInterface.review_pr_system_prompt()`

#### UpdateChangelogSystemPromptUseCase (`update_changelog_system_prompt.py`)
Generates system prompts for changelog generation tasks.

**Responsibilities:**
- Creates system-level prompts for changelog context
- Defines changelog conventions and formatting rules
- Delegates to `PromptRepositoryInterface.update_changelog_system_prompt()`

#### ApprovePRSystemPromptUseCase (`approve_pr_system_prompt.py`)
Generates system prompts for PR approval tasks.

**Responsibilities:**
- Creates system-level prompts for approval context
- Defines approval criteria and decision framework
- Delegates to `PromptRepositoryInterface.approve_pr_system_prompt()`

## Architecture Patterns

### Prompt Request Pattern
All prompt use cases use the `PromptRequest` data structure:

```python
PromptRequest(
    pr_details=PRDetails(repo_owner, repo_name, pr_number),
    pr_commit_messages=str,  # Concatenated commit messages
    pr_diff=str             # Unified diff content
)
```

### Repository Delegation Pattern
Use cases delegate actual prompt generation to the repository layer:
- **Separation of concerns**: Use cases handle orchestration, repositories handle AI interaction
- **Testability**: Easy to mock repository responses
- **Flexibility**: Can switch AI providers without changing use cases

### Async/Await Pattern
All operations are asynchronous to handle:
- Network latency in AI API calls
- Potentially long-running prompt generation
- Concurrent prompt processing

## Integration with Other Layers

### Domain Layer Integration
- **Entities**: Uses `PRDetails` and `PromptRequest` domain entities
- **Repository Interfaces**: Depends on `PromptRepositoryInterface`
- **Consistent patterns**: Follows same patterns as other domain use cases

### Application Layer Usage
Application layer creates and executes prompt use cases:

```python
# In MCP server or application service
prompt_repository = get_prompt_repository()
describer = DescribePRUserPromptUseCase(prompt_repository)

# Execute with PR context
prompt = await describer.execute(pr_details, commit_messages, diff_content)
```

### Infrastructure Layer Implementation
- **PromptRepository**: Concrete implementation handles AI API calls
- **String Integration**: Returns plain strings for prompt content
- **Error Handling**: Infrastructure handles AI provider errors and rate limiting

## Development Guidelines

### Adding New Prompt Use Cases
1. **Identify prompt need**: Define the specific AI task requirement
2. **Create use case class**: Follow the established pattern
3. **Add repository method**: Extend `PromptRepositoryInterface` if needed
4. **Update __init__.py**: Export the new use case
5. **Write tests**: Unit tests with mocked repository responses

### Prompt Engineering Considerations
- **Context formatting**: Ensure PR details, commits, and diffs are properly formatted
- **Token limits**: Be aware of AI model token limitations
- **Prompt clarity**: Design prompts for clear AI understanding
- **Consistency**: Maintain consistent prompt patterns across use cases

### Testing Strategies

#### Unit Testing
```python
async def test_describe_pr_user_prompt():
    mock_repo = Mock(spec=PromptRepositoryInterface)
    mock_repo.describe_pr_user_prompt.return_value = "test prompt"
    
    use_case = DescribePRUserPromptUseCase(mock_repo)
    pr_details = PRDetails("owner", "repo", 123)
    
    result = await use_case.execute(pr_details, "commit msg", "diff content")
    
    assert isinstance(result, str)
    mock_repo.describe_pr_user_prompt.assert_called_once()
```

#### Integration Testing
Test with real repository implementation to verify:
- Prompt request formatting
- AI API integration
- Error handling
- Response processing

## Performance Considerations

### Caching Strategies
- **Prompt caching**: Cache frequently used prompt templates
- **Response caching**: Cache AI responses for identical inputs
- **Token optimization**: Minimize prompt size to reduce API costs

### Rate Limiting
- **AI API limits**: Respect provider rate limits
- **Batch processing**: Process multiple prompts efficiently
- **Retry logic**: Handle transient AI API failures

### Resource Management
- **Connection pooling**: Reuse AI API connections
- **Timeout handling**: Set appropriate timeouts for AI calls
- **Error recovery**: Graceful degradation when AI services are unavailable

## File Organization

```
ccpragents/domain/usecases/prompt/
├── __init__.py                 # Public API exports
├── describe_pr_user_prompt.py  # PR description prompts
├── review_pr_user_prompt.py    # Code review prompts
├── update_changelog_user_prompt.py  # Changelog prompts
├── approve_pr_user_prompt.py   # PR approval prompts
├── describe_pr_system_prompt.py # System role prompts
├── review_pr_system_prompt.py  # Code review system prompts
├── update_changelog_system_prompt.py  # Changelog system prompts
└── approve_pr_system_prompt.py  # PR approval system prompts
```

## Best Practices

### Prompt Design
- **Clear objectives**: Each use case should have a single, clear purpose
- **Consistent formatting**: Use consistent prompt structures across use cases
- **Context inclusion**: Provide sufficient context for accurate AI responses
- **Output formatting**: Specify desired output format in prompts

### Error Handling
- **Graceful degradation**: Handle AI service failures gracefully
- **Fallback strategies**: Provide fallback content when AI is unavailable
- **Error logging**: Log AI API errors for monitoring and debugging

### Security Considerations
- **Data sanitization**: Ensure no sensitive data is sent to AI services
- **API key management**: Properly manage AI service credentials
- **Privacy compliance**: Follow data privacy regulations for AI processing

This prompt use case layer provides a structured approach to AI-powered PR analysis tasks, enabling consistent prompt engineering, easy testing, and flexible AI provider integration.