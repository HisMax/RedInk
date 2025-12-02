"""ModelScope Z-Image Generator"""
import time
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)

class ModelScopeGenerator(ImageGeneratorBase):
    """ModelScope Z-Image Generator"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://api-inference.modelscope.cn/')
        self.model = config.get('model', 'Tongyi-MAI/Z-Image-Turbo')
        # Default polling interval in seconds
        self.polling_interval = config.get('polling_interval', 2)
        # Maximum wait time in seconds
        self.timeout = config.get('timeout', 60)

    def validate_config(self) -> bool:
        """Validate configuration"""
        if not self.api_key:
            raise ValueError("ModelScope API Key is required")
        return True

    def generate_image(
        self,
        prompt: str,
        **kwargs
    ) -> bytes:
        """
        Generate image using ModelScope Z-Image model
        
        Args:
            prompt: Image prompt
            **kwargs: Other parameters
            
        Returns:
            Image bytes
        """
        self.validate_config()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-ModelScope-Async-Mode": "true"
        }

        # Ensure base_url ends with /
        base_url = self.base_url if self.base_url.endswith('/') else f"{self.base_url}/"
        
        # Check prompt length and truncate if necessary
        # ModelScope Z-Image has a limit of ~2000 characters
        MAX_PROMPT_LENGTH = 1800
        if len(prompt) > MAX_PROMPT_LENGTH:
            logger.warning(f"Prompt length ({len(prompt)}) exceeds limit ({MAX_PROMPT_LENGTH}). Truncating...")
            prompt = prompt[:MAX_PROMPT_LENGTH]
        
        payload = {
            "model": self.model,
            "prompt": prompt
        }
        
        # Add optional parameters if needed, e.g., negative_prompt, etc.
        # Currently keeping it simple as per user request
        
        logger.info(f"Submitting ModelScope task for model: {self.model}")
        
        try:
            response = requests.post(
                f"{base_url}v1/images/generations",
                headers=headers,
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"ModelScope API Error: {response.status_code} - {response.text}")
            
            response.raise_for_status()
            task_id = response.json()["task_id"]
            logger.info(f"Task submitted successfully, ID: {task_id}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to submit task: {e}")
            if hasattr(e, 'response') and e.response is not None:
                 logger.error(f"Error Response Content: {e.response.text}")
            raise

        # Poll for results
        start_time = time.time()
        while True:
            if time.time() - start_time > self.timeout:
                raise TimeoutError(f"Image generation timed out after {self.timeout} seconds")
                
            try:
                result_response = requests.get(
                    f"{base_url}v1/tasks/{task_id}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "X-ModelScope-Task-Type": "image_generation"
                    },
                    timeout=10
                )
                result_response.raise_for_status()
                data = result_response.json()
                
                task_status = data.get("task_status")
                
                if task_status == "SUCCEED":
                    output_url = data["output_images"][0]
                    logger.info("Task succeeded, downloading image...")
                    image_response = requests.get(output_url, timeout=30)
                    image_response.raise_for_status()
                    return image_response.content
                    
                elif task_status == "FAILED":
                    error_msg = data.get("message", "Unknown error")
                    logger.error(f"Task failed: {error_msg}")
                    raise RuntimeError(f"Image generation failed: {error_msg}")
                
                # Wait before next poll
                time.sleep(self.polling_interval)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error while polling task status: {e}")
                # Don't break immediately on network error during polling, maybe retry?
                # For now, just re-raise or let it continue loop if temporary
                # If it's a persistent error, the timeout will eventually catch it
                time.sleep(self.polling_interval) 

    def get_supported_sizes(self) -> List[str]:
        return ["1024x1024"]  # Z-Image usually supports standard sizes

    def get_supported_aspect_ratios(self) -> List[str]:
        return ["1:1"] # Default to 1:1 for now
