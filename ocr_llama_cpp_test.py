#!/usr/bin/env python
"""
Test script for using llama_cpp with surya-2.gguf model as OCR.

This script demonstrates how to use the llama_cpp Python library
with the surya-2.gguf model for OCR tasks.

Note: This is a test script only. Make sure you have the required
dependencies installed:
- llama-cpp-python
- The surya-2.gguf model file

Usage:
    python ocr_llama_cpp_test.py <image_path> [--model-path MODEL_PATH]
"""

import sys
import os
import argparse
import base64


def encode_image_base64(image_path: str) -> str:
    """Encode image to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def perform_ocr(model_path: str, image_path: str) -> str:
    """
    Perform OCR using llama_cpp with the surya-2.gguf model.
    
    Args:
        model_path: Path to the surya-2.gguf model file
        image_path: Path to the image file to process
        
    Returns:
        Extracted text from the image
    """
    try:
        from llama_cpp import Llama
    except ImportError:
        return "Error: llama-cpp-python not installed. Run: pip install llama-cpp-python"

    if not os.path.exists(model_path):
        return f"Error: Model file not found: {model_path}"

    # Load the model
    # n_gpu_layers=-1 uses all GPU layers (requires CUDA/Metal)
    # n_ctx=4096 sets context window size
    # verbose=False suppresses llama.cpp logs
    llm = Llama(
        model_path=model_path,
        n_gpu_layers=-1,
        n_ctx=4096,
        verbose=False,
        logits_all=False,
    )

    # Encode image to base64
    b64_image = encode_image_base64(image_path)

    # Create the prompt for OCR
    # Surya models typically expect a specific format for vision tasks
    prompt = f"""<|im_start|>user
<|image|>{b64_image}<|im_end|>
Extract all text visible in this image. Preserve the structure. If there is no text, say 'No text found'.
<|im_start|>assistant
"""

    # Generate response
    response = llm(
        prompt,
        max_tokens=2048,
        temperature=0.1,
        top_p=0.9,
        stop=["<|im_end|>", "<|im_start|>"],
        echo=False,
    )

    # Extract the generated text
    if response and "choices" in response and len(response["choices"]) > 0:
        return response["choices"][0]["text"].strip()
    
    return "No text extracted"


def main():
    """Main entry point for the OCR test script."""
    parser = argparse.ArgumentParser(description="Test OCR with llama_cpp and surya-2.gguf")
    parser.add_argument("image_path", help="Path to the image file to process")
    parser.add_argument(
        "--model-path", 
        default="surya-2.gguf",
        help="Path to the surya-2.gguf model file (default: surya-2.gguf in current directory)"
    )
    args = parser.parse_args()

    image_path = args.image_path
    model_path = args.model_path

    if not os.path.exists(image_path):
        print(f"Error: File not found: {image_path}")
        sys.exit(1)

    print(f"Processing image: {image_path}")
    print(f"File size: {os.path.getsize(image_path)} bytes")
    print(f"Model path: {model_path}")
    print("-" * 50)

    # Perform OCR
    result = perform_ocr(model_path, image_path)
    
    print("OCR Result:")
    print(result)
    print("-" * 50)
    print("Test completed successfully!")


if __name__ == "__main__":
    main()