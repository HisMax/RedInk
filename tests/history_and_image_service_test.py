from pathlib import Path

from backend.services.history import HistoryService
from backend.services.image import ImageService
from backend.services.image_rate_limiter import ImageRateLimiter


def make_history_service(tmp_path: Path) -> HistoryService:
    service = HistoryService.__new__(HistoryService)
    service.history_dir = str(tmp_path)
    service.index_file = str(tmp_path / "index.json")
    service._init_index()
    return service


def test_history_update_protects_images_and_completed_status(tmp_path):
    service = make_history_service(tmp_path)
    record_id = service.create_record("topic", {
        "raw": "raw",
        "pages": [
            {"index": 0, "type": "cover", "content": "cover"},
            {"index": 1, "type": "content", "content": "content"},
        ],
    })

    assert service.update_record(
        record_id,
        images={"task_id": "task_1", "generated": ["0.png", "1.png"]},
        status="completed",
        thumbnail="0.png",
    )
    assert service.update_record(
        record_id,
        images={"task_id": "task_1", "generated": []},
        status="generating",
    )

    record = service.get_record(record_id)
    assert record["images"]["generated"] == ["0.png", "1.png"]
    assert record["status"] == "completed"


def test_merge_generated_image_is_index_aligned(tmp_path):
    service = make_history_service(tmp_path)
    record_id = service.create_record("topic", {
        "raw": "raw",
        "pages": [
            {"index": 0, "type": "cover", "content": "cover"},
            {"index": 1, "type": "content", "content": "content"},
            {"index": 2, "type": "summary", "content": "summary"},
        ],
    })

    service.merge_generated_image(record_id, "task_1", 2, "2.png")
    record = service.get_record(record_id)

    assert record["images"]["generated"] == ["", "", "2.png"]
    assert record["status"] == "partial"
    assert record["thumbnail"] == "2.png"


def test_cached_generation_events_do_not_call_generator(tmp_path):
    service = make_history_service(tmp_path)
    record_id = service.create_record("topic", {
        "raw": "raw",
        "pages": [
            {"index": 0, "type": "cover", "content": "cover"},
            {"index": 1, "type": "content", "content": "content"},
        ],
    })
    service.update_record(
        record_id,
        images={"task_id": "task_1", "generated": ["0.png", ""]},
        status="partial",
    )

    image_service = ImageService.__new__(ImageService)
    image_service.history_service = service

    events = image_service.get_cached_generation_events(record_id, [
        {"index": 0, "type": "cover", "content": "cover"},
        {"index": 1, "type": "content", "content": "content"},
    ])

    assert [event["event"] for event in events] == ["complete", "error", "finish"]
    assert events[0]["data"]["cached"] is True
    assert events[-1]["data"]["completed"] == 1
    assert events[-1]["data"]["failed_indices"] == [1]


class FakeGenerator:
    def __init__(self):
        self.calls = []

    def generate_image(self, **kwargs):
        self.calls.append(kwargs)
        return b"image-bytes"


def test_single_image_generation_writes_history_immediately(tmp_path):
    service = make_history_service(tmp_path)
    record_id = service.create_record("topic", {
        "raw": "raw",
        "pages": [{"index": 0, "type": "cover", "content": "cover"}],
    })

    image_service = ImageService.__new__(ImageService)
    image_service.generator = FakeGenerator()
    image_service.provider_config = {"type": "image_api", "model": "gpt-image-2"}
    image_service.use_short_prompt = False
    image_service.prompt_template = "{page_content}"
    image_service.prompt_template_short = ""
    image_service.current_task_dir = str(tmp_path / "task_1")
    Path(image_service.current_task_dir).mkdir()
    image_service.rate_limiter = ImageRateLimiter(max_concurrent=1, interval_seconds=0)
    image_service.history_service = service

    result = image_service._generate_single_image(
        {"index": 0, "type": "cover", "content": "cover"},
        "task_1",
        record_id=record_id,
        total_count=1,
    )

    assert result == (0, True, "0.png", None)
    record = service.get_record(record_id)
    assert record["images"]["generated"] == ["0.png"]
    assert record["status"] == "completed"


def test_atlascloud_generation_uses_media_api_size(tmp_path):
    image_service = ImageService.__new__(ImageService)
    image_service.generator = FakeGenerator()
    image_service.provider_config = {
        "type": "atlascloud_image",
        "model": "bytedance/seedream-v5.0-lite",
        "size": "1728*2304",
        "output_format": "png",
    }
    image_service.use_short_prompt = False
    image_service.prompt_template = "{page_content}"
    image_service.prompt_template_short = ""
    image_service.current_task_dir = str(tmp_path / "task_1")
    Path(image_service.current_task_dir).mkdir()
    image_service.rate_limiter = ImageRateLimiter(max_concurrent=1, interval_seconds=0)
    image_service.history_service = make_history_service(tmp_path)

    result = image_service._generate_single_image(
        {"index": 0, "type": "cover", "content": "cover"},
        "task_1",
    )

    assert result == (0, True, "0.png", None)
    assert image_service.generator.calls[0]["size"] == "1728*2304"
    assert image_service.generator.calls[0]["output_format"] == "png"
    assert image_service.generator.calls[0]["model"] == "bytedance/seedream-v5.0-lite"


def test_retry_failed_images_creates_task_dir_and_merges_by_index(tmp_path):
    service = make_history_service(tmp_path)
    record_id = service.create_record("topic", {
        "raw": "raw",
        "pages": [
            {"index": 0, "type": "cover", "content": "cover"},
            {"index": 1, "type": "content", "content": "content"},
            {"index": 2, "type": "summary", "content": "summary"},
        ],
    })

    image_service = ImageService.__new__(ImageService)
    image_service.generator = FakeGenerator()
    image_service.provider_config = {"type": "image_api", "model": "gpt-image-2"}
    image_service.use_short_prompt = False
    image_service.prompt_template = "{page_content}"
    image_service.prompt_template_short = ""
    image_service.history_root_dir = str(tmp_path)
    image_service.rate_limiter = ImageRateLimiter(max_concurrent=1, interval_seconds=0)
    image_service.history_service = service
    image_service.worker_count = 1
    image_service._task_states = {}

    events = list(image_service.retry_failed_images(
        "task_1",
        [
            {"index": 2, "type": "summary", "content": "summary"},
            {"index": 1, "type": "content", "content": "content"},
        ],
        record_id=record_id,
    ))

    assert [event["event"] for event in events] == [
        "retry_start",
        "complete",
        "complete",
        "retry_finish",
    ]
    assert (tmp_path / "task_1" / "1.png").exists()
    assert (tmp_path / "task_1" / "2.png").exists()

    record = service.get_record(record_id)
    assert record["images"]["generated"] == ["", "1.png", "2.png"]
    assert record["status"] == "partial"
