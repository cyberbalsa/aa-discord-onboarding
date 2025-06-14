# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-14

### Added
- Initial release of AA Discord Onboarding plugin
- Automatic Discord DM sending when users join the server
- EVE Online SSO integration for user authentication
- `/auth` slash command for self-service authentication
- `/auth-user` admin command to send authentication links to specific users
- Secure token-based authentication with automatic expiration
- Integration with Alliance Auth Discord service for role/nickname sync
- Admin interface for token management
- Automatic cleanup of expired tokens via Celery tasks
- Comprehensive test suite
- Django management commands for token cleanup
- Multi-language support ready

### Features
- **Simple Onboarding**: One-click authentication process for new Discord users
- **Admin Controls**: Role-based permissions for admin commands
- **Security**: Secure token generation with configurable expiration
- **Integration**: Seamless integration with existing Alliance Auth infrastructure
- **Automation**: Automatic role and nickname synchronization
- **Monitoring**: Comprehensive logging and admin interface

### Technical Details
- Python 3.8+ support
- Django 4.0+ compatibility
- Alliance Auth 3.0+ integration
- AA-DiscordBot 2.0+ compatibility
- Production-ready with proper error handling
- Clean, linted code following Python/Django best practices

[1.0.0]: https://github.com/cyberbalsa/aa-discord-onboarding/releases/tag/v1.0.0