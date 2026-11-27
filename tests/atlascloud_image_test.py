import yaml

from backend.generators.atlascloud_image import AtlasCloudImageGenerator
from backend.generators.factory import ImageGeneratorFactory


class FakeResponse:
    def __init__(self, status_code=200, payload=None, content=b"", text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content
        self.text = text

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.posts = []
        self.gets = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.posts.append({
            "url": url,
            "headers": headers,
            "json": json,
            "timeout": timeout,
        })
        return FakeResponse(payload={
            "code": 200,
            "data": {
                "id": "prediction_123",
                "status": "starting",
            },
        })

    def get(self, url, headers=None, timeout=None):
        self.gets.append({
            "url": url,
            "headers": headers,
            "timeout": timeout,
        })
        if url.endswith("/model/result/prediction_123"):
            return FakeResponse(payload={
                "code": 200,
                "data": {
                    "id": "prediction_123",
                    "status": "completed",
                    "outputs": ["https://cdn.example.com/generated.png"],
                },
            })
        return FakeResponse(content=b"image-bytes")


class PredictionFallbackSession(FakeSession):
    def get(self, url, headers=None, timeout=None):
        self.gets.append({
            "url": url,
            "headers": headers,
            "timeout": timeout,
        })
        if url.endswith("/model/result/prediction_123"):
            return FakeResponse(status_code=404, text="not found")
        if url.endswith("/model/prediction/prediction_123"):
            return FakeResponse(payload={
                "data": {
                    "id": "prediction_123",
                    "status": "completed",
                    "outputs": ["data:image/png;base64,aW1hZ2UtYnl0ZXM="],
                },
            })
        return FakeResponse(content=b"image-bytes")


def test_atlascloud_image_generator_submits_polls_and_downloads():
    session = FakeSession()
    generator = AtlasCloudImageGenerator({
        "api_key": "ak-test",
        "base_url": "https://api.atlascloud.ai/api/v1",
        "model": "bytedance/seedream-v5.0-lite",
        "size": "1728*2304",
        "output_format": "png",
        "poll_interval_seconds": 0,
        "max_poll_attempts": 2,
    })
    generator.session = session

    image = generator.generate_image("生成一张小红书封面")

    assert image == b"image-bytes"
    assert session.posts[0]["url"] == "https://api.atlascloud.ai/api/v1/model/generateImage"
    assert session.posts[0]["headers"]["Authorization"] == "Bearer ak-test"
    assert session.posts[0]["json"] == {
        "model": "bytedance/seedream-v5.0-lite",
        "prompt": "生成一张小红书封面",
        "size": "1728*2304",
        "output_format": "png",
        "enable_base64_output": False,
    }
    assert session.gets[0]["url"] == "https://api.atlascloud.ai/api/v1/model/result/prediction_123"
    assert session.gets[1]["url"] == "https://cdn.example.com/generated.png"


def test_atlascloud_image_generator_falls_back_to_prediction_poll_path():
    session = PredictionFallbackSession()
    generator = AtlasCloudImageGenerator({
        "api_key": "ak-test",
        "base_url": "https://api.atlascloud.ai/api/v1",
        "poll_interval_seconds": 0,
    })
    generator.session = session

    image = generator.generate_image("生成一张小红书封面")

    assert image == b"image-bytes"
    assert session.gets[0]["url"] == "https://api.atlascloud.ai/api/v1/model/result/prediction_123"
    assert session.gets[1]["url"] == "https://api.atlascloud.ai/api/v1/model/prediction/prediction_123"


def test_atlascloud_image_generator_supports_data_url_output():
    generator = AtlasCloudImageGenerator({
        "api_key": "ak-test",
        "poll_interval_seconds": 0,
    })

    assert generator._read_output("data:image/png;base64,aW1hZ2UtYnl0ZXM=") == b"image-bytes"


def test_factory_registers_atlascloud_image_generator():
    generator = ImageGeneratorFactory.create("atlascloud_image", {"api_key": "ak-test"})

    assert isinstance(generator, AtlasCloudImageGenerator)


def test_atlascloud_provider_examples_are_valid_yaml():
    with open("image_providers.yaml.example", "r", encoding="utf-8") as f:
        image_config = yaml.safe_load(f)
    with open("text_providers.yaml.example", "r", encoding="utf-8") as f:
        text_config = yaml.safe_load(f)

    image_provider = image_config["providers"]["atlascloud"]
    text_provider = text_config["providers"]["atlascloud"]

    assert image_provider["type"] == "atlascloud_image"
    assert image_provider["base_url"] == "https://api.atlascloud.ai/api/v1"
    assert image_provider["model"] == "bytedance/seedream-v5.0-lite"
    assert image_provider["size"] == "1728*2304"
    assert text_provider["type"] == "openai_compatible"
    assert text_provider["base_url"] == "https://api.atlascloud.ai/v1"
    assert text_provider["model"] == "qwen/qwen3.5-flash"
