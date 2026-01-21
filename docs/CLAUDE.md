# CLAUDE.md - Documentation Directory

This file provides guidance for working with the documentation in PRDiffer.

**Current Version:** 0.4.8

## Documentation Overview

The `docs/` directory is intended for project documentation, user guides, API references, and other documentation artifacts.

## Documentation Structure

### Recommended Structure
```
docs/
├── CLAUDE.md                  # This file - documentation guidance
├── README.md                  # Main documentation overview
├── API.md                     # API reference documentation
├── USER_GUIDE.md              # User guide and tutorials
├── DEVELOPMENT.md             # Development setup and guidelines
├── ARCHITECTURE.md            # System architecture overview
├── DEPLOYMENT.md              # Deployment instructions
└── images/                    # Documentation images and diagrams
    ├── architecture.png
    ├── workflow.png
    └── sequence-diagrams/
```

## Documentation Types

### User Documentation
- **Getting Started**: Quick start guide for new users
- **Installation**: Step-by-step installation instructions
- **Configuration**: How to configure the application
- **Usage Examples**: Practical examples of common use cases
- **Troubleshooting**: Common issues and solutions

### Developer Documentation
- **API Reference**: Complete API documentation with examples
- **Architecture**: System design and component relationships
- **Development Setup**: Local development environment setup
- **Testing**: Testing strategy and how to run tests
- **Contributing**: Guidelines for contributing to the project

### Operational Documentation
- **Deployment**: Production deployment instructions
- **Monitoring**: How to monitor the application
- **Scaling**: Scaling considerations and best practices
- **Security**: Security considerations and hardening

## Security Documentation (NEW in Sprint 1)

### SecurityUsageGuide.md

A comprehensive security guide has been added to document authentication, input validation, and secure deployment practices:

**Topics Covered:**
- API key authentication setup and configuration
- SHA-256 hashed token storage
- Per-client rate limiting
- Client connection examples (Python, TypeScript, cURL)
- Security best practices and troubleshooting
- nginx configuration for security headers

**Key Sections:**
```markdown
# SecurityUsageGuide.md

## Authentication Setup
- Admin vs. regular API keys
- Token generation and hashing
- Configuration in settings.toml

## Client Connection Examples
- Python: Using MCP client with authentication
- TypeScript: Using FastMCP client
- cURL: Testing authentication endpoint

## Security Headers
- Content-Security-Policy (CSP)
- X-Frame-Options
- X-Content-Type-Options
- nginx configuration examples

## Troubleshooting
- Authentication failures
- Rate limiting issues
- Token validation problems
```

**Integration with CLAUDE.md:**

- The root `prdiffer/CLAUDE.md` references `SecurityUsageGuide.md`
- Application layer documentation links to authentication patterns
- Infrastructure security documentation validates against the guide

## Documentation Standards

### Markdown Formatting
- Use GitHub-flavored Markdown
- Include proper headers and table of contents
- Use code blocks with language specification
- Include examples and practical usage

### Images and Diagrams
- Store images in `images/` subdirectory
- Use descriptive filenames
- Include alt text for accessibility
- Consider using Mermaid.js for diagrams

### Code Examples
- Use proper code fencing with language tags
- Include complete, runnable examples when possible
- Show both input and expected output
- Document any prerequisites or setup needed

## Documentation Generation

### Automated Documentation
Consider using tools like:
- **MkDocs**: For static site generation
- **Sphinx**: For Python API documentation
- **Swagger/OpenAPI**: For REST API documentation
- **Docusaurus**: For comprehensive documentation sites

### API Documentation
For MCP server API documentation:
- Document all available tools and functions
- Include parameter descriptions and types
- Provide example requests and responses
- Document error conditions and responses

## Maintenance Guidelines

### Keeping Documentation Current
- Update documentation when code changes
- Include documentation in code review process
- Use documentation as part of acceptance criteria
- Regularly review and prune outdated content

### Versioning Documentation
- Keep documentation in sync with code versions
- Consider using versioned documentation for releases
- Maintain changelog for documentation updates

## Best Practices

### Writing Effective Documentation
- **Clarity**: Write clearly and concisely
- **Completeness**: Cover all important aspects
- **Examples**: Include practical examples
- **Organization**: Use logical structure and navigation
- **Accessibility**: Ensure documentation is accessible to all users

### Documentation Review
- Peer review documentation changes
- Test documentation instructions actually work
- Get feedback from actual users
- Continuously improve based on feedback

This documentation directory provides a centralized location for all project documentation, making it easy for users, developers, and operators to find the information they need.