from copy import deepcopy


class ConversationState:
    def __init__(self):
        self.raw_input = {}

    def merge(self, new_data: dict):
        self.raw_input = self._deep_merge(self.raw_input, new_data)

    def reset(self):
        self.raw_input = {}

    def _deep_merge(self, old, new):
        result = deepcopy(old)
        for k, v in new.items():
            if isinstance(v, dict):
                result[k] = self._deep_merge(result.get(k, {}), v)
            else:
                result[k] = v
        return result
