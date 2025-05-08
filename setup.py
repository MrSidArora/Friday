# setup.py
import os
import json

def setup_friday_environment():
    """Set up the initial Friday AI environment."""
    print("Setting up Friday AI environment...")
    
    # Create necessary directories
    directories = [
        "configs",
        "data/memory",
        "logs",
        "models"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Create configuration files
    create_config_files()
    
    print("Setup complete!")

def create_config_files():
    """Create initial configuration files."""
    # Main configuration
    main_config = {
        "system": {
            "name": "Friday",
            "version": "0.1.0",
            "development_mode": True
        },
        "paths": {
            "models": "models",
            "data": "data",
            "logs": "logs",
            "configs": "configs"
        },
        "components": {
            "model_manager": {
                "config_path": "configs/model_config.json",
                "enabled": True
            },
            "memory_system": {
                "config_path": "configs/memory_config.json",
                "enabled": True
            },
            "security_monitor": {
                "config_path": "configs/security_config.json",
                "enabled": True
            }
        }
    }
    
    with open("configs/config.json", "w") as f:
        json.dump(main_config, f, indent=2)
    print("Created main configuration file")
    
    # Model configuration
    model_config = {
        "model_directory": "models",
        "auto_load_model": False,
        "default_model": "mixtral-8x7b-instruct-v0.1-4bit",
        "models": {
            "mixtral-8x7b-instruct-v0.1-4bit": {
                "type": "mixtral",
                "path": "mixtral-8x7b-instruct-v0.1-4bit",
                "quantization": "4bit",
                "max_context_length": 8192,
                "requires_gpu": True
            }
        }
    }
    
    with open("configs/model_config.json", "w") as f:
        json.dump(model_config, f, indent=2)
    print("Created model configuration file")
    
    # Memory configuration
    memory_config = {
        "short_term": {
            "host": "redis",  # Use the Docker service name
            "port": 6379,
            "db": 0,
            "ttl": 3600  # 1 hour
        },
        "mid_term": {
            "db_path": "data/memory/mid_term.db",
            "retention_days": 30
        },
        "long_term": {
            "db_path": "data/memory/long_term",
            "similarity_threshold": 0.75
        }
    }
    
    with open("configs/memory_config.json", "w") as f:
        json.dump(memory_config, f, indent=2)
    print("Created memory configuration file")
    
    # Security configuration
    security_config = {
        "logging": {
            "level": "INFO",
            "file_path": "logs/security.log",
            "max_size_mb": 10,
            "backup_count": 5
        },
        "monitoring": {
            "check_interval_seconds": 60,
            "thresholds": {
                "cpu_warning": 80.0,
                "cpu_critical": 95.0,
                "memory_warning": 80.0,
                "memory_critical": 95.0,
                "disk_warning": 85.0,
                "disk_critical": 95.0
            }
        },
        "security": {
            "log_api_access": True,
            "log_internet_access": True,
            "require_confirmation_for_system_commands": True
        }
    }
    
    with open("configs/security_config.json", "w") as f:
        json.dump(security_config, f, indent=2)
    print("Created security configuration file")

if __name__ == "__main__":
    setup_friday_environment()