#!/usr/bin/env python3
import os
import json
import argparse
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch

def load_config():
    with open('models/model_config.json', 'r') as f:
        return json.load(f)

def download_model(config):
    print(f"Downloading and preparing {config['model_name']}...")
    
    # Create quantization config
    if config['quantization']['enabled']:
        print(f"Using {config['quantization']['bits']}-bit quantization...")
        
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=config['quantization']['bits'] == 4,
            load_in_8bit=config['quantization']['bits'] == 8,
            llm_int8_threshold=6.0,
            llm_int8_has_fp16_weight=False,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
    else:
        quantization_config = None
    
    # Download tokenizer
    print("Downloading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        f"mistralai/{config['model_name']}",
        use_auth_token=os.environ.get("HF_TOKEN")
    )
    
    # Download model
    print("Downloading model (this may take a while)...")
    model = AutoModelForCausalLM.from_pretrained(
        f"mistralai/{config['model_name']}",
        quantization_config=quantization_config,
        device_map="auto",
        use_auth_token=os.environ.get("HF_TOKEN")
    )
    
    # Save the model and tokenizer locally
    local_path = Path(config['local_path'])
    local_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Saving model and tokenizer to {local_path}...")
    model.save_pretrained(local_path)
    tokenizer.save_pretrained(local_path)
    
    print("Model download and preparation complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and prepare Mixtral model")
    parser.add_argument("--config", type=str, default="models/model_config.json", help="Path to model config file")
    args = parser.parse_args()
    
    config = load_config()
    download_model(config)