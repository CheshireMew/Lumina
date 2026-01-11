import os
import logging
import yaml
from typing import Dict, Any, Optional, Union
from pathlib import Path
from jinja2 import Template, Environment, FileSystemLoader

logger = logging.getLogger("PromptManager")

class PromptManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        # Determine base path
        # In PyInstaller frozen state, sys._MEIPASS should be used if bundling,
        # but here we rely on file system for hot-reloading if possible, 
        # or fallback to relative path.
        import sys
        
        if getattr(sys, 'frozen', False):
            # If frozen, we expect prompts to be in a specific resource dir
            # But we want to allow user overrides?
            # For now, stick to internal resources.
            base_dir = Path(sys._MEIPASS) / "python_backend" # type: ignore
        else:
            base_dir = Path(__file__).parent.absolute()
            
        self.prompts_dir = base_dir / "prompts"
        logger.info(f"[PromptManager] Initialized with prompts dir: {self.prompts_dir}")
        
        # Configure Jinja2 Env
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            autoescape=False # Prompts are text, not HTML
        )
        
    def render(self, template_name: str, context: Dict[str, Any] = {}) -> str:
        """
        Render a template file with context variables.
        template_name can be "chat/system.yaml" or "memory/extract.txt"
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"[PromptManager] Failed to render template '{template_name}': {e}")
            return f"(Render Error: {e})"

    def load_structured(self, template_name: str, context: Dict[str, Any] = {}) -> Union[Dict, str]:
        """
        Render a YAML/JSON template and parse it into a Python dict.
        """
        content = self.render(template_name, context)
        if not content:
            return {}
            
        try:
            if template_name.endswith('.yaml') or template_name.endswith('.yml'):
                return yaml.safe_load(content)
            elif template_name.endswith('.json'):
                import json
                return json.loads(content)
        except Exception as e:
            logger.error(f"[PromptManager] Failed to parse structured template '{template_name}': {e}")
            return content
            
        return content

# Global Instance
prompt_manager = PromptManager()
