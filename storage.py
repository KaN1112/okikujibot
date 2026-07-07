import json
import os

COOLDOWN_FILE = "cooldown.json"
FORCE_FILE = "force_result.json"


def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


class DataManager:

    def __init__(self):
        self.cooldown = load_json(COOLDOWN_FILE)
        self.force = load_json(FORCE_FILE)

    # ------------------------
    # クールタイム
    # ------------------------

    def get_cooldown(self):
        return self.cooldown

    def save_cooldown(self):
        save_json(COOLDOWN_FILE, self.cooldown)

    # ------------------------
    # 強制運勢
    # ------------------------

    def get_force(self, user_id):

        return self.force.get(str(user_id))

    def set_force(self, user_id, result, permanent=False):

        self.force[str(user_id)] = {
            "result": result,
            "permanent": permanent
        }

        save_json(FORCE_FILE, self.force)

    def clear_force(self, user_id):

        uid = str(user_id)

        if uid in self.force:
            del self.force[uid]
            save_json(FORCE_FILE, self.force)

    def consume_force(self, user_id):

        uid = str(user_id)

        if uid not in self.force:
            return None

        data = self.force[uid]

        if not data["permanent"]:
            del self.force[uid]
            save_json(FORCE_FILE, self.force)

        return data["result"]

    def get_all_force(self):
        return self.force
