"""Parse IsaacLab agent.yaml configuration files.

Extracts algorithm hyperparameters, network architecture, encoder config, etc.
"""

import json
from pathlib import Path
from typing import Any

from backend.parsers.yaml_cleaner import safe_load_yaml


class AgentConfigParser:
    """Parse agent.yaml and extract structured configuration."""

    def __init__(self, yaml_path: str):
        self.data = safe_load_yaml(yaml_path)

    def extract(self) -> dict:
        """Extract all agent configuration as a flat dict."""
        algo = self.data.get('algorithm', {})
        policy = self.data.get('policy', {})
        encoder = self.data.get('encoder', {})

        actor_dims = policy.get('actor_hidden_dims', [])
        critic_dims = policy.get('critic_hidden_dims', [])
        encoder_dims = encoder.get('hidden_dims', [])

        return {
            'algorithm': algo.get('class_name', ''),
            'learning_rate': algo.get('learning_rate'),
            'gamma': algo.get('gamma'),
            'lam': algo.get('lam'),
            'entropy_coef': algo.get('entropy_coef'),
            'desired_kl': algo.get('desired_kl'),
            'max_grad_norm': algo.get('max_grad_norm'),
            'value_loss_coef': algo.get('value_loss_coef'),
            'clip_param': algo.get('clip_param'),
            'num_learning_epochs': algo.get('num_learning_epochs'),
            'num_mini_batches': algo.get('num_mini_batches'),
            'schedule': algo.get('schedule'),
            'max_iterations': self.data.get('max_iterations'),
            'num_steps': self.data.get('num_steps_per_env'),
            'seed': self.data.get('seed'),
            'experiment_name': self.data.get('experiment_name'),
            'actor_dims': actor_dims,
            'critic_dims': critic_dims,
            'activation': policy.get('activation', ''),
            'init_noise_std': policy.get('init_noise_std'),
            'obs_history_len': (algo.get('obs_history_len') or
                               self.data.get('obs_history_len')),
            'encoder_dims': encoder_dims,
            'encoder_output_dim': encoder.get('num_output_dim'),
            'resume': 1 if self.data.get('resume') else 0,
            'load_run': self.data.get('load_run'),
            'save_interval': self.data.get('save_interval'),
        }

    def flatten_to_params(self, run_id: int) -> list[dict]:
        """Flatten agent config into config_params format."""
        from backend.utils import type_name
        config = self.extract()
        params = []
        for key, value in config.items():
            if value is None:
                continue
            if isinstance(value, list):
                vtext = json.dumps(value)
                vtype = 'list'
            else:
                vtext = str(value)
                vtype = type_name(value)
            params.append({
                'section': 'agent',
                'param_path': f'agent.{key}',
                'param_name': key,
                'value_text': vtext,
                'value_type': vtype,
            })
        return params
