"""
Combiner Node for ComfyUI
Combine character + clothing + pose with independent iteration and random
"""

import random as _random
import re

WEB_DIRECTORY = "./web"

ITERATOR_STATE = {}


class CombinerNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "characters": ("STRING", {
                    "multiline": True,
                    "default": "Tohru\nKanna\nLucoa",
                    "dynamicPrompts": False
                }),
                "clothing": ("STRING", {
                    "multiline": True,
                    "default": "maid outfit\nschool uniform\ncasual clothes\nbikini",
                    "dynamicPrompts": False
                }),
                "poses": ("STRING", {
                    "multiline": True,
                    "default": "standing\nsitting\nlying down\njumping",
                    "dynamicPrompts": False
                }),
                "separator": ("STRING", {
                    "default": ", ",
                    "multiline": False
                }),
            },
            "optional": {
                "iterate_character": ("BOOLEAN", {
                    "default": False,
                    "label_on": "Iterate",
                    "label_off": "Index 0"
                }),
                "iterate_clothing": ("BOOLEAN", {
                    "default": False,
                    "label_on": "Iterate",
                    "label_off": "Index 0"
                }),
                "iterate_pose": ("BOOLEAN", {
                    "default": False,
                    "label_on": "Iterate",
                    "label_off": "Index 0"
                }),
                "random_character": ("BOOLEAN", {
                    "default": False,
                    "label_on": "Random",
                    "label_off": "Sequential"
                }),
                "random_clothing": ("BOOLEAN", {
                    "default": False,
                    "label_on": "Random",
                    "label_off": "Sequential"
                }),
                "random_pose": ("BOOLEAN", {
                    "default": False,
                    "label_on": "Random",
                    "label_off": "Sequential"
                }),
                "character_index": ("INT", {
                    "default": 0, "min": 0, "max": 999, "step": 1
                }),
                "clothing_index": ("INT", {
                    "default": 0, "min": 0, "max": 999, "step": 1
                }),
                "pose_index": ("INT", {
                    "default": 0, "min": 0, "max": 999, "step": 1
                }),
                "reset": ("BOOLEAN", {
                    "default": False,
                    "label_on": "Reset",
                    "label_off": "Continue"
                }),
                "workflow_id": ("STRING", {
                    "default": "default",
                    "multiline": False
                }),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "STRING")
    RETURN_NAMES = ("prompt", "step", "total", "status")
    FUNCTION = "combine"
    CATEGORY = "iteration"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def _parse(self, text):
        import re
        cleaned = re.sub(r'^\[\d+\]\s*', '', text.strip(), flags=re.MULTILINE)
        return [x.strip() for x in cleaned.split("\n") if x.strip()]

    def _pick_index(self, items, do_iterate, do_random, manual_idx, step, is_random_dim):
        """Pick index for a category based on mode."""
        if not items:
            return 0
        if do_random:
            return _random.randint(0, len(items) - 1)
        if do_iterate:
            return step % len(items)
        return min(manual_idx, len(items) - 1)

    def combine(self, characters, clothing, poses, separator=", ",
                iterate_character=False, iterate_clothing=False, iterate_pose=False,
                random_character=False, random_clothing=False, random_pose=False,
                character_index=0, clothing_index=0, pose_index=0,
                reset=False, workflow_id="default"):

        global ITERATOR_STATE

        chars = self._parse(characters)
        clothes = self._parse(clothing)
        pos = self._parse(poses)

        if not chars:
            chars = [""]
        if not clothes:
            clothes = [""]
        if not pos:
            pos = [""]

        # calculate total
        # random dims don't count toward total (infinite)
        iter_dims = []
        if iterate_character and not random_character:
            iter_dims.append(len(chars))
        if iterate_clothing and not random_clothing:
            iter_dims.append(len(clothes))
        if iterate_pose and not random_pose:
            iter_dims.append(len(pos))

        total = 1
        for size in iter_dims:
            total *= size

        has_random = random_character or random_clothing or random_pose
        if has_random and total == 1 and not iter_dims:
            total = 0  # 0 = infinite, random only

        # state
        if workflow_id not in ITERATOR_STATE:
            ITERATOR_STATE[workflow_id] = 0

        state = ITERATOR_STATE

        if reset:
            state[workflow_id] = 0

        idx = state[workflow_id]

        if total > 0 and idx >= total:
            idx = 0
            state[workflow_id] = 0

        # sequential dims: calculate sub-indices from global idx
        seq_dims = []
        if iterate_character and not random_character:
            seq_dims.append("char")
        if iterate_clothing and not random_clothing:
            seq_dims.append("cloth")
        if iterate_pose and not random_pose:
            seq_dims.append("pose")

        seq_offsets = {}
        if seq_dims:
            dim_sizes = []
            if iterate_character and not random_character:
                dim_sizes.append(len(chars))
            if iterate_clothing and not random_clothing:
                dim_sizes.append(len(clothes))
            if iterate_pose and not random_pose:
                dim_sizes.append(len(pos))

            remaining = idx
            calc_offsets = []
            for size in reversed(dim_sizes):
                calc_offsets.append(remaining % size)
                remaining //= size
            calc_offsets.reverse()

            oi = 0
            if iterate_character and not random_character:
                seq_offsets["char"] = calc_offsets[oi]
                oi += 1
            if iterate_clothing and not random_clothing:
                seq_offsets["cloth"] = calc_offsets[oi]
                oi += 1
            if iterate_pose and not random_pose:
                seq_offsets["pose"] = calc_offsets[oi]

        # pick indices
        if random_character:
            char_i = _random.randint(0, len(chars) - 1)
        elif iterate_character:
            char_i = seq_offsets.get("char", idx % len(chars))
        else:
            char_i = min(character_index, len(chars) - 1)

        if random_clothing:
            cloth_i = _random.randint(0, len(clothes) - 1)
        elif iterate_clothing:
            cloth_i = seq_offsets.get("cloth", idx % len(clothes))
        else:
            cloth_i = min(clothing_index, len(clothes) - 1)

        if random_pose:
            pose_i = _random.randint(0, len(pos) - 1)
        elif iterate_pose:
            pose_i = seq_offsets.get("pose", idx % len(pos))
        else:
            pose_i = min(pose_index, len(pos) - 1)

        # build prompt
        parts = []
        if chars[char_i]:
            parts.append(chars[char_i])
        if clothes[cloth_i]:
            parts.append(clothes[cloth_i])
        if pos[pose_i]:
            parts.append(pos[pose_i])

        prompt = separator.join(parts)

        state[workflow_id] = idx + 1

        # status
        def cat_label(name, items, idx, is_iter, is_rand):
            item = items[idx] if items and idx < len(items) else "?"
            if is_rand:
                return f"{name}(random): {item}"
            elif is_iter:
                return f"{name}({idx+1}/{len(items)}): {item}"
            else:
                return f"{name}(fixed): {item}"

        step_str = f"Step {idx+1}"
        if total > 0:
            step_str += f"/{total}"
        else:
            step_str += "/??"

        status_parts = [
            step_str,
            cat_label("Char", chars, char_i, iterate_character, random_character),
            cat_label("Cloth", clothes, cloth_i, iterate_clothing, random_clothing),
            cat_label("Pose", pos, pose_i, iterate_pose, random_pose),
        ]

        status = " | ".join(status_parts)

        print(f"[Combiner] {status}")

        return (prompt, idx + 1, total, status)


NODE_CLASS_MAPPINGS = {
    "CombinerNode": CombinerNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CombinerNode": "Combiner",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']

print("[ComfyUI-iterationNode] Loaded: Combiner")
