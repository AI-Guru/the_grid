

texts = {
    "action_success": {
        "de": "Aktion erfolgreich!"
    },
    "action_failure_cause": {
        "de": "Aktion fehlgeschlagen: {}"
    },
    "action_failure_cause_cell_not_empty": {
        "de": "Der Weg ist blockiert!"
    },
    "action_failure_cause_entity_blocking": {
        "de": "Der Weg ist blockiert!"
    },
    "plan_generated": {
        "de": "Ich habe einen Plan: {}"
    },
    # Actions.
    "action_left": {
        "de": "Links"
    },
    "action_right": {
        "de": "Rechts"
    },
    "action_up": {
        "de": "Hoch"
    },
    "action_down": {
        "de": "Runter"
    },
    "action_pickup": {
        "de": "Aufheben"
    },
    "action_drop": {
        "de": "Ablegen"
    },
}

class TextDictionary:
    def __init__(self, language="de"):
        self.language = language
        self.dictionary = {}

    def get(self, key):

        if key in texts:
            if self.language in texts[key]:
                return texts[key][self.language]
            else:
                raise KeyError(f"Language {self.language} not found in dictionary for key {key}")
        else:
            raise KeyError(f"Key {key} not found in dictionary")

