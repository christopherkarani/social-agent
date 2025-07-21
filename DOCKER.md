# Docker Deployment Guide

This guide covers how to deploy the Bluesky Crypto Agent using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Required API keys (Perplexity, Bluesky)

## Quick Start

1. **Clone and setup environment:**
   ```bash
   git clone <repository-url>
   cd bluesky-crypto-agent
   cp .env.example .env
   ```

2. **Configure environment variables:**
   Edit `.env` file with your API credentials:
   ```bash
   PERPLEXITY_API_KEY=your_actual_perplexity_api_key
   BLUESKY_USERNAME=your_bluesky_username
   BLUESKY_PASSWORD=your_bluesky_password
   ```

3. **Start the agent:**
   ```bash
   docker-compose up -d
   ```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PERPLEXITY_API_KEY` | Yes | - | Perplexity API key for news retrieval |
| `BLUESKY_USERNAME` | Yes | - | Bluesky username/handle |
| `BLUESKY_PASSWORD` | Yes | - | Bluesky password |
| `POSTING_INTERVAL_MINUTES` | No | 30 | Minutes between posts |
| `MAX_EXECUTION_TIME_MINUTES` | No | 25 | Max execution time per cycle |
| `MAX_POST_LENGTH` | No | 300 | Maximum post character length |
| `MIN_ENGAGEMENT_SCORE` | No | 0.7 | Minimum engagement score for posting |
| `DUPLICATE_THRESHOLD` | No | 0.8 | Similarity threshold for duplicate detection |
| `MAX_RETRIES` | No | 3 | Maximum API retry attempts |
| `CONTENT_THEMES` | No | Bitcoin,Ethereum,DeFi,NFT,Altcoins | Comma-separated content themes |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | No | json | Log format (json, text) |

### Volume Mounts

The container uses the following volume mounts for persistence:

- `./logs:/app/logs` - Application logs
- `./config:/app/config` - Configuration files
- `./.env:/app/.env:ro` - Environment variables (read-only)

## Docker Commands

### Build and Run

```bash
# Build the image
docker build -t bluesky-crypto-agent .

# Run with environment variables
docker run -d \
  --name bluesky-crypto-agent \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config \
  bluesky-crypto-agent
```

### Docker Compose (Recommended)

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Update and restart
docker-compose pull && docker-compose up -d
```

### Monitoring

```bash
# Check container status
docker-compose ps

# View real-time logs
docker-compose logs -f bluesky-crypto-agent

# Check resource usage
docker stats bluesky-crypto-agent

# Execute commands in container
docker-compose exec bluesky-crypto-agent bash
```

## Health Checks

The container includes health checks that run every 30 seconds:

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' bluesky-crypto-agent

# View health check logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' bluesky-crypto-agent
```

## Troubleshooting

### Common Issues

1. **Container fails to start:**
   ```bash
   # Check logs for errors
   docker-compose logs bluesky-crypto-agent
   
   # Verify environment variables
   docker-compose config
   ```

2. **API authentication errors:**
   ```bash
   # Verify credentials in .env file
   cat .env | grep -E "(PERPLEXITY|BLUESKY)"
   
   # Test API connectivity
   docker-compose exec bluesky-crypto-agent python -c "from src.config.agent_config import AgentConfig; print(AgentConfig.from_env().validate())"
   ```

3. **Permission issues with volumes:**
   ```bash
   # Fix permissions
   sudo chown -R $USER:$USER logs config
   chmod 755 logs config
   ```

4. **Container resource issues:**
   ```bash
   # Check resource usage
   docker stats bluesky-crypto-agent
   
   # Adjust limits in docker-compose.yml if needed
   ```

### Log Analysis

```bash
# View recent logs
docker-compose logs --tail=100 bluesky-crypto-agent

# Search for errors
docker-compose logs bluesky-crypto-agent | grep -i error

# Monitor logs in real-time
docker-compose logs -f bluesky-crypto-agent | grep -E "(ERROR|WARNING|INFO)"
```

## Security Considerations

1. **Environment Variables:**
   - Never commit `.env` file to version control
   - Use Docker secrets for production deployments
   - Rotate API keys regularly

2. **Container Security:**
   - Container runs as non-root user (`app`)
   - Minimal base image (Python slim)
   - No unnecessary packages installed

3. **Network Security:**
   - Container uses custom bridge network
   - Only necessary ports exposed
   - No privileged access required

## Production Deployment

For production deployments, consider:

1. **Use Docker Secrets:**
   ```yaml
   secrets:
     perplexity_api_key:
       external: true
     bluesky_password:
       external: true
   ```

2. **Add monitoring:**
   - Prometheus metrics
   - Grafana dashboards
   - Alert manager integration

3. **Implement backup:**
   - Regular log rotation
   - Configuration backup
   - Database backup (if applicable)

4. **Use orchestration:**
   - Docker Swarm
   - Kubernetes
   - Nomad

## Development

### Running Tests

```bash
# Run all tests including Docker integration
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Run specific test
docker-compose exec bluesky-crypto-agent python -m pytest tests/test_docker_integration.py -v
```

### Debugging

```bash
# Run container interactively
docker-compose run --rm bluesky-crypto-agent bash

# Override entrypoint for debugging
docker-compose run --rm --entrypoint="" bluesky-crypto-agent bash
```

## Support

For issues and questions:
1. Check the logs first: `docker-compose logs bluesky-crypto-agent`
2. Verify configuration: `docker-compose config`
3. Test connectivity: Run health checks
4. Review this documentation
5. Check GitHub issues