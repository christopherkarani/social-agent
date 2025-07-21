# Environment Variables Documentation

This document provides comprehensive documentation for all environment variables used by the Bluesky Crypto Agent.

## Required Variables

These variables must be set for the agent to function properly.

### API Credentials

#### `PERPLEXITY_API_KEY`
- **Type**: String
- **Required**: Yes
- **Description**: Your Perplexity API key for news retrieval
- **Example**: `pplx-1234567890abcdef1234567890abcdef`
- **How to get**: Sign up at [Perplexity API](https://docs.perplexity.ai/) and generate an API key
- **Security**: Keep this secret, never commit to version control

#### `BLUESKY_USERNAME`
- **Type**: String
- **Required**: Yes
- **Description**: Your Bluesky username or handle
- **Example**: `myusername.bsky.social` or `myusername`
- **Format**: Can be with or without the `.bsky.social` suffix
- **Security**: This is your public username, but keep it secure

#### `BLUESKY_PASSWORD`
- **Type**: String
- **Required**: Yes
- **Description**: Your Bluesky account password
- **Example**: `my_secure_password_123`
- **Security**: Keep this secret, never commit to version control
- **Note**: Consider using app-specific passwords if available

## Optional Configuration Variables

These variables have default values but can be customized.

### Scheduling Configuration

#### `POSTING_INTERVAL_MINUTES`
- **Type**: Integer
- **Required**: No
- **Default**: `30`
- **Description**: Minutes between automated posts
- **Range**: 5-1440 (5 minutes to 24 hours)
- **Example**: `30`
- **Note**: Too frequent posting may hit rate limits

#### `MAX_EXECUTION_TIME_MINUTES`
- **Type**: Integer
- **Required**: No
- **Default**: `25`
- **Description**: Maximum time allowed for each execution cycle
- **Range**: 5-60 minutes
- **Example**: `25`
- **Note**: Should be less than `POSTING_INTERVAL_MINUTES`

### Content Configuration

#### `MAX_POST_LENGTH`
- **Type**: Integer
- **Required**: No
- **Default**: `300`
- **Description**: Maximum characters per post
- **Range**: 50-300 (Bluesky limit is 300)
- **Example**: `280`
- **Note**: Bluesky's character limit is 300

#### `CONTENT_THEMES`
- **Type**: Comma-separated string
- **Required**: No
- **Default**: `Bitcoin,Ethereum,DeFi,NFT,Altcoins`
- **Description**: Cryptocurrency topics to focus on
- **Example**: `Bitcoin,Ethereum,DeFi,NFTs,Web3,Blockchain,Trading,Altcoins`
- **Available themes**: 
  - `Bitcoin` - Bitcoin-related news
  - `Ethereum` - Ethereum ecosystem
  - `DeFi` - Decentralized Finance
  - `NFT` or `NFTs` - Non-Fungible Tokens
  - `Altcoins` - Alternative cryptocurrencies
  - `Web3` - Web3 and blockchain technology
  - `Trading` - Crypto trading and markets
  - `Blockchain` - Blockchain technology
  - `Regulation` - Crypto regulations
  - `Mining` - Cryptocurrency mining

### Quality Control

#### `MIN_ENGAGEMENT_SCORE`
- **Type**: Float
- **Required**: No
- **Default**: `0.7`
- **Description**: Minimum content quality score (0.0-1.0)
- **Range**: 0.0-1.0
- **Example**: `0.8`
- **Note**: Higher values = stricter quality control

#### `DUPLICATE_THRESHOLD`
- **Type**: Float
- **Required**: No
- **Default**: `0.8`
- **Description**: Similarity threshold for duplicate detection (0.0-1.0)
- **Range**: 0.0-1.0
- **Example**: `0.85`
- **Note**: Higher values = more sensitive duplicate detection

#### `MAX_RETRIES`
- **Type**: Integer
- **Required**: No
- **Default**: `3`
- **Description**: Maximum retry attempts for failed API calls
- **Range**: 1-10
- **Example**: `3`
- **Note**: Higher values increase resilience but may delay execution

### Logging Configuration

#### `LOG_LEVEL`
- **Type**: String
- **Required**: No
- **Default**: `INFO`
- **Description**: Logging verbosity level
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Example**: `DEBUG`
- **Note**: `DEBUG` provides most detail, `ERROR` provides least

#### `LOG_FORMAT`
- **Type**: String
- **Required**: No
- **Default**: `json`
- **Description**: Log output format
- **Options**: `json`, `text`
- **Example**: `json`
- **Note**: JSON format is better for log aggregation

#### `LOG_FILE_PATH`
- **Type**: String
- **Required**: No
- **Default**: `logs/bluesky_agent.log`
- **Description**: Path to log file
- **Example**: `logs/agent.log`
- **Note**: Directory must exist and be writable

### Docker Configuration

#### `CONTAINER_NAME`
- **Type**: String
- **Required**: No
- **Default**: `bluesky-crypto-agent`
- **Description**: Name for the Docker container
- **Example**: `my-crypto-agent`
- **Note**: Used in docker-compose.yml

#### `RESTART_POLICY`
- **Type**: String
- **Required**: No
- **Default**: `unless-stopped`
- **Description**: Docker container restart policy
- **Options**: `no`, `always`, `unless-stopped`, `on-failure`
- **Example**: `always`
- **Note**: `unless-stopped` is recommended for production

## Advanced Configuration

### Performance Tuning

#### `CONTENT_HISTORY_SIZE`
- **Type**: Integer
- **Required**: No
- **Default**: `50`
- **Description**: Number of recent posts to keep for duplicate detection
- **Range**: 10-200
- **Example**: `100`
- **Note**: Higher values use more memory but better duplicate detection

#### `API_TIMEOUT_SECONDS`
- **Type**: Integer
- **Required**: No
- **Default**: `30`
- **Description**: Timeout for API requests in seconds
- **Range**: 10-120
- **Example**: `45`
- **Note**: Increase for slow network connections

#### `RATE_LIMIT_DELAY`
- **Type**: Float
- **Required**: No
- **Default**: `1.0`
- **Description**: Delay between API calls in seconds
- **Range**: 0.1-10.0
- **Example**: `2.0`
- **Note**: Increase to be more respectful of API rate limits

### Content Generation

#### `CONTENT_TEMPERATURE`
- **Type**: Float
- **Required**: No
- **Default**: `0.7`
- **Description**: AI creativity level (0.0-1.0)
- **Range**: 0.0-1.0
- **Example**: `0.8`
- **Note**: Higher values = more creative but less predictable

#### `HASHTAG_COUNT`
- **Type**: Integer
- **Required**: No
- **Default**: `3`
- **Description**: Maximum number of hashtags per post
- **Range**: 0-10
- **Example**: `5`
- **Note**: Too many hashtags may look spammy

## Environment File Examples

### Minimal Configuration (.env)

```bash
# Required - Replace with your actual values
PERPLEXITY_API_KEY=pplx-your-api-key-here
BLUESKY_USERNAME=your-username.bsky.social
BLUESKY_PASSWORD=your-secure-password

# Optional - Uncomment and modify as needed
# POSTING_INTERVAL_MINUTES=30
# LOG_LEVEL=INFO
```

### Development Configuration (.env.dev)

```bash
# API Credentials
PERPLEXITY_API_KEY=pplx-dev-api-key
BLUESKY_USERNAME=testuser.bsky.social
BLUESKY_PASSWORD=dev-password

# Development Settings
POSTING_INTERVAL_MINUTES=60
MAX_EXECUTION_TIME_MINUTES=55
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Content Settings
CONTENT_THEMES=Bitcoin,Ethereum,DeFi
MIN_ENGAGEMENT_SCORE=0.5
DUPLICATE_THRESHOLD=0.7

# Performance
MAX_RETRIES=2
API_TIMEOUT_SECONDS=45
```

### Production Configuration (.env.prod)

```bash
# API Credentials (use secure values)
PERPLEXITY_API_KEY=pplx-prod-api-key
BLUESKY_USERNAME=produser.bsky.social
BLUESKY_PASSWORD=secure-production-password

# Production Settings
POSTING_INTERVAL_MINUTES=30
MAX_EXECUTION_TIME_MINUTES=25
LOG_LEVEL=INFO
LOG_FORMAT=json

# Content Settings
CONTENT_THEMES=Bitcoin,Ethereum,DeFi,NFTs,Altcoins,Web3,Trading
MIN_ENGAGEMENT_SCORE=0.8
DUPLICATE_THRESHOLD=0.85

# Quality Control
MAX_RETRIES=3
CONTENT_HISTORY_SIZE=100

# Performance
API_TIMEOUT_SECONDS=30
RATE_LIMIT_DELAY=1.5
```

### High-Frequency Configuration (.env.highfreq)

```bash
# API Credentials
PERPLEXITY_API_KEY=pplx-your-api-key
BLUESKY_USERNAME=your-username.bsky.social
BLUESKY_PASSWORD=your-password

# High-frequency posting (every 15 minutes)
POSTING_INTERVAL_MINUTES=15
MAX_EXECUTION_TIME_MINUTES=12

# Broader content themes for more variety
CONTENT_THEMES=Bitcoin,Ethereum,DeFi,NFTs,Altcoins,Web3,Blockchain,Trading,Regulation,Mining

# Stricter quality control for frequent posting
MIN_ENGAGEMENT_SCORE=0.8
DUPLICATE_THRESHOLD=0.9
CONTENT_HISTORY_SIZE=100

# Faster execution
API_TIMEOUT_SECONDS=20
RATE_LIMIT_DELAY=0.5
```

## Validation

The agent validates environment variables on startup. Common validation errors:

### Missing Required Variables
```
ERROR: PERPLEXITY_API_KEY environment variable is required
ERROR: BLUESKY_USERNAME environment variable is required
ERROR: BLUESKY_PASSWORD environment variable is required
```

### Invalid Values
```
ERROR: POSTING_INTERVAL_MINUTES must be between 5 and 1440
ERROR: MIN_ENGAGEMENT_SCORE must be between 0.0 and 1.0
ERROR: LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Configuration Conflicts
```
WARNING: MAX_EXECUTION_TIME_MINUTES should be less than POSTING_INTERVAL_MINUTES
WARNING: Very low DUPLICATE_THRESHOLD may cause excessive duplicate detection
```

## Security Best Practices

1. **Never commit .env files** to version control
2. **Use strong passwords** for Bluesky accounts
3. **Rotate API keys** regularly
4. **Set proper file permissions**: `chmod 600 .env`
5. **Use environment-specific configurations**
6. **Monitor logs** for credential exposure
7. **Use Docker secrets** in production environments

## Troubleshooting

### Common Issues

**Environment variables not loading:**
- Check file permissions: `ls -la .env`
- Verify file format (no spaces around `=`)
- Check for hidden characters or encoding issues

**Invalid API credentials:**
- Verify API key format and validity
- Check Bluesky username format
- Test credentials manually

**Configuration conflicts:**
- Run validation: `./scripts/setup.sh validate`
- Check logs for warnings
- Review interdependent settings

### Testing Configuration

```bash
# Validate environment
./scripts/setup.sh validate

# Test with specific environment file
docker-compose --env-file .env.dev up

# Check loaded environment in container
docker-compose exec bluesky-crypto-agent env | grep -E "(PERPLEXITY|BLUESKY|POSTING)"
```