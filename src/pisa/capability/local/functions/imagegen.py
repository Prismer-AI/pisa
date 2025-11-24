"""
Image Generation Capability using Google Gemini API

Generates images from text prompts using Google's Gemini model.
"""

import os
import base64
from typing import Dict, Any, Optional, List
from pathlib import Path

from pisa.capability import capability


@capability(
    name="generate_image",
    description="Generate images from text prompts using Google Gemini API with customizable aspect ratio and size",
    capability_type="function",
    tags=["image", "generation", "gemini", "ai"],
    strict_mode=False
)
async def generate_image(
    prompt: str,
    aspect_ratio: str = "16:9",
    image_size: str = "2K",
    output_path: Optional[str] = None,
    include_text: bool = True
) -> Dict[str, Any]:
    """
    Generate an image from a text prompt using Google Gemini API
    
    Args:
        prompt: Text description of the image to generate
        aspect_ratio: Aspect ratio of the image (e.g., "16:9", "1:1", "9:16")
        image_size: Image size ("2K", "1K", "4K")
        output_path: Optional path to save the generated image
        include_text: Whether to include text explanation with the image
    
    Returns:
        Dictionary containing:
        - success: Whether generation was successful
        - image_data: Base64 encoded image data (if successful)
        - text: Generated text explanation (if include_text=True)
        - image_path: Path to saved image (if output_path provided)
        - error: Error message (if failed)
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return {
            "success": False,
            "error": "google-genai package not installed",
            "message": "Install google-genai: pip install google-genai"
        }
    
    # Get configuration from environment
    project_id = os.getenv("GOOGLE_PROJECT_ID", "prismer-web-application")
    location = os.getenv("GOOGLE_LOCATION", "global")
    model_id = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")
    
    try:
        # Initialize client
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location
        )
        
        # Configure generation
        response_modalities = ['IMAGE']
        if include_text:
            response_modalities.append('TEXT')
        
        config = types.GenerateContentConfig(
            response_modalities=response_modalities,
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            ),
        )
        
        # Generate content
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=config,
        )
        
        result = {
            "success": True,
            "prompt": prompt,
            "config": {
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
                "model": model_id,
                "project": project_id
            }
        }
        
        # Extract image data from response
        if response.candidates:
            candidate = response.candidates[0]
            
            # Get image and text from parts
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    # Extract image data
                    if hasattr(part, 'inline_data') and part.inline_data:
                        result['image_data'] = base64.b64encode(
                            part.inline_data.data
                        ).decode('utf-8')
                        result['mime_type'] = part.inline_data.mime_type
                        
                        # Save to file if requested
                        if output_path:
                            output_file = Path(output_path)
                            output_file.parent.mkdir(parents=True, exist_ok=True)
                            
                            with open(output_file, 'wb') as f:
                                f.write(part.inline_data.data)
                            
                            result['image_path'] = str(output_file.absolute())
                    
                    # Extract text explanation
                    elif hasattr(part, 'text') and part.text:
                        result['text'] = part.text
        
        if 'image_data' not in result:
            result['success'] = False
            result['error'] = "No image data in response"
        
        return result
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "message": f"Failed to generate image: {e}"
        }


@capability(
    name="generate_image_batch",
    description="Generate multiple images from a list of prompts using Google Gemini API",
    capability_type="function",
    tags=["image", "generation", "gemini", "batch"],
    strict_mode=False
)
async def generate_image_batch(
    prompts: List[str],
    aspect_ratio: str = "16:9",
    image_size: str = "2K",
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate multiple images from a list of prompts
    
    Args:
        prompts: List of text descriptions
        aspect_ratio: Aspect ratio for all images
        image_size: Image size for all images
        output_dir: Optional directory to save images
    
    Returns:
        Dictionary containing:
        - success: Whether all generations were successful
        - results: List of individual results
        - success_count: Number of successful generations
        - failed_count: Number of failed generations
    """
    results = []
    success_count = 0
    failed_count = 0
    
    for i, prompt in enumerate(prompts):
        output_path = None
        if output_dir:
            output_path = os.path.join(output_dir, f"image_{i+1}.png")
        
        result = await generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            output_path=output_path,
            include_text=False
        )
        
        if result.get("success"):
            success_count += 1
        else:
            failed_count += 1
        
        results.append({
            "prompt": prompt,
            "result": result
        })
    
    return {
        "success": failed_count == 0,
        "total": len(prompts),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results
    }


__all__ = ["generate_image", "generate_image_batch"]