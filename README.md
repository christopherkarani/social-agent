# Bluesky Crypto Agent

An AI-powered agent that automatically creates and posts engaging cryptocurrency content to Bluesky social media platform. The agent retrieves the latest crypto news using Perplexity API, generates original viral content, and publishes posts every 30 minutes while running in a Docker container.

## Features

- 🤖 **Automated Content Creation**: AI-powered content generation from latest crypto news
- 📰 **News Integration**: Real-time crypto news retrieval via Perplexity API
- 🚀 **Viral Content Optimization**: Engagement-focused content strategies
- 📱 **Bluesky Integration**: Seamless posting to Bluesky social platform
- ⏰ **Scheduled Posting**: Automated posting every 30 minutes
- 🐳 **Docker Containerized**: Easy deployment and management
- 📊 **Quality Control**: Duplicate detection and content filtering
- 📈 **Monitoring**: Comprehensive logging and health checks

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Perplexity API key
- Bluesky account credentials

### 1. Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd bluesky-crypto-agent

# Run the setup script
./scripts/setup.sh
```

### 2. Configuration

Edit the `.env` file with your credentials:

```bash
# Required API credentials
PERPLEXITY_API_KEY=your_perplexity_api_key_here
BLUESKY_USERNAME=your_bluesky_username_here
BLUESKY_PASSWORD=your_bluesky_password_here

# Optional: Customize behavior
POSTING_INTERVAL_MINUTES=30
CONTENT_THEMES=Bitcoin,Ethereum,DeFi,NFTs,Altcoins
```

### 3. Deploy

```bash
# Deploy the agent
./scripts/deploy.sh

# Check status
./scripts/deploy.sh status

# View logs
./scripts/deploy.sh logs
```

## Project Structure

```
bluesky-crypto-agent/
├── src/
│   ├── agents/
│   │   ├── base_agent.py          # Base agent framework
│   │   └── bluesky_crypto_agent.py # Main crypto agent
│   ├── tools/
│   │   ├── news_retrieval_tool.py  # Perplexity API integration
│   │   ├── content_generation_tool.py # AI content generation
│   │   └── bluesky_social_tool.py  # Bluesky API integration
│   ├── services/
│   │   ├── content_filter.py       # Quality control
│   │   ├── scheduler_service.py    # Automated scheduling
│   │   └── management_api.py       # Configuration API
│   ├── config/
│   │   └── agent_config.py         # Configuration management
│   ├── models/
│   │   └── data_models.py          # Data structures
│   └── utils/
│       ├── logging_config.py       # Logging setup
│       ├── error_handler.py        # Error handling
│       └── helpers.py              # Utility functions
├── tests/                          # Comprehensive test suite
├── scripts/
│   ├── setup.sh                    # Initial setup script
│   └── deploy.sh                   # Deployment script
├── docker-compose.yml              # Container orchestration
├── Dockerfile                      # Container definition
└── .env.example                    # Configuration template
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PERPLEXITY_API_KEY` | Yes | - | Your Perplexity API key |
| `BLUESKY_USERNAME` | Yes | - | Your Bluesky username |
| `BLUESKY_PASSWORD` | Yes | - | Your Bluesky password |
| `POSTING_INTERVAL_MINUTES` | No | 30 | Minutes between posts |
| `MAX_EXECUTION_TIME_MINUTES` | No | 25 | Max execution time per cycle |
| `MAX_POST_LENGTH` | No | 300 | Maximum characters per post |
| `CONTENT_THEMES` | No | Bitcoin,Ethereum,DeFi,NFT,Altcoins | Crypto topics to focus on |
| `MIN_ENGAGEMENT_SCORE` | No | 0.7 | Minimum content quality score |
| `DUPLICATE_THRESHOLD` | No | 0.8 | Similarity threshold for duplicates |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Content Themes

Customize the crypto topics the agent focuses on:

```bash
CONTENT_THEMES=Bitcoin,Ethereum,DeFi,NFTs,Altcoins,Web3,Blockchain,Trading
```

### Quality Control

Fine-tune content quality and filtering:

```bash
MIN_ENGAGEMENT_SCORE=0.7    # Higher = stricter quality
DUPLICATE_THRESHOLD=0.8     # Higher = more duplicate detection
MAX_RETRIES=3              # API retry attempts
```

## Usage

### Deployment Commands

```bash
# Deploy the agent
./scripts/deploy.sh

# Stop the agent
./scripts/deploy.sh stop

# Restart the agent
./scripts/deploy.sh restart

# View real-time logs
./scripts/deploy.sh logs

# Check deployment status
./scripts/deploy.sh status
```

### Docker Commands

```bash
# Manual container management
docker-compose up -d        # Start in background
docker-compose down         # Stop and remove
docker-compose logs -f      # Follow logs
docker-compose ps           # Show status
```

### Monitoring

The agent provides comprehensive monitoring:

- **Health Checks**: Automatic container health monitoring
- **Structured Logging**: JSON-formatted logs with timestamps
- **Performance Metrics**: Execution time and success rates
- **Error Tracking**: Detailed error reporting and recovery

View logs:
```bash
# Real-time logs
./scripts/deploy.sh logs

# Specific log files
tail -f logs/bluesky_agent.log
```

## API Integration

### Perplexity API

The agent uses Perplexity API for news retrieval:

- **Authentication**: API key-based
- **Rate Limiting**: Automatic handling with backoff
- **Content Filtering**: Crypto-specific news filtering
- **Error Handling**: Retry logic with exponential backoff

### Bluesky API

Integration with Bluesky's AT Protocol:

- **Authentication**: Username/password with session management
- **Post Publishing**: Character limit validation and formatting
- **Error Recovery**: Automatic retry for failed posts
- **Rate Limiting**: Respect platform limits

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Run the agent locally
python example_usage.py
```

### Testing

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/test_integration.py
python -m pytest tests/test_bluesky_crypto_agent.py

# Run with coverage
python -m pytest --cov=src tests/
```

### Adding New Features

1. **Tools**: Add new tools in `src/tools/`
2. **Services**: Add services in `src/services/`
3. **Configuration**: Update `src/config/agent_config.py`
4. **Tests**: Add corresponding tests in `tests/`

## Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs
./scripts/deploy.sh logs

# Verify configuration
./scripts/setup.sh validate

# Rebuild image
docker-compose build --no-cache
```

**API authentication errors:**
```bash
# Verify credentials in .env
cat .env | grep -E "(PERPLEXITY|BLUESKY)"

# Test API connectivity
docker-compose exec bluesky-crypto-agent python -c "from src.tools.news_retrieval_tool import NewsRetrievalTool; print('API test')"
```

**Content not posting:**
```bash
# Check content filter logs
./scripts/deploy.sh logs | grep -i "filter\|duplicate"

# Verify Bluesky credentials
./scripts/deploy.sh logs | grep -i "bluesky\|auth"
```

### Performance Issues

**High memory usage:**
```bash
# Check resource usage
docker stats bluesky-crypto-agent

# Adjust memory limits in docker-compose.yml
```

**Slow execution:**
```bash
# Check execution times in logs
./scripts/deploy.sh logs | grep -i "execution\|time"

# Adjust timeout settings
```

### Getting Help

1. **Check Logs**: Always start with `./scripts/deploy.sh logs`
2. **Validate Config**: Run `./scripts/setup.sh validate`
3. **Test Components**: Use individual test files
4. **Check Resources**: Monitor Docker resource usage

## Security

### Best Practices

- **Environment Variables**: Never commit `.env` file
- **API Keys**: Use environment variables only
- **Container Security**: Runs as non-root user
- **Network**: Isolated Docker network
- **Logs**: Sensitive data filtering

### Credential Management

```bash
# Secure .env file permissions
chmod 600 .env

# Use Docker secrets for production
docker secret create perplexity_key perplexity_key.txt
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Run linting
flake8 src/ tests/
black src/ tests/
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review existing issues
3. Create a new issue with:
   - Error logs
   - Configuration (without sensitive data)
   - Steps to reproduce# social-agent
