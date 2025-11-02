import yaml
from logger import PM


class yamlconfig():
    def __init__(self):
        self.base_path = PM.base_path
        self.config = "config.yaml"
        self.feeds = "feeds.yaml"

    def config_yaml(self):
        with open(self.base_path / "config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def feeds_yaml(self):
        with open(self.base_path / "feeds.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)


if __name__ == "__main__":
    print(yamlconfig().feeds_yaml())