#!/usr/bin/env python3
"""
Integration tests for Docker containerization setup
"""
import os
import subprocess
import time
import tempfile
import shutil
from pathlib import Path
import pytest
import yaml


class TestDockerIntegration:
    """Test Docker containerization setup"""
    
    @classmethod
    def setup_class(cls):
        """Set up test environment"""
        cls.project_root = Path(__file__).parent.parent
        cls.image_name = "bluesky-crypto-agent-test"
        cls.container_name = "bluesky-crypto-agent-test-container"
        
        try:
            import docker
            cls.docker_client = docker.from_env()
            cls.docker_client.ping()
            cls.docker_available = True
        except Exception as e:
            cls.docker_available = False
            pytest.skip(f"Docker is not available: {e}")
    
    @classmethod
    def _check_docker_available(cls):
        """Check if Docker is available"""
        return cls.docker_available
    
    def teardown_method(self):
        """Clean up containers and images after each test"""
        if not hasattr(self, 'docker_client'):
            return
            
        try:
            import docker
            # Stop and remove container if it exists
            try:
                container = self.docker_client.containers.get(self.container_name)
                container.stop(timeout=10)
                container.remove()
            except docker.errors.NotFound:
                pass
            
            # Remove test image if it exists
            try:
                self.docker_client.images.remove(self.image_name, force=True)
            except docker.errors.ImageNotFound:
                pass
        except Exception as e:
            print(f"Cleanup warning: {e}")
    
    def test_dockerfile_build(self):
        """Test that Dockerfile builds successfully"""
        # Build the Docker image
        image, build_logs = self.docker_client.images.build(
            path=str(self.project_root),
            tag=self.image_name,
            rm=True,
            forcerm=True
        )
        
        assert image is not None
        assert any(self.image_name in tag for tag in image.tags)
        
        # Verify image properties
        assert image.attrs['Config']['WorkingDir'] == '/app'
        assert image.attrs['Config']['User'] == 'app'
        
        # Check that required directories exist in image
        container = self.docker_client.containers.create(
            image=self.image_name,
            command="ls -la /app",
            entrypoint=""
        )
        container.start()
        container.wait()
        
        logs = container.logs().decode('utf-8')
        assert 'logs' in logs
        assert 'config' in logs
        assert 'src' in logs
        
        container.remove()
    
    def test_environment_variable_configuration(self):
        """Test environment variable configuration in container"""
        # Create test environment variables
        test_env = {
            'PERPLEXITY_API_KEY': 'test_perplexity_key',
            'BLUESKY_USERNAME': 'test_username',
            'BLUESKY_PASSWORD': 'test_password',
            'POSTING_INTERVAL_MINUTES': '15',
            'LOG_LEVEL': 'DEBUG'
        }
        
        # Build image first
        self.docker_client.images.build(
            path=str(self.project_root),
            tag=self.image_name,
            rm=True
        )
        
        # Run container with environment variables
        container = self.docker_client.containers.run(
            image=self.image_name,
            environment=test_env,
            command="python -c \"import os; print('ENV_TEST_PASSED') if os.getenv('PERPLEXITY_API_KEY') == 'test_perplexity_key' else print('ENV_TEST_FAILED')\"",
            detach=True,
            name=self.container_name
        )
        
        # Wait for container to complete
        result = container.wait(timeout=30)
        logs = container.logs().decode('utf-8')
        
        assert result['StatusCode'] == 0
        assert 'ENV_TEST_PASSED' in logs
        
        container.remove()
    
    def test_volume_mounting(self):
        """Test volume mounting for persistent logs and configuration"""
        # Create temporary directories for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, 'logs')
            config_dir = os.path.join(temp_dir, 'config')
            os.makedirs(logs_dir)
            os.makedirs(config_dir)
            
            # Create a test config file
            test_config_path = os.path.join(config_dir, 'test.txt')
            with open(test_config_path, 'w') as f:
                f.write('test configuration')
            
            # Build image
            self.docker_client.images.build(
                path=str(self.project_root),
                tag=self.image_name,
                rm=True
            )
            
            # Run container with volume mounts, bypassing entrypoint
            container = self.docker_client.containers.run(
                image=self.image_name,
                volumes={
                    logs_dir: {'bind': '/app/logs', 'mode': 'rw'},
                    config_dir: {'bind': '/app/config', 'mode': 'rw'}
                },
                command="sh -c 'echo \"test log entry\" > /app/logs/test.log && cat /app/config/test.txt'",
                entrypoint="",
                detach=True,
                name=self.container_name
            )
            
            # Wait for container to complete
            result = container.wait(timeout=30)
            logs = container.logs().decode('utf-8')
            
            assert result['StatusCode'] == 0
            assert 'test configuration' in logs
            
            # Verify log file was created on host
            test_log_path = os.path.join(logs_dir, 'test.log')
            assert os.path.exists(test_log_path)
            
            with open(test_log_path, 'r') as f:
                log_content = f.read()
                assert 'test log entry' in log_content
            
            container.remove()
    
    def test_docker_compose_configuration(self):
        """Test docker-compose.yml configuration"""
        compose_file = self.project_root / 'docker-compose.yml'
        assert compose_file.exists()
        
        # Read and validate docker-compose.yml content
        with open(compose_file, 'r') as f:
            compose_content = f.read()
        
        # Check required sections
        assert 'version:' in compose_content
        assert 'services:' in compose_content
        assert 'bluesky-crypto-agent:' in compose_content
        assert 'volumes:' in compose_content
        assert 'networks:' in compose_content
        
        # Check environment variables
        assert 'PERPLEXITY_API_KEY' in compose_content
        assert 'BLUESKY_USERNAME' in compose_content
        assert 'BLUESKY_PASSWORD' in compose_content
        
        # Check volume mounts
        assert './logs:/app/logs' in compose_content
        assert './config:/app/config' in compose_content
        
        # Check health check
        assert 'healthcheck:' in compose_content
    
    def test_entrypoint_script(self):
        """Test Docker entrypoint script functionality"""
        entrypoint_script = self.project_root / 'docker-entrypoint.sh'
        assert entrypoint_script.exists()
        
        # Check script is executable
        assert os.access(entrypoint_script, os.X_OK)
        
        # Build image
        self.docker_client.images.build(
            path=str(self.project_root),
            tag=self.image_name,
            rm=True
        )
        
        # Test entrypoint with missing environment variables
        container = self.docker_client.containers.run(
            image=self.image_name,
            command="echo 'test'",
            detach=True,
            name=self.container_name
        )
        
        result = container.wait(timeout=30)
        logs = container.logs().decode('utf-8')
        
        # Should fail due to missing required environment variables
        assert result['StatusCode'] != 0
        assert 'ERROR:' in logs
        assert 'PERPLEXITY_API_KEY' in logs
        
        container.remove()
    
    def test_container_health_check(self):
        """Test container health check functionality"""
        # Build image
        self.docker_client.images.build(
            path=str(self.project_root),
            tag=self.image_name,
            rm=True
        )
        
        # Run container with required environment variables
        test_env = {
            'PERPLEXITY_API_KEY': 'test_key',
            'BLUESKY_USERNAME': 'test_user',
            'BLUESKY_PASSWORD': 'test_pass'
        }
        
        container = self.docker_client.containers.run(
            image=self.image_name,
            environment=test_env,
            detach=True,
            name=self.container_name
        )
        
        # Wait a bit for health check to run
        time.sleep(5)
        
        # Reload container to get updated health status
        container.reload()
        
        # Health check should be defined
        health_config = container.attrs['Config'].get('Healthcheck')
        assert health_config is not None
        assert health_config['Test'] == ['CMD-SHELL', 'python -c "import sys; sys.exit(0)"']
        
        container.stop(timeout=10)
        container.remove()
    
    def test_resource_limits(self):
        """Test resource limits configuration in docker-compose"""
        compose_file = self.project_root / 'docker-compose.yml'
        
        with open(compose_file, 'r') as f:
            compose_content = f.read()
        
        # Check resource limits are defined
        assert 'deploy:' in compose_content
        assert 'resources:' in compose_content
        assert 'limits:' in compose_content
        assert 'memory: 512M' in compose_content
        assert 'cpus:' in compose_content
        assert 'reservations:' in compose_content
    
    def test_network_configuration(self):
        """Test network configuration in docker-compose"""
        compose_file = self.project_root / 'docker-compose.yml'
        
        with open(compose_file, 'r') as f:
            compose_content = f.read()
        
        # Check network configuration
        assert 'networks:' in compose_content
        assert 'bluesky-network:' in compose_content
        assert 'driver: bridge' in compose_content
    
    def test_dockerfile_security(self):
        """Test Dockerfile security best practices"""
        dockerfile_path = self.project_root / 'Dockerfile'
        
        with open(dockerfile_path, 'r') as f:
            dockerfile_content = f.read()
        
        # Check non-root user
        assert 'USER app' in dockerfile_content
        assert 'useradd' in dockerfile_content
        
        # Check environment variables for security
        assert 'PYTHONDONTWRITEBYTECODE=1' in dockerfile_content
        assert 'PYTHONUNBUFFERED=1' in dockerfile_content
        
        # Check package cleanup
        assert 'rm -rf /var/lib/apt/lists/*' in dockerfile_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])