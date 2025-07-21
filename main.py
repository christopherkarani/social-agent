#!/usr/bin/env python3
"""
Main entry point for the Bluesky Crypto Agent
Runs the agent continuously with scheduled posting
"""
import os
import sys
import time
import signal
import logging
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.config.agent_config import AgentConfig
from src.agents.bluesky_crypto_agent import BlueskyCryptoAgent
from src.utils.logging_config import setup_logging


class BlueskyCryptoAgentRunner:
    """Main runner for the Bluesky Crypto Agent"""
    
    def __init__(self):
        self.config = None
        self.agent = None
        self.scheduler = None
        self.running = False
        self.logger = None
        
    def setup(self):
        """Initialize the agent and all components"""
        try:
            # Load configuration
            self.config = AgentConfig.from_env()
            
            # Setup logging
            setup_logging({
                "log_level": self.config.log_level,
                "log_file": os.path.basename(self.config.log_file_path),
                "log_dir": os.path.dirname(self.config.log_file_path) or "logs"
            })
            self.logger = logging.getLogger(__name__)
            
            self.logger.info("Starting Bluesky Crypto Agent...")
            self.logger.info(f"Configuration: {self.config.to_dict()}")
            
            # Validate configuration
            if not self.config.validate():
                self.logger.error("Configuration validation failed")
                return False
            
            # Initialize agent (tools are initialized internally)
            # Create a mock LLM for now - in production you'd use a real LLM
            from unittest.mock import Mock
            mock_llm = Mock()
            mock_llm.name = "MockLLM"
            
            self.agent = BlueskyCryptoAgent(
                llm=mock_llm,
                config=self.config
            )
            
            # No separate scheduler needed - we'll handle scheduling in the main loop
            
            self.logger.info("Agent initialization completed successfully")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize agent: {e}")
            else:
                print(f"ERROR: Failed to initialize agent: {e}")
            return False
    
    def run_single_cycle(self):
        """Run a single posting cycle"""
        try:
            self.logger.info("Starting posting cycle...")
            
            # Execute the complete workflow using the agent's main method
            # This handles: retrieve news -> generate content -> filter -> post
            import asyncio
            
            # Run the async workflow
            if hasattr(asyncio, 'run'):
                # Python 3.7+
                result = asyncio.run(self.agent.execute_workflow("latest cryptocurrency news"))
            else:
                # Python 3.6 compatibility
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(self.agent.execute_workflow("latest cryptocurrency news"))
            
            if result.success:
                self.logger.info(f"Successfully posted: {result.content.text[:50] if result.content else 'N/A'}...")
                self.logger.info(f"Post ID: {result.post_id}")
                return True
            else:
                self.logger.warning(f"Posting cycle failed: {result.error_message}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error in posting cycle: {e}")
            return False
    
    def run_scheduled(self):
        """Run the agent with scheduled posting"""
        self.logger.info(f"Starting scheduled mode - posting every {self.config.posting_interval_minutes} minutes")
        
        self.running = True
        next_post_time = datetime.now()
        
        while self.running:
            try:
                current_time = datetime.now()
                
                if current_time >= next_post_time:
                    self.logger.info("Time for next posting cycle")
                    
                    # Run posting cycle
                    success = self.run_single_cycle()
                    
                    # Schedule next post
                    next_post_time = current_time + timedelta(minutes=self.config.posting_interval_minutes)
                    self.logger.info(f"Next post scheduled for: {next_post_time}")
                    
                    if success:
                        self.logger.info("Posting cycle completed successfully")
                    else:
                        self.logger.warning("Posting cycle completed with issues")
                
                # Sleep for 1 minute before checking again
                time.sleep(60)
                
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(60)  # Wait before retrying
    
    def run_once(self):
        """Run the agent once and exit"""
        self.logger.info("Running single posting cycle...")
        success = self.run_single_cycle()
        
        if success:
            self.logger.info("Single cycle completed successfully")
            return 0
        else:
            self.logger.error("Single cycle failed")
            return 1
    
    def stop(self):
        """Stop the agent"""
        self.logger.info("Stopping agent...")
        self.running = False
        
        if self.scheduler:
            self.scheduler.stop()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    global agent_runner
    if agent_runner:
        agent_runner.stop()
    sys.exit(0)


def main():
    """Main entry point"""
    global agent_runner
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    mode = sys.argv[1] if len(sys.argv) > 1 else "scheduled"
    
    # Initialize agent runner
    agent_runner = BlueskyCryptoAgentRunner()
    
    # Setup agent
    if not agent_runner.setup():
        print("Failed to initialize agent")
        return 1
    
    try:
        if mode == "once":
            # Run once and exit
            return agent_runner.run_once()
        elif mode == "scheduled":
            # Run continuously with scheduled posting
            agent_runner.run_scheduled()
            return 0
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python main.py [once|scheduled]")
            return 1
            
    except Exception as e:
        if agent_runner.logger:
            agent_runner.logger.error(f"Fatal error: {e}")
        else:
            print(f"FATAL ERROR: {e}")
        return 1
    finally:
        if agent_runner:
            agent_runner.stop()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)