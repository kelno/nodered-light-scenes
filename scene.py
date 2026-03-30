import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


# light data such as {"brightness":254,"color":{"x":0.47203459634857003,"y":0.410156969657555},"color_mode":"xy","color_temp":395,"state":"ON"}
@dataclass(frozen=True)
class LightData:
    brightness: int
    color: dict[str, float]
    color_mode: str
    color_temp: str
    state: str


@dataclass(frozen=True)
class Scene:
    """Represents a light scene configuration."""

    name: str
    lights: dict[str, LightData] = field(default_factory=dict)

    def lights_to_json(self) -> str:
        return json.dumps({name: asdict(light) for name, light in self.lights.items()})


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
        console_handler = logging.StreamHandler(sys.stderr)  # only output in err, keep stdout clear
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

            for scene_name, scene_data in data.items():
                lights: dict[str, LightData] = {}
                if isinstance(scene_data, dict):
                    raw_lights = scene_data.get("lights")
                    if isinstance(raw_lights, dict):
                        for light_name, payload in raw_lights.items():
                            if isinstance(payload, dict) and (light := self._parse_light_data(light_name, payload)):
                                lights[light_name] = light

                self.scenes[scene_name] = Scene(name=scene_name, lights=lights)
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

    def get_scene(self, scene_name: str) -> Scene | None:
        """Return scene data in json format"""
        if scene_name not in self.scenes:
            self.logger.warning(f"Scene '{scene_name}' not found")
            return None

        return self.scenes[scene_name]

    def _parse_light_data(self, light_name: str, data: dict) -> LightData | None:
        """Parse a raw light data payload into LightData (ignore extra fields)."""
        try:
            brightness = int(data["brightness"])
            color = data["color"]
            if not isinstance(color, dict):
                raise ValueError("color must be object")
            color_clean = {str(k): float(v) for k, v in color.items()}
            color_mode = str(data["color_mode"])
            color_temp = str(data["color_temp"])
            state = str(data["state"])
        except KeyError as e:
            self.logger.warning(f"Skipping light '{light_name}': missing required field {e}")
            return None
        except (TypeError, ValueError) as e:
            self.logger.warning(f"Skipping light '{light_name}': invalid data {e}")
            return None

        return LightData(
            brightness=brightness,
            color=color_clean,
            color_mode=color_mode,
            color_temp=color_temp,
            state=state,
        )

    def _load_scene_lights_from_file(self, source_path: Path) -> dict[str, LightData] | None:
        """Load light definitions from a source JSON file."""
        if not source_path.exists():
            self.logger.error(f"Source file not found: {source_path}")
            return None

        try:
            with open(source_path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            if not isinstance(raw, dict):
                self.logger.error(f"Invalid scene source format in {source_path}, expected object")
                return None

            lights: dict[str, LightData] = {}
            for light_name, payload in raw.items():
                if not isinstance(payload, dict):
                    self.logger.warning(f"Skipping light '{light_name}' because payload is not an object")
                    continue

                if light := self._parse_light_data(light_name, payload):
                    lights[light_name] = light

            if not lights:
                self.logger.error("No valid lights found in source file")
                return None

            return lights

        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Error reading source file {source_path}: {e}")
            return None

    def create_scene(self, scene_name, source_path: Path) -> bool:
        """Create a new scene by reading light data from source JSON."""
        if scene_name in self.scenes:
            self.logger.warning(f"Scene '{scene_name}' already exists")
            return False

        lights = self._load_scene_lights_from_file(source_path)
        if lights is None:
            return False

        self.scenes[scene_name] = Scene(name=scene_name, lights=lights)
        self._save_scenes()
        self.logger.info(f"Created scene '{scene_name}' with {len(lights)} lights")
        return True

    def update_scene(self, scene_name, source_path: Path) -> bool:
        """Update an existing scene by reading light data from source JSON."""
        if scene_name not in self.scenes:
            self.logger.warning(f"Scene '{scene_name}' not found")
            return False

        lights = self._load_scene_lights_from_file(source_path)
        if lights is None:
            return False

        self.scenes[scene_name] = Scene(name=scene_name, lights=lights)
        self._save_scenes()
        self.logger.info(f"Updated scene '{scene_name}' with {len(lights)} lights")
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


def main() -> None:
    """Main entry point."""
    script_dir = Path(__file__).parent
    scenes_file = script_dir / "scenes.json"
    log_file = script_dir / "scene.log"

    manager = SceneManager(scenes_file, log_file)

    parser = argparse.ArgumentParser(description="Manage light scenes")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("list", help="Get list of available scenes")

    create_parser = subparsers.add_parser("create", help="Create a new scene")
    create_parser.add_argument("scene_name", help="Name of the scene to create")
    create_parser.add_argument("--source", required=True, help="Path to source JSON file to create scene from")

    update_parser = subparsers.add_parser("update", help="Update a scene")
    update_parser.add_argument("scene_name", help="Name of the scene to update")
    update_parser.add_argument("--source", required=True, help="Path to source JSON file to update scene from")

    delete_parser = subparsers.add_parser("delete", help="Delete a scene")
    delete_parser.add_argument("scene_name", help="Name of the scene to delete")

    delete_parser = subparsers.add_parser("get", help="Get a scene data")
    delete_parser.add_argument("scene_name", help="Name of the scene to get")

    args = parser.parse_args()

    success = True

    if args.command == "list":
        print(manager.list_scenes())
    elif args.command == "create":
        success = manager.create_scene(args.scene_name, Path(args.source))
    elif args.command == "update":
        success = manager.update_scene(args.scene_name, Path(args.source))
    elif args.command == "delete":
        success = manager.delete_scene(args.scene_name)
    elif args.command == "get":
        if scene := manager.get_scene(args.scene_name):
            print(scene.lights_to_json())
            success = True
        else:
            print("{}")
            success = False
    else:
        parser.print_help()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
