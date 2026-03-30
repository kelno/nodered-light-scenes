import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Scene:
    """Represents a light scene configuration."""

    name: str


class SceneManager:
    """Manages scene operations and persistence."""

    def __init__(self, scenes_file: Path, log_file: Path):
        self.scenes_file = scenes_file
        self.log_file = log_file
        self.scenes: dict[str, Scene] = {}
        self._setup_logger()
        self._load_scenes()

    def _setup_logger(self) -> None:
        """Configure logger to output to both console and file."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        console_handler.setFormatter(console_formatter)

        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(file_formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def _load_scenes(self) -> None:
        """Load scenes from the JSON file."""
        if not self.scenes_file.exists():
            self.logger.debug(f"Scenes file not found, creating: {self.scenes_file}")
            self._save_scenes()
            return

        try:
            with open(self.scenes_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for scene_name, _scene_data in data.items():
                self.scenes[scene_name] = Scene(name=scene_name)
            self.logger.debug(f"Loaded {len(self.scenes)} scenes from {self.scenes_file}")
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Error loading scenes: {e}")
            self.scenes = {}

    def _save_scenes(self) -> None:
        """Save scenes to the JSON file."""
        data = {name: asdict(scene) for name, scene in self.scenes.items()}
        try:
            with open(self.scenes_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.logger.debug(f"Saved {len(self.scenes)} scenes to {self.scenes_file}")
        except IOError as e:
            self.logger.error(f"Error saving scenes: {e}")

    def list_scenes(self) -> str:
        """Return a JSON array of available scene names."""
        scene_names = list(self.scenes.keys())
        self.logger.info(f"Retrieved {len(scene_names)} scenes")
        return json.dumps(scene_names)

    def get_scene(self, scene_name: str) -> str:
        """Return scene data in json format"""
        if scene_name not in self.scenes:
            self.logger.warning(f"Scene '{scene_name}' not found")
            return "{}"

        return json.dumps(asdict(self.scenes[scene_name]))

    def create_scene(self, scene_name: str) -> bool:
        """Create a new scene."""
        if scene_name in self.scenes:
            self.logger.warning(f"Scene '{scene_name}' already exists")
            return False

        self.scenes[scene_name] = Scene(name=scene_name)
        self._save_scenes()
        self.logger.info(f"Created scene '{scene_name}'")
        return True

    def delete_scene(self, scene_name: str) -> bool:
        """Delete an existing scene."""
        if scene_name not in self.scenes:
            self.logger.warning(f"Scene '{scene_name}' not found")
            return False

        del self.scenes[scene_name]
        self._save_scenes()
        self.logger.info(f"Deleted scene '{scene_name}'")
        return True

    def apply_scene(self, scene_name: str) -> bool:
        """Apply a scene (stub for future implementation)."""
        if scene_name not in self.scenes:
            self.logger.error(f"Scene '{scene_name}' not found")
            return False

        self.logger.info(f"Applying scene '{scene_name}'")
        # TODO: Implement scene application logic
        return True


def main() -> None:
    """Main entry point."""
    script_dir = Path(__file__).parent
    scenes_file = script_dir / "scenes.json"
    log_file = script_dir / "scene.log"

    manager = SceneManager(scenes_file, log_file)

    parser = argparse.ArgumentParser(description="Manage light scenes")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("list", help="Get list of available scenes")

    apply_parser = subparsers.add_parser("apply", help="Apply a scene")
    apply_parser.add_argument("scene_name", help="Name of the scene to apply")

    create_parser = subparsers.add_parser("create", help="Create a new scene")
    create_parser.add_argument("scene_name", help="Name of the scene to create")
    create_parser.add_argument("--filename", default="", help="Filename for the scene")

    delete_parser = subparsers.add_parser("delete", help="Delete a scene")
    delete_parser.add_argument("scene_name", help="Name of the scene to delete")

    delete_parser = subparsers.add_parser("get", help="Get a scene data")
    delete_parser.add_argument("scene_name", help="Name of the scene to get")

    args = parser.parse_args()

    if args.command == "list":
        print(manager.list_scenes())
    elif args.command == "apply":
        manager.apply_scene(args.scene_name)
    elif args.command == "create":
        manager.create_scene(args.scene_name)
    elif args.command == "delete":
        manager.delete_scene(args.scene_name)
    elif args.command == "get":
        print(manager.get_scene(args.scene_name))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
