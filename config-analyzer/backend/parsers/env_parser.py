"""Section-by-section extractor for IsaacLab env.yaml configuration files.

Extracts structured data from the ~1720-line env.yaml focusing on:
- Rewards (positive/negative with weights)
- Events (domain randomization)
- Commands (gait_command, base_velocity)
- Observations (policy, critic, commands, obsHistory)
- Actuators (legs, ankles with stiffness/damping)
- Sim/MDP parameters
- Terminations
"""

import json
from pathlib import Path
from typing import Any

from backend.parsers.yaml_cleaner import safe_load_yaml


class EnvConfigParser:
    """Parse and extract key sections from env.yaml."""

    def __init__(self, yaml_path: str):
        self.data = safe_load_yaml(yaml_path)
        self._func_cache = {}

    @staticmethod
    def _shorten_func(func_full: str) -> str:
        """Extract short function name from full module path."""
        if not func_full:
            return ''
        if ':' in func_full:
            return func_full.split(':')[-1].split('.')[-1]
        return func_full.split('.')[-1]

    @staticmethod
    def _simplify_params(params: dict) -> dict:
        """Filter params down to meaningful scalar/short-list values."""
        if not isinstance(params, dict):
            return {}
        simplified = {}
        for k, v in params.items():
            if isinstance(v, (str, int, float, bool)):
                simplified[k] = v
            elif isinstance(v, list) and len(v) <= 4:
                simplified[k] = v
            elif v is None:
                continue
            elif k in ('asset_cfg', 'sensor_cfg'):
                sub = {}
                if isinstance(v, dict):
                    for sk in ('body_names', 'joint_names', 'name'):
                        if sk in v:
                            sub[sk] = v[sk]
                if sub:
                    simplified[k] = sub
        return simplified

    # ---- Rewards ----

    def extract_rewards(self) -> list[dict]:
        """Extract reward/penalty terms with weights and params."""
        rewards = self.data.get('rewards', {})
        terms = []
        for name, cfg in rewards.items():
            if not isinstance(cfg, dict):
                continue
            func_short = self._shorten_func(cfg.get('func', ''))
            weight = cfg.get('weight', 0.0)
            params = self._simplify_params(cfg.get('params', {}))
            category = 'reward' if weight > 0 else ('penalty' if weight < 0 else 'neutral')
            terms.append({
                'term_name': name,
                'func': func_short,
                'weight': weight,
                'category': category,
                'params_summary': params,
            })
        return terms

    # ---- Events ----

    def extract_events(self) -> list[dict]:
        """Extract domain randomization events."""
        events = self.data.get('events', {})
        result = []
        for name, cfg in events.items():
            if not isinstance(cfg, dict):
                continue
            mode = cfg.get('mode', 'unknown')
            func_short = self._shorten_func(cfg.get('func', ''))
            params = self._simplify_params(cfg.get('params', {}))
            result.append({
                'event_name': name,
                'func': func_short,
                'mode': mode,
                'params_summary': params,
            })
        return result

    # ---- Commands ----

    def extract_commands(self) -> dict:
        """Extract gait command and base velocity command configuration."""
        cmds = self.data.get('commands', {})
        result = {}
        for cmd_name, cmd_cfg in cmds.items():
            if not isinstance(cmd_cfg, dict):
                continue
            simplified = {}

            # Extract ranges
            ranges = cmd_cfg.get('ranges', {})
            if ranges:
                for rname, rval in ranges.items():
                    if isinstance(rval, (list, tuple)):
                        simplified[rname] = rval
                    else:
                        simplified[rname] = rval

            # Extract top-level scalars
            for key in ('resampling_time_range', 'heading_command',
                         'rel_standing_envs', 'rel_heading_envs',
                         'heading_control_stiffness'):
                if key in cmd_cfg and cmd_cfg[key] is not None:
                    simplified[key] = cmd_cfg[key]

            result[cmd_name] = simplified

        return result

    # ---- Observations ----

    def extract_observations(self) -> dict:
        """Extract observation groups and their features."""
        obs = self.data.get('observations', {})
        result = {}
        # Special keys that are group-level config, not features
        group_config_keys = {'concatenate_terms', 'enable_corruption',
                            'history_length', 'flatten_history_dim'}

        for group_name, group_cfg in obs.items():
            if not isinstance(group_cfg, dict):
                continue
            features = []
            for feat_name, feat_cfg in group_cfg.items():
                if feat_name in group_config_keys:
                    continue
                if not isinstance(feat_cfg, dict):
                    continue
                if 'func' in feat_cfg and feat_cfg['func'] is not None:
                    func_short = self._shorten_func(feat_cfg['func'])
                    noise_std = None
                    noise = feat_cfg.get('noise')
                    if isinstance(noise, dict):
                        noise_std = noise.get('std')
                    features.append({
                        'name': feat_name,
                        'func': func_short,
                        'scale': feat_cfg.get('scale'),
                        'noise_std': noise_std,
                        'history_length': feat_cfg.get('history_length'),
                    })

            result[group_name] = {
                'concatenate_terms': group_cfg.get('concatenate_terms'),
                'enable_corruption': group_cfg.get('enable_corruption'),
                'history_length': group_cfg.get('history_length'),
                'feature_count': len(features),
                'features': features,
            }
        return result

    # ---- Actuators ----

    def extract_actuators(self) -> list[dict]:
        """Extract actuator (joint drive) configuration."""
        robot = self.data.get('scene', {}).get('robot', {})
        actuators = robot.get('actuators', {})
        result = []
        for name, cfg in actuators.items():
            if not isinstance(cfg, dict):
                continue
            result.append({
                'group': name,
                'class_type': cfg.get('class_type', ''),
                'joints': cfg.get('joint_names_expr', []),
                'stiffness': cfg.get('stiffness'),
                'damping': cfg.get('damping'),
                'effort_limit': cfg.get('effort_limit'),
                'velocity_limit': cfg.get('velocity_limit'),
            })
        return result

    # ---- Sim Parameters ----

    def extract_sim_params(self) -> dict:
        """Extract simulation and MDP parameters."""
        sim = self.data.get('sim', {})
        scene = self.data.get('scene', {})
        terrain = scene.get('terrain', {})
        robot = scene.get('robot', {})

        # Get episode length
        episode_length_s = self.data.get('episode_length_s')
        if episode_length_s is None:
            # Infer: dt * decimation * num_steps_per_env (from agent.yaml)
            episode_length_s = None

        return {
            'decimation': self.data.get('decimation'),
            'dt': sim.get('dt'),
            'num_envs': scene.get('num_envs'),
            'env_spacing': scene.get('env_spacing'),
            'episode_length_s': episode_length_s,
            'seed': self.data.get('seed'),
            'terrain_type': terrain.get('terrain_type') if isinstance(terrain, dict) else None,
            'gravity': sim.get('gravity'),
            'render_interval': sim.get('render_interval'),
            'device': sim.get('device'),
            'use_fabric': sim.get('use_fabric'),
            'is_finite_horizon': self.data.get('is_finite_horizon'),
            'rerender_on_reset': self.data.get('rerender_on_reset'),
        }

    # ---- Robot Init State ----

    def extract_robot_init_state(self) -> dict:
        """Extract robot initial state configuration."""
        robot = self.data.get('scene', {}).get('robot', {})
        init = robot.get('init_state', {})
        if not isinstance(init, dict):
            return {}
        return {
            'pos': init.get('pos'),
            'rot': init.get('rot'),
            'joint_pos': init.get('joint_pos'),
            'soft_joint_pos_limit_factor': robot.get('soft_joint_pos_limit_factor'),
        }

    # ---- Terminations ----

    def extract_terminations(self) -> list[dict]:
        """Extract termination conditions."""
        terms = self.data.get('terminations', {})
        result = []
        for name, cfg in terms.items():
            if not isinstance(cfg, dict):
                continue
            result.append({
                'name': name,
                'func': self._shorten_func(cfg.get('func', '')),
                'time_out': cfg.get('time_out', False),
                'params_summary': self._simplify_params(cfg.get('params', {})),
            })
        return result

    # ---- Full extraction ----

    def extract_all(self) -> dict:
        """Extract all key sections into a single structured dict."""
        return {
            'sim_params': self.extract_sim_params(),
            'robot_init_state': self.extract_robot_init_state(),
            'rewards': self.extract_rewards(),
            'events': self.extract_events(),
            'commands': self.extract_commands(),
            'observations': self.extract_observations(),
            'actuators': self.extract_actuators(),
            'terminations': self.extract_terminations(),
        }

    # ---- Flatten for config_params table ----

    def flatten_to_params(self, run_id: int) -> list[dict]:
        """Flatten key sections into (section, param_path, value) rows."""
        params = []

        # Sim params
        sim = self.extract_sim_params()
        for k, v in sim.items():
            if v is not None:
                params.append(self._make_param('env.sim', f'sim.{k}', k, v))

        # Rewards
        for term in self.extract_rewards():
            params.append(self._make_param(
                'env.rewards', f'rewards.{term["term_name"]}.weight',
                'weight', term['weight']))
            params.append(self._make_param(
                'env.rewards', f'rewards.{term["term_name"]}.func',
                'func', term['func']))

        # Events
        for event in self.extract_events():
            params.append(self._make_param(
                'env.events', f'events.{event["event_name"]}.mode',
                'mode', event['mode']))

        # Commands
        cmds = self.extract_commands()
        for cmd_name, cmd_cfg in cmds.items():
            for k, v in cmd_cfg.items():
                if v is not None and not isinstance(v, dict):
                    params.append(self._make_param(
                        'env.commands', f'commands.{cmd_name}.{k}', k, v))

        # Actuators
        for act in self.extract_actuators():
            for key in ('stiffness', 'damping', 'effort_limit', 'velocity_limit'):
                if act.get(key) is not None:
                    params.append(self._make_param(
                        'env.actuators', f'actuators.{act["group"]}.{key}',
                        key, act[key]))

        return params

    @staticmethod
    def _make_param(section: str, param_path: str, param_name: str, value: Any) -> dict:
        from backend.utils import type_name
        vtype = type_name(value)
        if isinstance(value, list):
            import json
            vtext = json.dumps(value)
        else:
            vtext = str(value) if value is not None else ''
        return {
            'section': section,
            'param_path': param_path,
            'param_name': param_name,
            'value_text': vtext,
            'value_type': vtype,
        }
