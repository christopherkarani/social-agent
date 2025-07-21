# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Bluesky Crypto Agent.

## Quick Diagnostics

### 1. Check Agent Status
```bash
# Check if container is running
./scripts/deploy.sh status

# View recent logs
./scripts/deploy.sh logs

# Check container health
docker inspect --format='{{.State.Health.Status}}' bluesky-crypto-agent
```

### 2. Validate Configuration
```bash
# Run configuration validation
./scripts/setup.sh validate

# Check environment variables
cat .env | grep -v '^#' | grep -v '^$'
```

### 3. Test Components
```bash
# Test Docker build
docker-compose build --no-cache

# Test container creation
docker-compose create
```

## Common Issues

### Container Issues

#### Container Won't Start

**Symptoms:**
- Container exits immediately
- "Container not running" error
- Exit code 1 or 125

**Diagnosis:**
```bash
# Check container logs
docker-compose logs bluesky-crypto-agent

# Check Docker daemon
docker info

# Verify image exists
docker images | grep bluesky-crypto-agent
```

**Solutions:**

1. **Missing environment variables:**
   ```bash
   # Check for required variables
   grep -E "(PERPLEXITY_API_KEY|BLUESKY_USERNAME|BLUESKY_PASSWORD)" .env
   
   # Fix: Update .env file with valid credentials
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Docker build issues:**
   ```bash
   # Rebuild without cache
   docker-compose build --no-cache
   
   # Check Dockerfile syntax
   docker build -t test-build .
   ```

3. **Permission issues:**
   ```bash
   # Fix file permissions
   chmod 600 .env
   chmod +x scripts/*.sh
   chmod 755 logs/ config/
   ```

#### Container Keeps Restarting

**Symptoms:**
- Container status shows "Restarting"
- Frequent restart logs
- High CPU usage

**Diagnosis:**
```bash
# Check restart count
docker ps -a | grep bluesky-crypto-agent

# Monitor resource usage
docker stats bluesky-crypto-agent

# Check system resources
free -h
df -h
```

**Solutions:**

1. **Memory issues:**
   ```bash
   # Increase memory limit in docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 1G  # Increase from 512M
   ```

2. **Infinite restart loop:**
   ```bash
   # Check entrypoint script
   cat docker-entrypoint.sh
   
   # Disable restart policy temporarily
   docker-compose up --no-deps bluesky-crypto-agent
   ```

3. **Application crashes:**
   ```bash
   # Check Python errors in logs
   ./scripts/deploy.sh logs | grep -i "error\|exception\|traceback"
   ```

### API Integration Issues

#### Perplexity API Errors

**Symptoms:**
- "API key invalid" errors
- "Rate limit exceeded" messages
- News retrieval failures

**Diagnosis:**
```bash
# Check API key format
echo $PERPLEXITY_API_KEY | wc -c  # Should be ~40 characters

# Test API connectivity
curl -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"llama-3.1-sonar-small-128k-online","messages":[{"role":"user","content":"test"}]}' \
     https://api.perplexity.ai/chat/completions
```

**Solutions:**

1. **Invalid API key:**
   ```bash
   # Get new API key from Perplexity dashboard
   # Update .env file
   PERPLEXITY_API_KEY=pplx-new-valid-key
   
   # Restart container
   ./scripts/deploy.sh restart
   ```

2. **Rate limiting:**
   ```bash
   # Increase delay between requests
   RATE_LIMIT_DELAY=2.0
   
   # Reduce posting frequency
   POSTING_INTERVAL_MINUTES=60
   ```

3. **Network connectivity:**
   ```bash
   # Test from container
   docker-compose exec bluesky-crypto-agent ping api.perplexity.ai
   
   # Check firewall/proxy settings
   ```

#### Bluesky API Errors

**Symptoms:**
- Authentication failures
- "Invalid credentials" errors
- Posts not appearing on Bluesky

**Diagnosis:**
```bash
# Check credentials format
echo "Username: $BLUESKY_USERNAME"
echo "Password length: $(echo $BLUESKY_PASSWORD | wc -c)"

# Test authentication manually
curl -X POST https://bsky.social/xrpc/com.atproto.server.createSession \
     -H "Content-Type: application/json" \
     -d '{"identifier":"'$BLUESKY_USERNAME'","password":"'$BLUESKY_PASSWORD'"}'
```

**Solutions:**

1. **Wrong credentials:**
   ```bash
   # Verify username format (with or without .bsky.social)
   BLUESKY_USERNAME=myuser.bsky.social
   # OR
   BLUESKY_USERNAME=myuser
   
   # Check password (no special characters issues)
   # Update .env and restart
   ```

2. **Account locked/suspended:**
   ```bash
   # Check Bluesky account status in web interface
   # Contact Bluesky support if needed
   ```

3. **API changes:**
   ```bash
   # Check for agent updates
   git pull origin main
   
   # Rebuild with latest code
   docker-compose build --no-cache
   ```

### Content Generation Issues

#### No Posts Being Generated

**Symptoms:**
- Agent runs but no posts appear
- "Content filtered" messages in logs
- Low engagement scores

**Diagnosis:**
```bash
# Check content generation logs
./scripts/deploy.sh logs | grep -i "content\|generate\|filter"

# Check quality thresholds
grep -E "(MIN_ENGAGEMENT_SCORE|DUPLICATE_THRESHOLD)" .env
```

**Solutions:**

1. **Quality thresholds too high:**
   ```bash
   # Lower quality requirements
   MIN_ENGAGEMENT_SCORE=0.5
   DUPLICATE_THRESHOLD=0.7
   
   # Restart agent
   ./scripts/deploy.sh restart
   ```

2. **Content themes too narrow:**
   ```bash
   # Expand content themes
   CONTENT_THEMES=Bitcoin,Ethereum,DeFi,NFTs,Altcoins,Web3,Blockchain,Trading,Regulation
   ```

3. **Duplicate detection too aggressive:**
   ```bash
   # Reduce duplicate sensitivity
   DUPLICATE_THRESHOLD=0.6
   CONTENT_HISTORY_SIZE=25
   ```

#### Poor Content Quality

**Symptoms:**
- Generic or repetitive posts
- Low engagement on posted content
- Content doesn't match crypto themes

**Diagnosis:**
```bash
# Check content generation parameters
grep -E "(CONTENT_TEMPERATURE|HASHTAG_COUNT)" .env

# Review recent posts
./scripts/deploy.sh logs | grep -A5 -B5 "Posted content"
```

**Solutions:**

1. **Increase creativity:**
   ```bash
   # Higher temperature for more creative content
   CONTENT_TEMPERATURE=0.8
   
   # More diverse themes
   CONTENT_THEMES=Bitcoin,Ethereum,DeFi,NFTs,Altcoins,Web3,Trading,Regulation,Mining
   ```

2. **Improve content filtering:**
   ```bash
   # Stricter quality control
   MIN_ENGAGEMENT_SCORE=0.8
   
   # Better duplicate detection
   DUPLICATE_THRESHOLD=0.85
   CONTENT_HISTORY_SIZE=100
   ```

### Performance Issues

#### Slow Execution

**Symptoms:**
- Execution takes longer than expected
- Timeout errors
- High CPU/memory usage

**Diagnosis:**
```bash
# Check execution times
./scripts/deploy.sh logs | grep -i "execution\|time\|duration"

# Monitor resource usage
docker stats bluesky-crypto-agent

# Check system load
top
htop
```

**Solutions:**

1. **Increase timeouts:**
   ```bash
   # Longer execution time
   MAX_EXECUTION_TIME_MINUTES=35
   
   # Longer API timeouts
   API_TIMEOUT_SECONDS=60
   ```

2. **Optimize performance:**
   ```bash
   # Reduce content history
   CONTENT_HISTORY_SIZE=25
   
   # Faster API calls
   RATE_LIMIT_DELAY=0.5
   ```

3. **Resource allocation:**
   ```bash
   # Increase Docker resources in docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 1G
         cpus: '1.0'
   ```

#### Memory Issues

**Symptoms:**
- Out of memory errors
- Container killed by system
- Slow performance

**Diagnosis:**
```bash
# Check memory usage
docker stats --no-stream bluesky-crypto-agent

# Check system memory
free -h

# Check for memory leaks
./scripts/deploy.sh logs | grep -i "memory\|oom"
```

**Solutions:**

1. **Increase memory limits:**
   ```bash
   # In docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 1G
   ```

2. **Reduce memory usage:**
   ```bash
   # Smaller content history
   CONTENT_HISTORY_SIZE=25
   
   # Less verbose logging
   LOG_LEVEL=WARNING
   ```

### Scheduling Issues

#### Posts Not Scheduled Correctly

**Symptoms:**
- Irregular posting times
- Posts too frequent or infrequent
- Scheduler not running

**Diagnosis:**
```bash
# Check scheduler logs
./scripts/deploy.sh logs | grep -i "schedul\|interval\|cron"

# Verify timing configuration
grep POSTING_INTERVAL_MINUTES .env
```

**Solutions:**

1. **Fix timing configuration:**
   ```bash
   # Ensure reasonable interval
   POSTING_INTERVAL_MINUTES=30  # 30 minutes
   MAX_EXECUTION_TIME_MINUTES=25  # Less than interval
   ```

2. **Restart scheduler:**
   ```bash
   # Restart container
   ./scripts/deploy.sh restart
   
   # Check if scheduler starts
   ./scripts/deploy.sh logs | tail -20
   ```

#### Execution Timeouts

**Symptoms:**
- "Execution timeout" errors
- Incomplete workflows
- Scheduler skipping cycles

**Diagnosis:**
```bash
# Check timeout settings
grep -E "(MAX_EXECUTION_TIME|TIMEOUT)" .env

# Look for timeout errors
./scripts/deploy.sh logs | grep -i "timeout\|exceeded"
```

**Solutions:**

1. **Increase timeout:**
   ```bash
   # Longer execution time
   MAX_EXECUTION_TIME_MINUTES=35
   
   # Longer API timeouts
   API_TIMEOUT_SECONDS=45
   ```

2. **Optimize workflow:**
   ```bash
   # Faster API calls
   RATE_LIMIT_DELAY=0.5
   MAX_RETRIES=2
   ```

## Advanced Troubleshooting

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Set debug logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Restart with debug mode
./scripts/deploy.sh restart

# Monitor debug logs
./scripts/deploy.sh logs | grep DEBUG
```

### Component Testing

Test individual components:

```bash
# Test news retrieval
docker-compose exec bluesky-crypto-agent python -c "
from src.tools.news_retrieval_tool import NewsRetrievalTool
tool = NewsRetrievalTool()
result = tool._run('Bitcoin news')
print(result)
"

# Test content generation
docker-compose exec bluesky-crypto-agent python -c "
from src.tools.content_generation_tool import ContentGenerationTool
tool = ContentGenerationTool()
result = tool._run({'headline': 'Bitcoin reaches new high'})
print(result)
"

# Test Bluesky posting
docker-compose exec bluesky-crypto-agent python -c "
from src.tools.bluesky_social_tool import BlueskySocialTool
tool = BlueskySocialTool()
# Note: This will actually post, use carefully
"
```

### Network Debugging

Check network connectivity:

```bash
# Test DNS resolution
docker-compose exec bluesky-crypto-agent nslookup api.perplexity.ai
docker-compose exec bluesky-crypto-agent nslookup bsky.social

# Test HTTP connectivity
docker-compose exec bluesky-crypto-agent curl -I https://api.perplexity.ai
docker-compose exec bluesky-crypto-agent curl -I https://bsky.social

# Check proxy settings
docker-compose exec bluesky-crypto-agent env | grep -i proxy
```

### Log Analysis

Analyze logs for patterns:

```bash
# Error frequency
./scripts/deploy.sh logs | grep -i error | wc -l

# Most common errors
./scripts/deploy.sh logs | grep -i error | sort | uniq -c | sort -nr

# Execution patterns
./scripts/deploy.sh logs | grep -i "execution\|workflow" | tail -20

# API call patterns
./scripts/deploy.sh logs | grep -i "api\|request" | tail -20
```

## Getting Help

### Information to Collect

When seeking help, collect this information:

```bash
# System information
uname -a
docker --version
docker-compose --version

# Container status
./scripts/deploy.sh status

# Recent logs (last 50 lines)
./scripts/deploy.sh logs | tail -50

# Configuration (without sensitive data)
cat .env | sed 's/=.*/=***HIDDEN***/'

# Resource usage
docker stats --no-stream bluesky-crypto-agent
```

### Log Sanitization

Remove sensitive data from logs before sharing:

```bash
# Create sanitized log file
./scripts/deploy.sh logs | \
  sed 's/pplx-[a-zA-Z0-9]*/pplx-***HIDDEN***/g' | \
  sed 's/password[^,]*,/password:***HIDDEN***,/g' > sanitized_logs.txt
```

### Support Channels

1. **Check documentation** first
2. **Search existing issues** in the repository
3. **Create detailed issue** with:
   - Problem description
   - Steps to reproduce
   - Expected vs actual behavior
   - System information
   - Sanitized logs
   - Configuration (without secrets)

### Emergency Recovery

If the agent is completely broken:

```bash
# Stop everything
./scripts/deploy.sh stop

# Clean up
docker-compose down --volumes --remove-orphans
docker system prune -f

# Fresh start
./scripts/setup.sh
./scripts/deploy.sh
```

## Prevention

### Monitoring Setup

Set up monitoring to prevent issues:

```bash
# Regular health checks
*/5 * * * * docker inspect --format='{{.State.Health.Status}}' bluesky-crypto-agent

# Log rotation
*/0 * * * * find logs/ -name "*.log" -size +100M -exec truncate -s 50M {} \;

# Resource monitoring
*/15 * * * * docker stats --no-stream bluesky-crypto-agent >> monitoring.log
```

### Maintenance Tasks

Regular maintenance:

```bash
# Weekly: Update and restart
git pull origin main
./scripts/deploy.sh stop
docker-compose build --no-cache
./scripts/deploy.sh

# Monthly: Clean up Docker
docker system prune -f
docker volume prune -f

# Check for updates
pip list --outdated
```

### Best Practices

1. **Monitor logs regularly**
2. **Keep backups of working configurations**
3. **Test changes in development first**
4. **Monitor resource usage**
5. **Keep API keys secure and rotated**
6. **Document any custom modifications**